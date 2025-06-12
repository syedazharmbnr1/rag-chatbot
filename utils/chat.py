"""Chat functionality for the RAG Chatbot."""
# Add or update these imports at the top of chat.py
import logging
from typing import List, Dict, Any, Optional
import yaml
import os

from langchain_openai import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_community.vectorstores import FAISS
from langchain_ollama import ChatOllama
# Import from document_processing (this was missing)
from utils.document_processing import initialize_embedding_model, get_retriever
from utils.database import add_message, add_sources, get_messages, update_conversation_title
# Setup logging
logger = logging.getLogger("rag-chatbot.chat")

def load_settings(settings_path="settings.yml"):
    """Load settings from a YAML file."""
    try:
        with open(settings_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Error loading settings file: {e}")
        # Return default settings
        return {
            "chat_model": "gpt-4o-mini",
            "embeddings_model": "text-embedding-3-small",
            "retrieval": {
                "top_k": 4,
                "search_type": "mmr",
                "fetch_k": 8
            }
        }

def get_conversation_chain(kb_name: str, embedding_model: str, chat_model: str, retrieval_k: int = 4):
    """Create a conversational chain for the RAG system."""
    logger.info(f"Creating conversation chain with KB: {kb_name}, model: {chat_model}")
    
    try:
        # Get the retriever for the knowledge base
        retriever = get_retriever(
            kb_name=kb_name,
            embedding_model_name=embedding_model,
            k=retrieval_k,
            search_type="mmr"
        )
        
        # Initialize the LLM
        llm = ChatOpenAI(model_name=chat_model, temperature=0.7)
        logger.debug(f"Initialized ChatOpenAI with model: {chat_model}")
        
        # Create system prompt template with better context handling
        template = """
        You are an Enterprise RAG (Retrieval-Augmented Generation) Chatbot providing helpful information based on the documents in the knowledge base.
        
        Use the following pieces of context to answer the question at the end. If you don't know the answer, just say you don't know. Don't try to make up an answer.
        The answer should be comprehensive and detailed, drawing specifically from the provided context.
        
        If the question relates to the documents, provide page numbers and document names as source citations.
        
        Context:
        {context}
        
        Chat History:
        {chat_history}
        
        Question: {question}
        
        Answer:
        """
        
        PROMPT = PromptTemplate(
            input_variables=["context", "chat_history", "question"],
            template=template,
        )
        
        # Initialize memory
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        
        # Create the chain
        chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            memory=memory,
            combine_docs_chain_kwargs={"prompt": PROMPT},
            return_source_documents=True,
            verbose=False  # Set to True for debugging
        )
        
        logger.info("Conversation chain created successfully")
        return chain
    except Exception as e:
        logger.exception(f"Error creating conversation chain: {str(e)}")
        raise


# Fix the process_query function in chat.py:

