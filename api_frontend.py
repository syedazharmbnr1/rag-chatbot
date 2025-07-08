import streamlit as st
import requests

API_URL = "http://localhost:8000"  # Change if your FastAPI runs elsewhere

st.set_page_config(page_title="RAG Chatbot (API Frontend)", layout="wide")
st.title("RAG Chatbot (API Frontend)")

# --- Sidebar: Conversations ---
st.sidebar.header("Conversations")

# List conversations
def fetch_conversations(user_id):
    resp = requests.get(f"{API_URL}/conversations", params={"user_id": user_id})
    if resp.status_code == 200:
        return resp.json()
    return []

# Create conversation
def create_conversation(user_id, title="New Chat"):
    resp = requests.post(f"{API_URL}/create/conversations", json={"user_id": user_id, "title": title})
    if resp.status_code == 200:
        return resp.json()
    return None

# --- User selection (simulate login) ---
user_id = st.sidebar.text_input("User ID", value="demo_user")

if st.sidebar.button("New Conversation"):
    conv = create_conversation(user_id)
    st.session_state["current_conversation_id"] = conv["id"] if conv else None

convs = fetch_conversations(user_id)
conv_options = {f"{c['title']} ({c['id']})": c["id"] for c in convs}
selected_conv = st.sidebar.selectbox("Select Conversation", list(conv_options.keys()))
current_conversation_id = conv_options[selected_conv] if selected_conv else None
st.session_state["current_conversation_id"] = current_conversation_id

# --- Main: Chat ---
st.subheader(f"Conversation: {selected_conv}")

# Fetch messages
def fetch_messages(conversation_id):
    resp = requests.get(f"{API_URL}/messages", params={"conversation_id": conversation_id})
    if resp.status_code == 200:
        return resp.json()
    return []

messages = fetch_messages(current_conversation_id)
for msg in messages:
    role = msg["role"]
    content = msg["content"]
    user_name = msg.get("user_name")
    if role == "user":
        st.markdown(f"**{user_name or 'User'}:** {content}")
    else:
        st.markdown(f"**Assistant:** {content}")

# --- Send message (Direct Chat) ---
st.markdown("---")
st.markdown("### Send a Message (Direct Chat)")
user_input = st.text_input("Your message", key="user_input")
model_name = st.selectbox("Model", ["gpt-4o-mini", "gemma2:latest", "llama3.2:latest"], index=0)
if st.button("Send (Direct Chat)") and user_input:
    payload = {
        "conversation_id": current_conversation_id,
        "query": user_input,
        "model_name": model_name
    }
    resp = requests.post(f"{API_URL}/query/direct", json=payload)
    if resp.status_code == 200:
        # Show assistant reply immediately
        assistant_reply = resp.json()["response"]
        st.markdown(f"**Assistant:** {assistant_reply}")
        # Update conversation title if needed
        title_resp = requests.put(f"{API_URL}/update/conversations/{current_conversation_id}/title")
        if title_resp.status_code == 200:
            new_title = title_resp.json()["title"]
            st.session_state["updated_title"] = new_title
    else:
        st.error(f"Error: {resp.text}")

# --- Send message (RAG) ---
st.markdown("### Send a Message (RAG)")
rag_input = st.text_input("Your message (RAG)", key="rag_input")
# Fetch KBs
# Fetch KBs and their compatible embedding models
kbs = requests.get(f"{API_URL}/knowledge_bases").json()
kbs_names = [kb["name"] for kb in kbs]
selected_kb = st.selectbox("Select KB", kbs_names)

# Find compatible embedding models for the selected KB
embedding_models = ["text-embedding-3-small", "gemma2:latest", "llama3.2:latest"]
compatible_model = None
for model in embedding_models:
    compatible_kbs = requests.get(f"{API_URL}/knowledge_bases/compatible", params={"embedding_model": model}).json()
    if selected_kb in compatible_kbs:
        compatible_model = model
        break

embedding_model = st.selectbox("Embedding Model", embedding_models, index=embedding_models.index(compatible_model) if compatible_model else 0, disabled=True)
# Optionally, map embedding model to chat model
chat_model_map = {
    "text-embedding-3-small": "gpt-4o-mini",
    "gemma2:latest": "gemma2:latest",
    "llama3.2:latest": "llama3.2:latest"
}
chat_model = chat_model_map.get(embedding_model, "gpt-4o-mini")
st.text(f"Chat Model: {chat_model} (auto-selected)")
retrieval_k = st.number_input("Top K Chunks", min_value=1, max_value=10, value=4)
if st.button("Send (RAG)") and rag_input:
    payload = {
        "conversation_id": current_conversation_id,
        "query": rag_input,
        "kb_names": [selected_kb],  # <-- wrap in a list!
        "embedding_model": embedding_model,
        "chat_model": chat_model,
        "retrieval_k": retrieval_k
    }
    resp = requests.post(f"{API_URL}/query/rag", json=payload)
    if resp.status_code == 200:
        st.success("Assistant replied! Reload to see the message.")
        result = resp.json()
        st.markdown(f"**RAG Response:** {result['response']}")
        if result.get("sources"):
            st.markdown("**Sources:**")
            for src in result["sources"]:
                st.markdown(f"- {src['source']} (Page {src['page']}, Score: {src['score']})")
    else:
        st.error(f"Error: {resp.text}")

uploaded_file = st.file_uploader("Upload a document", type=["pdf", "docx"])

if uploaded_file is not None:
    # No need to ask for KB name, backend will auto-generate from file name
    embedding_model = st.selectbox("Embedding Model", ["text-embedding-3-small", "gemma2:latest", "llama3.2:latest"])
    chunking_strategy = st.selectbox("Chunking Strategy", ["semantic_percentile", "recursive"])
    if st.button("Upload to KB"):
        files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
        data = {
            # 'kb_name' is NOT sent
            "embedding_model_name": embedding_model,
            "chunking_strategy_name": chunking_strategy,
            "chunk_size": 1000,
            "chunk_overlap": 200
        }
        response = requests.post(f"{API_URL}/upload", files=files, data=data)
        if response.status_code == 200:
            st.success("File uploaded and processed!")
            st.json(response.json())
        else:
            st.error(f"Upload failed: {response.text}")
