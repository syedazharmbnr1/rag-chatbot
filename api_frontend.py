import streamlit as st
import requests
import jwt

API_URL = "http://localhost:8000"  # Change to your FastAPI host if different


# ----------------------------
# Utility: Login
# ----------------------------
def login(username: str, password: str):
    try:
        data = {
            'username': username,
            'password': password,
            'grant_type': 'password',
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(f"{API_URL}/token", data=data, headers=headers)

        if response.status_code == 200:
            token_data = response.json()
            st.session_state.token = token_data["access_token"]
            st.session_state.username = username

            # Decode token
            decoded = jwt.decode(token_data["access_token"], options={"verify_signature": False})
            st.session_state.user_id = decoded.get("sub")
            st.success("✅ Login successful!")
            st.rerun()
        else:
            st.error("❌ Incorrect username or password")
    except Exception as e:
        st.error(f"Login failed: {e}")


# ----------------------------
# Utility: Signup
# ----------------------------
def signup(username, full_name, email, password):
    data = {
        "username": username,
        "full_name": full_name,
        "email": email,
        "password": password
    }
    try:
        resp = requests.post(f"{API_URL}/signup", json=data)
        if resp.status_code == 200:
            st.success("🎉 Account created! Please log in.")
        else:
            st.error(f"❌ {resp.json().get('detail', 'Signup failed')}")
    except Exception as e:
        st.error(f"⚠️ Error: {e}")


# ----------------------------
# Auth Interface
# ----------------------------
if "token" not in st.session_state:
    st.set_page_config(page_title="RAG Chatbot", layout="wide")
    st.title("🔐 Login / Sign Up")

    auth_mode = st.radio("Choose Action", ["Login", "Sign Up"])

    if auth_mode == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            login(username, password)

    elif auth_mode == "Sign Up":
        new_username = st.text_input("Username")
        full_name = st.text_input("Full Name")
        email = st.text_input("Email")
        new_password = st.text_input("Password", type="password")
        if st.button("Create Account"):
            if all([new_username, full_name, email, new_password]):
                signup(new_username, full_name, email, new_password)
            else:
                st.warning("⚠️ Please fill all fields.")

    st.stop()

# ----------------------------
# Main Chatbot Interface
# ----------------------------
st.set_page_config(page_title="RAG Chatbot (API Frontend)", layout="wide")
st.title("💬 RAG Chatbot (API Frontend)")

user_id = st.session_state.user_id

# --- Sidebar ---
st.sidebar.header(f"👋 Hello, {user_id}")
if st.sidebar.button("🚪 Logout"):
    for key in ["token", "username", "user_id", "current_conversation_id"]:
        st.session_state.pop(key, None)
    st.rerun()


# Conversation management
def fetch_conversations(user_id):
    resp = requests.get(f"{API_URL}/conversations", params={"user_id": user_id})
    return resp.json() if resp.status_code == 200 else []


def create_conversation(user_id, title="New Chat"):
    resp = requests.post(f"{API_URL}/create/conversations", json={"user_id": user_id, "title": title})
    return resp.json() if resp.status_code == 200 else None


if st.sidebar.button("New Conversation"):
    conv = create_conversation(user_id)
    if conv:
        st.session_state["current_conversation_id"] = conv["id"]

convs = fetch_conversations(user_id)
conv_options = {f"{c['title']} ({c['id']})": c["id"] for c in convs}
selected_conv = st.sidebar.selectbox("Select Conversation", list(conv_options.keys()))
current_conversation_id = conv_options[selected_conv] if selected_conv else None
st.session_state["current_conversation_id"] = current_conversation_id


# Fetch and display messages
def fetch_messages(conversation_id):
    resp = requests.get(f"{API_URL}/messages", params={"conversation_id": conversation_id})
    return resp.json() if resp.status_code == 200 else []


st.subheader(f"Conversation: {selected_conv}")
messages = fetch_messages(current_conversation_id)
for msg in messages:
    role = msg["role"]
    content = msg["content"]
    user_name = msg.get("user_name", "User")
    if role == "user":
        st.markdown(f"**{user_name}:** {content}")
    else:
        st.markdown(f"**Assistant:** {content}")

# --- Direct Chat ---
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
        assistant_reply = resp.json()["response"]
        st.markdown(f"**Assistant:** {assistant_reply}")
        title_resp = requests.put(f"{API_URL}/update/conversations/{current_conversation_id}/title")
        if title_resp.status_code == 200:
            st.session_state["updated_title"] = title_resp.json()["title"]
    else:
        st.error(f"Error: {resp.text}")

# --- RAG Chat ---
st.markdown("### Send a Message (RAG)")
rag_input = st.text_input("Your message (RAG)", key="rag_input")

kbs = requests.get(f"{API_URL}/knowledge_bases").json()
kbs_names = [kb["name"] for kb in kbs]
selected_kb = st.selectbox("Select KB", kbs_names)

embedding_models = ["text-embedding-3-small", "gemma2:latest", "llama3.2:latest"]
compatible_model = None
for model in embedding_models:
    compatible_kbs = requests.get(f"{API_URL}/knowledge_bases/compatible", params={"embedding_model": model}).json()
    if selected_kb in compatible_kbs:
        compatible_model = model
        break

embedding_model = st.selectbox("Embedding Model", embedding_models,
                               index=embedding_models.index(compatible_model) if compatible_model else 0, disabled=True)
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
        "kb_names": [selected_kb],
        "embedding_model": embedding_model,
        "chat_model": chat_model,
        "retrieval_k": retrieval_k
    }
    resp = requests.post(f"{API_URL}/query/rag", json=payload)
    if resp.status_code == 200:
        result = resp.json()
        st.markdown(f"**RAG Response:** {result['response']}")
        if result.get("sources"):
            st.markdown("**Sources:**")
            for src in result["sources"]:
                st.markdown(f"- {src['source']} (Page {src['page']}, Score: {src['score']})")
    else:
        st.error(f"Error: {resp.text}")

# --- Upload File ---
uploaded_file = st.file_uploader("Upload a document", type=["pdf", "docx"])

if uploaded_file:
    embedding_model = st.selectbox("Embedding Model", ["text-embedding-3-small", "gemma2:latest", "llama3.2:latest"])
    chunking_strategy = st.selectbox("Chunking Strategy", ["semantic_percentile", "recursive"])
    if st.button("Upload to KB"):
        files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
        data = {
            "embedding_model_name": embedding_model,
            "chunking_strategy_name": chunking_strategy,
            "chunk_size": 1000,
            "chunk_overlap": 200
        }
        resp = requests.post(f"{API_URL}/upload", files=files, data=data)
        if resp.status_code == 200:
            st.success("✅ File uploaded and processed!")
            st.json(resp.json())
        else:
            st.error(f"Upload failed: {resp.text}")