def process_query(conversation_id: int, query: str, kb_name: str = None, kb_names: list = None,
                  embedding_model: str = "text-embedding-3-small", chat_model: str = "gpt-4o-mini",
                  retrieval_k: int = 4):
    """Process a user query and generate a response with sources from multiple knowledge bases."""
    logger.info(f"Processing query for conversation: {conversation_id}")
    logger.info(f"Using embedding model: {embedding_model}")  # ADD THIS
    logger.info(f"Using chat model: {chat_model}")

    # If kb_names is provided, use all selected KBs instead of just the active one
    if kb_names and len(kb_names) > 0:
        using_multiple_kbs = True
        logger.info(f"Using multiple knowledge bases: {', '.join(kb_names)}")
    elif kb_name:
        kb_names = [kb_name]
        using_multiple_kbs = False
        logger.info(f"Using single knowledge base: {kb_name}")
    else:
        logger.error("No knowledge base specified")
        raise ValueError("No knowledge base specified")

    try:
        # We'll collect all source documents across knowledge bases
        all_source_docs = []
        all_kb_docs = {}  # Store documents by KB
        all_answers = []
        queried_kb_count = 0
        successful_kb_count = 0

        # Query each knowledge base
        for current_kb in kb_names:
            try:
                queried_kb_count += 1
                logger.info(f"Processing KB: {current_kb}")

                # OPTION 1: If using new folder structure, use this:
                # from utils.document_processing import get_faiss_index_path
                # kb_path = get_faiss_index_path(current_kb, embedding_model)

                # OPTION 2: For current setup, check multiple possible paths:
                possible_paths = [
                    f"FAISS_Index/{current_kb}",  # Original path
                    f"llama3.2/FAISS_Index/{current_kb}",  # Llama path
                    f"openai/FAISS_Index/{current_kb}",  # OpenAI path
                    f"gemma2/FAISS_Index/{current_kb}",  # Gemma path
                    f"deepseek/FAISS_Index/{current_kb}"  # DeepSeek path
                ]

                kb_path = None
                for path in possible_paths:
                    if os.path.exists(path) and os.path.isdir(path):
                        kb_path = path
                        logger.info(f"Found KB at path: {kb_path}")
                        break

                if not kb_path:
                    logger.warning(f"Knowledge base {current_kb} not found in any location")
                    logger.debug(f"Searched paths: {possible_paths}")
                    continue

                # Initialize embedding model
                try:
                    embeddings = initialize_embedding_model(embedding_model)
                    logger.info(f"Initialized embedding model: {embedding_model}")
                except Exception as embed_error:
                    logger.error(f"Failed to initialize embedding model {embedding_model}: {embed_error}")
                    continue

                # Load vectorstore directly
                try:
                    vectorstore = FAISS.load_local(
                        folder_path=kb_path,
                        embeddings=embeddings,
                        allow_dangerous_deserialization=True
                    )
                    logger.info(f"Loaded vectorstore from: {kb_path}")
                except Exception as load_error:
                    logger.error(f"Failed to load vectorstore from {kb_path}: {load_error}")
                    continue

                # Get relevant documents directly with similarity scores
                try:
                    docs_and_scores = vectorstore.similarity_search_with_score(query, k=retrieval_k)
                    logger.info(f"Retrieved {len(docs_and_scores)} documents from {current_kb}")

                    # Debug: Log the first few results
                    for i, (doc, score) in enumerate(docs_and_scores[:2]):  # Just first 2
                        logger.debug(f"Doc {i}: score={score:.4f}, content_preview={doc.page_content[:100]}...")

                except Exception as search_error:
                    logger.error(f"Failed to search in {current_kb}: {search_error}")
                    continue

                # Only add documents if we got results
                if docs_and_scores:
                    # Process the retrieved documents
                    kb_docs = []
                    for doc, score in docs_and_scores:
                        # Calculate a true relevance score (convert distance to similarity)
                        relevance = 1.0 / (1.0 + float(score))

                        # Add metadata
                        doc.metadata['kb_name'] = current_kb
                        doc.metadata['score'] = relevance
                        doc.metadata['raw_score'] = float(score)

                        kb_docs.append(doc)
                        logger.debug(f"Added doc with score: {relevance:.4f}")

                    # Store documents for this KB
                    all_kb_docs[current_kb] = kb_docs
                    all_source_docs.extend(kb_docs)
                    logger.info(f"Added {len(kb_docs)} documents to collection")

                    # CRITICAL: Only try to get an answer if we have documents
                    if kb_docs:
                        logger.info(f"Processing {len(kb_docs)} documents from {current_kb}")

                        # Initialize the LLM with proper handling for different models
                        try:
                            if chat_model.startswith("gpt"):
                                from langchain_openai import ChatOpenAI
                                llm = ChatOpenAI(model_name=chat_model, temperature=0.7)
                            else:
                                from langchain_ollama import ChatOllama
                                llm = ChatOllama(model=chat_model, temperature=0.7)

                            logger.info(f"Initialized LLM: {chat_model}")
                        except Exception as llm_error:
                            logger.error(f"Failed to initialize LLM {chat_model}: {llm_error}")
                            continue

                        # Create context from the top documents
                        context = "\n\n".join([
                            f"Document: {doc.metadata.get('source', 'Unknown')}, "
                            f"Page: {doc.metadata.get('page', 0) + 1}, "
                            f"Knowledge Base: {current_kb}\n{doc.page_content}"
                            for doc in kb_docs[:retrieval_k]
                        ])

                        logger.info(f"Created context with {len(context)} characters")

                        # Create system prompt
                        template = f"""
                        You are an Enterprise RAG (Retrieval-Augmented Generation) Chatbot providing helpful information based on the documents in the knowledge base.

                        Use the following context to answer the question. If you don't know the answer, just say you don't know. Don't try to make up an answer.

                        Always provide page numbers and document names as source citations.

                        Context:
                        {context}

                        Question: {query}

                        Answer:
                        """

                        # Get response from LLM
                        try:
                            messages = [{"role": "system", "content": template}]
                            response = llm.invoke(messages)

                            if hasattr(response, 'content'):
                                answer = response.content
                            else:
                                answer = str(response)

                            logger.info(f"Got answer of length {len(answer)} from {current_kb}")
                            all_answers.append((current_kb, answer))
                            successful_kb_count += 1
                        except Exception as llm_error:
                            logger.error(f"LLM failed to generate answer: {llm_error}")
                            continue
                    else:
                        logger.warning(f"No valid documents found in {current_kb} after processing")
                else:
                    logger.warning(f"No documents retrieved from {current_kb} for query: {query}")
            except Exception as kb_error:
                logger.error(f"Error querying KB {current_kb}: {str(kb_error)}")
                import traceback
                logger.debug(f"KB error traceback: {traceback.format_exc()}")
                continue

        # Add detailed logging before determining final answer
        logger.info(f"=== FINAL PROCESSING SUMMARY ===")
        logger.info(f"Total answers collected: {len(all_answers)}")
        logger.info(f"Successful KB count: {successful_kb_count}")
        logger.info(f"Queried KB count: {queried_kb_count}")
        logger.info(f"Total source documents: {len(all_source_docs)}")
        logger.info(f"All KB docs keys: {list(all_kb_docs.keys())}")

        # Sort documents by relevance score
        all_source_docs.sort(key=lambda doc: doc.metadata.get('score', 0), reverse=True)

        # Deduplicate sources while preserving order
        seen_sources = set()
        unique_source_docs = []
        for doc in all_source_docs:
            source_key = (doc.metadata.get('source', ''), doc.metadata.get('page', 0))
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                unique_source_docs.append(doc)

        logger.info(f"Unique source documents: {len(unique_source_docs)}")

        # Determine the final answer
        if len(all_answers) == 0:
            logger.error(f"No answers generated despite processing {queried_kb_count} KBs")
            answer = f"I couldn't find any relevant information in the {queried_kb_count} selected knowledge bases. Please check if these knowledge bases contain the information you're looking for, or try rephrasing your question."
        elif len(all_answers) == 1:
            answer = all_answers[0][1]
            logger.info(f"Using single answer from {all_answers[0][0]}")
        else:
            logger.info(f"Synthesizing {len(all_answers)} answers")
            # ... existing synthesis logic ...

        # Format sources with detailed information
        query_relevant_sources = []
        kb_sources = {}

        # Process unique source documents for query-relevant sources
        for doc in unique_source_docs:
            source = {
                'source': doc.metadata.get('source', 'Unknown'),
                'page': doc.metadata.get('page', 0) + 1,
                'score': doc.metadata.get('score', 0.5),
                'kb_name': doc.metadata.get('kb_name', 'Unknown KB')
            }
            query_relevant_sources.append(source)

        logger.info(f"Final query_relevant_sources count: {len(query_relevant_sources)}")

        # Process documents by KB for the KB-specific tab
        for kb_name, docs in all_kb_docs.items():
            kb_specific_sources = []
            seen = set()

            for doc in docs:
                key = (doc.metadata.get('source', 'Unknown'), doc.metadata.get('page', 0))
                if key not in seen:
                    seen.add(key)
                    kb_specific_sources.append({
                        'source': doc.metadata.get('source', 'Unknown'),
                        'page': doc.metadata.get('page', 0) + 1,
                        'score': doc.metadata.get('score', 0.5),
                        'kb_name': kb_name
                    })

            kb_sources[kb_name] = kb_specific_sources

        # Add assistant message to database with model name
        assistant_message_id = add_message(
            conversation_id,
            "assistant",
            answer,
            f"AI Assistant ({chat_model})"
        )

        # Combine all sources for database storage
        all_sources = query_relevant_sources
        logger.info(f"Adding {len(all_sources)} sources to database")

        # Add sources to database
        if all_sources:
            add_sources(assistant_message_id, all_sources)
            logger.debug(f"Added {len(all_sources)} sources to message {assistant_message_id}")
        else:
            logger.warning("No sources to add to database!")

        return {
            "content": answer,
            "sources": {
                "query_relevant": query_relevant_sources,
                "kb_specific": kb_sources
            },
            "message_id": assistant_message_id
        }
    except Exception as e:
        logger.exception(f"Error processing query: {str(e)}")
        error_message = f"I encountered an error while processing your query: {str(e)}"
        message_id = add_message(conversation_id, "assistant", error_message, f"AI Assistant ({chat_model})")
        return {
            "content": error_message,
            "sources": {"query_relevant": [], "kb_specific": {}},
            "message_id": message_id,
            "error": str(e)
        }


