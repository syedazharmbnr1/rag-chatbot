from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
from uuid import uuid4
import requests
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from fastapi.responses import JSONResponse
import shutil


# Import DB functions
from utils.database import (
    get_conversations as db_get_conversations,
    create_conversation as db_create_conversation,
    delete_conversation as db_delete_conversation,
    update_conversation_title as db_update_conversation_title,
    get_messages as db_get_messages,
    add_message as db_add_message,
    get_knowledge_bases
)

from utils.document_processing import get_retriever, process_and_chunk_file, get_compatible_knowledge_bases

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Add your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

users_db = {}

class UserAuth(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    email: str
    id: str

class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str

class LoginRequest(BaseModel):
    username: str
    password: str


##########################################################
from datetime import datetime, timedelta, timezone
from typing import Annotated
import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from utils.auth import Token, authenticate_user, ACCESS_TOKEN_EXPIRE_MINUTES, User, get_current_active_user, create_access_token, get_password_hash, SignUpModel, get_user
from utils.database import create_user
from psycopg2.errors import UniqueViolation
from psycopg2 import IntegrityError

# 🧪 Routes
# here is sign up
@app.post("/signup")
async def signup(user: SignUpModel):
    # Check if user already exists
    if get_user(user.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    hashed_pw = get_password_hash(user.password)

    try:
        success = create_user(user.username, user.full_name, user.email, hashed_pw)
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Email or username already exists")

    if not success:
        raise HTTPException(status_code=500, detail="Failed to create user")

    return {"message": "✅ User created successfully. Please log in."}


@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

@app.get("/users/me/", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user

@app.get("/users/me/items/")
async def read_own_items(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return [{"item_id": "Foo", "owner": current_user.username}]


# ------------------ Conversation Models ------------------
class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: str

class CreateConversationRequest(BaseModel):
    user_id: str
    title: str

class UpdateConversationTitleRequest(BaseModel):
    title: str

@app.get("/conversations", response_model=List[ConversationOut])
def get_conversations(user_id: str):
    rows = db_get_conversations(user_id)
    # Each row: (id, title, created_at)
    return [ConversationOut(id=row[0], title=row[1], created_at=str(row[2])) for row in rows]

@app.post("/create/conversations", response_model=ConversationOut)
def create_conversation(req: CreateConversationRequest):
    conv_id = db_create_conversation(title=req.title, created_by=req.user_id)
    # Fetch the created conversation
    rows = db_get_conversations(req.user_id)
    conv = next((row for row in rows if row[0] == conv_id), None)
    if not conv:
        raise HTTPException(status_code=500, detail="Conversation creation failed")
    return ConversationOut(id=conv[0], title=conv[1], created_at=str(conv[2]))

@app.delete("/delete/conversations/{conv_id}")
def delete_conversation(conv_id: int):
    try:
        db_delete_conversation(conv_id)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.put("/update/conversations/{conv_id}/title")
def auto_update_conversation_title(conv_id: int):
    # Fetch all messages for this conversation
    messages = db_get_messages(conv_id)
    # Find the first user message
    first_user_msg = next((m for m in messages if m[1] == "user"), None)
    if not first_user_msg:
        raise HTTPException(status_code=404, detail="No user message found to generate title.")
    # Use first 30 chars of the message as title
    new_title = first_user_msg[2][:30] + ("..." if len(first_user_msg[2]) > 30 else "")
    db_update_conversation_title(conv_id, new_title)
    return {"title": new_title}

# ------------------ Message Models ------------------
class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    user_name: Optional[str] = None
    created_at: str

class AddMessageRequest(BaseModel):
    conversation_id: int
    role: str
    content: str
    user_name: str = None

@app.get("/messages", response_model=List[MessageOut])
def get_messages(conversation_id: int):
    rows = db_get_messages(conversation_id)
    # Each row: (id, role, content, user_name, created_at)
    return [MessageOut(id=row[0], role=row[1], content=row[2], user_name=row[3], created_at=str(row[4])) for row in rows]

@app.post("/add/messages", response_model=MessageOut)
def add_message(req: AddMessageRequest):
    msg_id = db_add_message(req.conversation_id, req.role, req.content, req.user_name)
    # Fetch the message just added
    rows = db_get_messages(req.conversation_id)
    msg = next((row for row in rows if row[0] == msg_id), None)
    # Auto-update title if this is the first user message
    user_msgs = [m for m in rows if m[1] == "user"]
    if len(user_msgs) == 1:
        auto_update_conversation_title(req.conversation_id)
    if not msg:
        raise HTTPException(status_code=500, detail="Message creation failed")
    return MessageOut(id=msg[0], role=msg[1], content=msg[2], user_name=msg[3], created_at=str(msg[4]))

# ------------------ Direct Chat (No KB) ------------------
class DirectChatRequest(BaseModel):
    conversation_id: int
    query: str
    model_name: str = "gemma2:latest"

class DirectChatResponse(BaseModel):
    response: str

# Helper: Call LLM using LangChain

def call_langchain_chat(query, model_name):
    if model_name.startswith("gpt"):
        llm = ChatOpenAI(model=model_name)
    else:
        llm = ChatOllama(model=model_name)
    response = llm.invoke([HumanMessage(content=query)])
    return response.content

@app.post("/query/direct", response_model=DirectChatResponse)
def direct_chat(req: DirectChatRequest):
    # Save user message
    db_add_message(req.conversation_id, "user", req.query, user_name=None)
    # Auto-update title if this is the first user message
    rows = db_get_messages(req.conversation_id)
    user_msgs = [m for m in rows if m[1] == "user"]
    if len(user_msgs) == 1:
        auto_update_conversation_title(req.conversation_id)
    # Call LLM via LangChain
    response = call_langchain_chat(req.query, req.model_name)
    # Save assistant message
    db_add_message(req.conversation_id, "assistant", response, user_name=None)
    return DirectChatResponse(response=response)

# ------------------ RAG (Knowledge Base) Query ------------------
class RAGQueryRequest(BaseModel):
    conversation_id: int
    query: str
    kb_names: List[str]
    embedding_model: str
    chat_model: str
    retrieval_k: Optional[int] = 4

class SourceInfo(BaseModel):
    source: str
    page: int
    score: float
    kb_name: str

class RAGQueryResponse(BaseModel):
    response: str
    sources: Optional[List[SourceInfo]] = None

@app.post("/query/rag", response_model=RAGQueryResponse)
def rag_query(req: RAGQueryRequest):
    # Save user message (no manual conversation existence check)
    db_add_message(req.conversation_id, "user", req.query, user_name=None)
    # Auto-update title if this is the first user message
    rows = db_get_messages(req.conversation_id)
    user_msgs = [m for m in rows if m[1] == "user"]
    if len(user_msgs) == 1:
        auto_update_conversation_title(req.conversation_id)
    all_sources = []
    all_contexts = []
    # For each KB, retrieve relevant docs
    for kb_name in req.kb_names:
        try:
            retriever = get_retriever(kb_name, req.embedding_model, k=req.retrieval_k)
            # Use the underlying vectorstore for similarity search with score
            vectorstore = retriever.vectorstore
            docs_and_scores = vectorstore.similarity_search_with_score(req.query, k=req.retrieval_k)
            for doc, score in docs_and_scores:
                meta = doc.metadata
                all_contexts.append(doc.page_content)
                relevance = 1 / (1 + float(score))
                relevance_percent = round(relevance * 100)
                all_sources.append({
                    "source": meta.get("source", "unknown"),
                    "page": meta.get("page", 0) + 1,
                    "score": relevance_percent,
                    "kb_name": kb_name
                })
        except Exception as e:
            continue
    # Compose context for LLM
    context = "\n---\n".join(all_contexts)
    prompt = f"Context:\n{context}\n\nUser question: {req.query}"
    # Call LLM via LangChain
    response = call_langchain_chat(prompt, req.chat_model)
    # Save assistant message
    db_add_message(req.conversation_id, "assistant", response, user_name=None)
    return RAGQueryResponse(response=response, sources=[SourceInfo(**s) for s in all_sources])







@app.post("/upload")
async def upload_and_process_file(
        file: UploadFile = File(...),
        embedding_model_name: str = Form(...),
        chunking_strategy_name: str = Form(...),
        chunk_size: int = Form(1000),
        chunk_overlap: int = Form(200)
):
    # Always generate kb_name from the file name
    base_name = os.path.splitext(file.filename)[0].lower().replace(' ', '_')
    kb_name = f"kb_{base_name}"

    # Save file temporarily to disk for processing if needed
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, file.filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        with open(file_path, "rb") as f:
            result = process_and_chunk_file(
                file=f,
                kb_name=kb_name,
                embedding_model_name=embedding_model_name,
                chunking_strategy_name=chunking_strategy_name,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

        return JSONResponse(content=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up the temporary file
        if os.path.exists(file_path):
            os.remove(file_path)

@app.get("/knowledge_bases")
def list_knowledge_bases():
    kbs = get_knowledge_bases()
    return kbs

@app.get("/knowledge_bases/compatible")
def get_compatible_kbs(embedding_model: str):
    kbs = get_compatible_knowledge_bases(embedding_model)
    return kbs