def direct_openai_query(conversation_id: int, query: str, model_name: str = "gpt-4o-mini"):
    """Process a direct query to LLM without using a knowledge base."""
    logger.info(f"Processing direct query with model: {model_name}")

    try:
        # Initialize the appropriate LLM based on model name
        if model_name.startswith("gpt"):
            # OpenAI models
            llm = ChatOpenAI(model_name=model_name, temperature=0.7)
        else:
            # Ollama models using new langchain_ollama
            llm = ChatOllama(model=model_name, temperature=0.7)

        # Simple system prompt for direct conversation
        system_message = f"""
        You are a helpful AI assistant powered by {model_name}. Provide informative, accurate, and helpful responses to the user's questions.
        If you don't know the answer to something, be honest about it rather than making up information.
        """

        # Get message history
        messages = get_messages(conversation_id)
        formatted_messages = []

        # Add system message
        formatted_messages.append({"role": "system", "content": system_message})

        # Add conversation history (excluding system messages)
        for msg_id, role, content, user_name, timestamp in messages:
            if role != "system":
                formatted_messages.append({"role": role, "content": content})

        # Process the query
        logger.debug(f"Sending query to {model_name}: {query[:50]}...")
        response = llm.invoke(formatted_messages)

        # Handle different response types
        if hasattr(response, 'content'):
            answer = response.content
        else:
            answer = str(response)

        logger.debug(f"Received answer of length: {len(answer)}")

        # Add assistant message to database with proper assistant name
        assistant_message_id = add_message(
            conversation_id,
            "assistant",
            answer,
            f"AI Assistant ({model_name})"
        )

        return {
            "content": answer,
            "message_id": assistant_message_id
        }
    except Exception as e:
        logger.exception(f"Error in direct query with {model_name}: {str(e)}")
        error_message = f"I encountered an error while processing your query with {model_name}: {str(e)}"
        message_id = add_message(
            conversation_id,
            "assistant",
            error_message,
            f"AI Assistant ({model_name})"
        )
        return {
            "content": error_message,
            "message_id": message_id,
            "error": str(e)
        }

def format_sources(source_docs):
    """Format source documents for display with enhanced information."""
    sources = []
    for doc in source_docs:
        # Safely handle score conversion
        try:
            score_value = doc.metadata.get('score', 0.5)
            score = float(score_value) if score_value is not None else 0.5
        except (ValueError, TypeError):
            score = 0.5  # Default if conversion fails
            
        source = {
            'source': doc.metadata.get('source', 'Unknown'),
            'page': doc.metadata.get('page', 0) + 1,  # Convert to 1-based indexing
            'score': score,
            'kb_name': doc.metadata.get('kb_name', 'Unknown KB')
        }
        sources.append(source)
    
    # Remove duplicates while preserving order
    unique_sources = []
    seen = set()
    for source in sources:
        key = (source['source'], source['page'], source['kb_name'])
        if key not in seen:
            seen.add(key)
            unique_sources.append(source)
    
    # Sort by relevance score
    return sorted(unique_sources, key=lambda x: x['score'], reverse=True)

def get_suggested_prompts() -> List[str]:
    """Get suggested prompts for the user."""
    return [
        "Can you summarize the key points in these documents?",
        "What are the main topics covered in the knowledge base?",
        "Extract the most important information from these files.",
        "What insights can you provide based on the documents?",
        "Compare and contrast the information across these documents.",
        "Generate a concise summary of the uploaded content."
    ]