import streamlit as st
import streamlit_authenticator as stauth
import os
import yaml
from yaml.loader import SafeLoader
import time
import uuid
import base64
import logging
from datetime import datetime, timedelta
from io import BytesIO

# Import utility modules
from utils.database import (
    get_conversations,
    create_conversation,
    get_messages,
    add_message,
    add_sources,
    get_sources,
    update_conversation_title,
    delete_conversation,
    get_setting,
    set_setting,
    get_active_knowledge_base,
    set_active_knowledge_base,
    init_database
)

from utils.document_processing import (
    process_and_chunk_file,
    get_all_knowledge_base_names,
    kb_exists,
    auto_create_knowledge_base_if_needed,
    get_compatible_knowledge_bases,
    ChunkingStrategy,
    EmbeddingModel,
    ChatModel
)

from utils.chat import (
    load_settings,
    process_query,
    get_suggested_prompts,
    direct_openai_query
)

logger = logging.getLogger("rag-chatbot")

# Page configuration
st.set_page_config(
    page_title="RAG Chatbot",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Custom CSS
import streamlit as st

def add_custom_css():
    st.markdown("""
    <style>
    @font-face {
      font-family: "racForward";
      src: url("../fonts/racForward-Regular.otf") format("opentype");
      font-weight: 400;
    }
    @font-face {
      font-family: "racForward";
      src: url("../fonts/racForward-Medium.otf") format("opentype");
      font-weight: 500;
    }
    @font-face {
      font-family: "racForward";
      src: url("../fonts/racForward-Bold.otf") format("opentype");
      font-weight: 700;
    }

    :root {
      --rac-purple-dark: #43206f;
      --rac-purple:       #5b2d91;
      --rac-pink:         #ff0066;
      --rac-pink-dark:    #e0005b;
      --rac-lavender:     #f3f0f9;
      --rac-light-gray:   #f7f7f8;
      --rac-gray:         #4b5563;
      --rac-green:        #00c389;

      --custom-dark:      #333446;
      --custom-muted:     #7F8CAA;
      --custom-pale:      #B8CFCE;
      --custom-offwhite:  #EAEFEF;
    }

    * {
      font-family: "racForward", "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
    }

    #MainMenu, footer, header { display: none !important; }

    /* Sidebar background */
    section[data-testid="stSidebar"] {
        background-color: #D1D8BE !important;
    }

    /* Sidebar button */
    section[data-testid="stSidebar"] button {
        background-color: #A7C1A8 !important;
        color: black !important;
        border: 1px solid #819A91 !important;
        border-radius: 6px !important;
    }

    /* Hover effect on sidebar buttons */
    section[data-testid="stSidebar"] button:hover {
        background-color: #819A91 !important;
        color: white !important;
        border-color: #819A91 !important;
    }

    /* Body background */
    .main {
        background-color: #EEEFE0 !important;
    }

    /* Optional: change text color in sidebar for better contrast */
    section[data-testid="stSidebar"] * {
        color: #333 !important;
    }

    .kb-card {
      background: #EEEFE0 !important;
      border: 1px solid var(--custom-pale) !important;
    }

    .kb-card.active {
      background: var(--rac-lavender) !important;
      border-color: var(--rac-purple) !important;
    }

    .mode-indicator.rag {
      background: var(--rac-purple) !important;
      color: white !important;
    }

    .mode-indicator.openai {
      background: var(--rac-gray) !important;
      color: white !important;
    }

    .main .block-container {
      padding-top: 30px !important;
      max-width: 1200px !important;
    }

    [data-testid="rachatMessage"] {
      background: transparent !important;
    }

    [data-testid="rachatMessage"] [data-testid="rachatMessageContent"] {
      background: var(--custom-offwhite) !important;
      color: #000 !important;
    }

    [data-testid="rachatMessage"][data-testid="rachatMessageUser"] [data-testid="rachatMessageContent"] {
      background: var(--rac-purple) !important;
      color: white !important;
    }

    .stButton > button {
      background: var(--rac-lavender) !important;
      color: var(--rac-purple-dark) !important;
      border: 1px solid #d1d5db !important;
    }

    .stButton > button:hover {
      background: var(--custom-offwhite) !important;
    }

    .stButton > button[data-testid="baseButton-primary"] {
      background: var(--rac-pink) !important;
    }

    .stButton > button[data-testid="baseButton-primary"]:hover {
      background: var(--rac-pink-dark) !important;
    }

    .stButton > button[data-testid="baseButton-secondary"] {
      background: var(--rac-gray) !important;
    }

    .stButton > button[data-testid="baseButton-secondary"]:hover {
      background: var(--rac-purple) !important;
    }

    .stProgress > div > div > div {
      background: var(--rac-pink) !important;
    }

    .upload-area {
      border: 2px dashed var(--rac-purple);
      background: var(--custom-offwhite);
    }

    .upload-area:hover {
      background: #ebe6f3;
    }

    div[data-baseweb="select"] {
      background: white !important;
      color: var(--rac-purple-dark) !important;
    }

    div[data-baseweb="select"]:hover {
      border-color: var(--rac-purple) !important;
    }

    div[data-baseweb="tag"] {
      background: var(--rac-purple) !important;
    }

    @keyframes pulse {
      0% { opacity: .4; transform: scale(1); }
      50% { opacity: 1; transform: scale(1.3); }
      100% { opacity: .4; transform: scale(1); }
    }

    .thinking-dot {
      background: var(--rac-purple);
      animation: pulse 1.5s infinite;
    }

    </style>
    """, unsafe_allow_html=True)


def api_key_required_screen():
    st.error("⚠️ OpenAI API Key Required")
    st.markdown("""
    Please configure your OpenAI API key in the settings.yml file:

    1. Get your API key from [OpenAI's platform](https://platform.openai.com/api-keys)
    2. Open the `settings.yml` file in the root directory
    3. Replace the placeholder with your actual API key:
       ```yaml
       openai_key: "your-api-key-here"
       ```
    4. Restart the application
    """)

def authenticate_user(yaml_path='credentials.yaml'):
    # Load config
    try:
        with open(yaml_path) as file:
            config = yaml.load(file, Loader=SafeLoader)
    except Exception as e:
        st.error(f"❌ Failed to load YAML: {e}")
        return None

    # Create authenticator object
    try:
        authenticator = stauth.Authenticate(
            config['credentials'],
            config['cookie']['name'],
            config['cookie']['key'],
            config['cookie']['expiry_days'],
            config.get('preauthorized')
        )
    except Exception as e:
        st.error(f"❌ Failed to initialize authenticator: {e}")
        return None

    # Render login form
    try:
        name, auth_status, username = authenticator.login("Login","main")
        st.session_state['authentication_status'] = auth_status
        st.session_state['name'] = name
        st.session_state['username'] = username
    except Exception as e:
        st.error(f"❌ Login error: {e}")
        return None

    # Handle login result
    if auth_status:
        with st.sidebar:
            st.write(f"Welcome *{name}*")
            authenticator.logout("Logout", location="main")
    elif auth_status is False:
        st.error("❌ Username/password is incorrect")
    elif auth_status is None:
        st.warning("🔐 Please enter your username and password")

    return auth_status
# Initialize session state variables
def init_session_state():
    logger.info("Initializing session state")

    try:
        init_database()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        st.error(f"Database initialization failed: {e}")
        return

    # Get current user
    current_user = st.session_state.get('username', 'admin')

    # ALWAYS refresh conversations from database (don't cache)
    st.session_state.conversations = get_conversations(current_user)
    logger.debug(f"Loaded {len(st.session_state.conversations)} conversations for user: {current_user}")

    # CRITICAL FIX: Ensure current_conversation_id is set
    if "current_conversation_id" not in st.session_state:
        # Create a new conversation if none exists
        if not st.session_state.conversations:
            logger.info(f"No conversations found for {current_user}, creating a new one")
            new_id = create_conversation(created_by=current_user)
            st.session_state.conversations = get_conversations(current_user)
            st.session_state.current_conversation_id = new_id
        else:
            logger.info(f"Setting current conversation to first in list for {current_user}")
            st.session_state.current_conversation_id = st.session_state.conversations[0][0]

    # ENSURE messages are loaded for current conversation
    if "messages" not in st.session_state:
        st.session_state.messages = get_messages(st.session_state.current_conversation_id)
        logger.debug(
            f"Loaded {len(st.session_state.messages)} messages for conversation {st.session_state.current_conversation_id}")

    if "settings" not in st.session_state:
        st.session_state.settings = load_settings()
        logger.debug(f"Loaded settings: {st.session_state.settings}")

    if "openai_key_configured" not in st.session_state:
        key = st.session_state.settings.get("openai_key")
        if key and key != "sk-proj-pJx" and key != "sk-":  # Check if it's not the placeholder
            os.environ["OPENAI_API_KEY"] = key
            st.session_state.openai_key_configured = True
            logger.info("OpenAI API key configured")
        else:
            st.session_state.openai_key_configured = False
            logger.warning("OpenAI API key not configured")

    if "active_kb" not in st.session_state:
        # Get active knowledge base from database
        active_kb = get_active_knowledge_base()
        if active_kb:
            st.session_state.active_kb = active_kb["name"]
            logger.info(f"Active knowledge base set to: {st.session_state.active_kb}")
        else:
            # Auto-create a knowledge base if none exists
            logger.info("No active knowledge base, creating default")
            kb_name = auto_create_knowledge_base_if_needed()
            st.session_state.active_kb = kb_name
            set_active_knowledge_base(kb_name)

    # For multiple KB selection
    if "selected_kbs" not in st.session_state:
        st.session_state.selected_kbs = [st.session_state.active_kb] if st.session_state.active_kb else []

    if "show_sources" not in st.session_state:
        st.session_state.show_sources = True

    if "is_thinking" not in st.session_state:
        st.session_state.is_thinking = False

    if "processing_file" not in st.session_state:
        st.session_state.processing_file = False

    if "direct_chat_mode" not in st.session_state:
        st.session_state.direct_chat_mode = False
        logger.info("Direct chat mode initially set to: False")

    if "upload_status" not in st.session_state:
        st.session_state.upload_status = None

    if "processed_files" not in st.session_state:
        st.session_state.processed_files = set()

    if "kb_names" not in st.session_state:
        st.session_state.kb_names = get_all_knowledge_base_names()


def process_uploaded_files(uploaded_files, embedding_model, chunking_strategy):
    """Process uploaded files with user-selected options"""
    if not uploaded_files:
        return

    # Set processing flag
    st.session_state.processing_file = True

    # Keep track of processed file names to avoid reprocessing
    if "processed_files" not in st.session_state:
        st.session_state.processed_files = set()

    # Get list of files to process (filter already processed ones)
    files_to_process = []
    for file in uploaded_files:
        # Create a unique identifier for the file based on name and size
        file_id = f"{file.name}_{len(file.getvalue())}"
        if file_id not in st.session_state.processed_files:
            files_to_process.append((file, file_id))

    if not files_to_process:
        st.session_state.processing_file = False
        return

    logger.info(f"Processing {len(files_to_process)} new uploaded files")
    logger.info(f"Using embedding model: {embedding_model}, chunking strategy: {chunking_strategy}")

    success_count = 0
    error_count = 0
    new_kb_created = False
    newly_created_kbs = []

    # Process each file
    for file, file_id in files_to_process:
        try:
            logger.info(f"Processing file: {file.name}")

            # Mark as processed
            st.session_state.processed_files.add(file_id)

            # Generate KB name from filename
            file_name = file.name
            base_name = os.path.splitext(file_name)[0].lower().replace(' ', '_')
            kb_name = f"kb_{base_name}"

            # Ensure file is not corrupted by reading content
            file_content = file.read()
            file.seek(0)  # Reset file pointer after reading

            logger.debug(f"File size: {len(file_content)} bytes")
            logger.debug(f"Knowledge base name: {kb_name}")

            # Process the file with user-selected options
            result = process_and_chunk_file(
                file=file,
                kb_name=kb_name,
                embedding_model_name=embedding_model,  # Use user selection
                chunking_strategy_name=chunking_strategy  # Use user selection
            )

            if result["status"] == "success":
                logger.info(f"Successfully processed {file_name}: {result['chunk_count']} chunks")

                # Add the new KB to the list of selected KBs
                if kb_name not in st.session_state.selected_kbs:
                    st.session_state.selected_kbs.append(kb_name)

                # Track newly created KBs
                newly_created_kbs.append(kb_name)

                # Set as active KB if needed
                if not st.session_state.active_kb or st.session_state.active_kb == "default_knowledge_base":
                    logger.info(f"Setting active knowledge base to: {kb_name}")
                    st.session_state.active_kb = kb_name
                    set_active_knowledge_base(kb_name)

                new_kb_created = True
                success_count += 1

                # Update the knowledge base list immediately
                if kb_name not in st.session_state.kb_names:
                    st.session_state.kb_names.append(kb_name)

                st.session_state.upload_status = {
                    "type": "success",
                    "message": f"✅ {file_name} processed with {result['chunk_count']} chunks using {embedding_model.split('-')[0].title()} + {chunking_strategy.replace('_', ' ').title()}"
                }
            else:
                logger.error(f"Error processing {file_name}: {result['message']}")
                error_count += 1
                st.session_state.upload_status = {
                    "type": "error",
                    "message": f"❌ Error processing {file_name}: {result['message']}"
                }
        except Exception as e:
            logger.exception(f"Exception while processing {file.name}: {str(e)}")
            error_count += 1
            st.session_state.upload_status = {
                "type": "error",
                "message": f"❌ Error: {str(e)}"
            }

    logger.info(f"Processing complete: {success_count} successful, {error_count} failed")

    # Update knowledge base list if new KBs were created
    if new_kb_created:
        st.session_state.kb_names = get_all_knowledge_base_names()

        # Add a new status message about knowledge bases
        if newly_created_kbs:
            kb_list = ", ".join(newly_created_kbs)
            st.session_state.upload_status = {
                "type": "success",
                "message": f"✅ Created knowledge base(s): {kb_list} using {embedding_model.split('-')[0].title()} embedding + {chunking_strategy.replace('_', ' ').title()} chunking."
            }

    # Turn off direct chat mode if we have successful uploads
    if success_count > 0 and st.session_state.direct_chat_mode:
        logger.info("Turning off direct chat mode due to successful KB creation")
        st.session_state.direct_chat_mode = False

    # Clear processing flag
    st.session_state.processing_file = False


def sidebar():
    st.sidebar.title("RAG Chatbot")
    current_user = st.session_state.get('username', 'admin')
    user_display_name = st.session_state.get('name', current_user)

    # Check if user changed and refresh conversations if needed
    if "last_user" not in st.session_state:
        st.session_state.last_user = current_user
        st.session_state.conversations = get_conversations(current_user)
    elif st.session_state.last_user != current_user:
        # User changed, refresh conversations
        logger.info(f"User changed from {st.session_state.last_user} to {current_user}, refreshing conversations")
        st.session_state.last_user = current_user
        st.session_state.conversations = get_conversations(current_user)

        # Reset current conversation if user has conversations
        if st.session_state.conversations:
            st.session_state.current_conversation_id = st.session_state.conversations[0][0]
            st.session_state.messages = get_messages(st.session_state.current_conversation_id)
        else:
            # Create new conversation for the new user
            new_id = create_conversation(created_by=current_user)
            st.session_state.current_conversation_id = new_id
            st.session_state.conversations = get_conversations(current_user)
            st.session_state.messages = []

        st.rerun()  # Only rerun when user actually changes

    if current_user == "admin":
        st.sidebar.markdown("👑 **Admin View** - All Conversations")
    else:
        st.sidebar.markdown(f"👤 **{user_display_name}'s** Conversations")

    # New Chat Button with better styling
    if st.sidebar.button("✨ New Chat", use_container_width=True, help="Start a new conversation"):
        logger.info(f"Creating new chat for user: {current_user}")
        new_id = create_conversation(created_by=current_user)
        st.session_state.current_conversation_id = new_id
        st.session_state.conversations = get_conversations(current_user)
        st.session_state.messages = []
        st.rerun()

    # Direct Chat Mode Option
    direct_chat_container = st.sidebar.container()
    direct_chat_container.markdown("<div style='margin-top:15px; margin-bottom:5px;'></div>",
                                   unsafe_allow_html=True)

    direct_chat = direct_chat_container.checkbox(
        "💬 Direct Chat Mode (No KB)",
        value=st.session_state.direct_chat_mode,
        help="Chat directly with the AI without using a knowledge base"
    )
    if direct_chat != st.session_state.direct_chat_mode:
        logger.info(f"Changing direct chat mode to: {direct_chat}")
        st.session_state.direct_chat_mode = direct_chat
        new_id = create_conversation(created_by=current_user)
        st.session_state.current_conversation_id = new_id
        st.session_state.conversations = get_conversations(current_user)
        st.session_state.messages = []
        st.rerun()

    st.sidebar.markdown("### 🤖 Chat Model Selection")

    # Get current LLM from session state or default
    model_options = ["__select__"] + [model.value for model in ChatModel]

    # Use "__select__" as default if not previously selected
    current_llm = st.session_state.get("selected_chat_model", "__select__")

    # Render selectbox
    selected_llm = st.sidebar.selectbox(
        "Choose Chat Model:",
        options=model_options,
        format_func=lambda x: {
            "__select__": "🔍 Select a model...",
            "gpt-4o-mini": "🚀 GPT-4o Mini (Fast & Efficient)",
            "deepseek-r1:latest": "🔥 DeepSeek R1 (Local)",
            "llama3.2:1b": "🦙 Llama 3.2 (Local)",
            "gemma2:2b": "🌪️ Gemma (Local)"
        }.get(x, x),
        index=model_options.index(current_llm) if current_llm in model_options else 0,
        help="Select the AI model for conversations"
    )

    # Update session state if selection changed
    if selected_llm != st.session_state.get('selected_chat_model'):
        st.session_state.selected_chat_model = selected_llm
        logger.info(f"Updated selected_chat_model to: {selected_llm}")
        # Save user preference
        current_user = st.session_state.get('username', 'admin')
        set_setting(f"user_{current_user}_chat_model", selected_llm)
        st.sidebar.success(
            f"✅ Switched to {selected_llm.split(':')[0].replace('gpt-', 'GPT-').replace('-', ' ').title()}")
    # API Key input for OpenAI models
    if selected_llm.startswith("gpt"):
        st.sidebar.markdown("### 🔑 OpenAI API Key")

        # Get API key from session state or environment
        if "openai_api_key" not in st.session_state:
            st.session_state.openai_api_key = os.getenv("OPENAI_API_KEY", "")

        api_key_input = st.sidebar.text_input(
            "Enter your OpenAI API Key:",
            value=st.session_state.openai_api_key if st.session_state.openai_api_key and not st.session_state.openai_api_key.startswith(
                "sk-proj-") else "",
            type="password",
            help="Get your API key from https://platform.openai.com/api-keys"
        )

        if api_key_input != st.session_state.openai_api_key:
            st.session_state.openai_api_key = api_key_input
            os.environ["OPENAI_API_KEY"] = api_key_input
            if api_key_input:
                st.session_state.openai_key_configured = True
                st.sidebar.success("✅ API Key updated")
            else:
                st.session_state.openai_key_configured = False

        if not st.session_state.openai_api_key:
            st.sidebar.warning("⚠️ API Key required for OpenAI models")
        else:
            st.session_state.openai_key_configured = True

    # Determine compatible embedding model
    chat_model = st.session_state.get('selected_chat_model')
    logger.info(f"Current chat model in sidebar: {chat_model}")

    if chat_model.startswith("gpt"):
        compatible_embedding = "text-embedding-3-small"
    elif chat_model.startswith("llama"):
        compatible_embedding = "llama3.2:1b"
    elif chat_model.startswith("deepseek"):
        compatible_embedding = "deepseek-r1:latest"
    elif chat_model.startswith("gemma"):
        compatible_embedding = "gemma2:2b"
    else:
        compatible_embedding = "text-embedding-3-small"

    logger.info(f"Determined compatible embedding: {compatible_embedding}")

    # Show current model info
    if chat_model.startswith("gpt"):
        provider = "🔵 OpenAI"
        cost = "💰 Paid API"
    else:
        provider = "🟠 Ollama (Local)"
        cost = "🆓 Free"

    st.sidebar.markdown(f"**Current:** {provider} | {cost}")

    # Knowledge Bases section
    st.sidebar.markdown("""
        <div class="sidebar-section-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
            </svg>
            <span>Knowledge Bases</span>
        </div>
        """, unsafe_allow_html=True)

    # Get compatible knowledge bases
    compatible_kbs = get_compatible_knowledge_bases(compatible_embedding)
    st.session_state.kb_names = compatible_kbs

    # Filter selected KBs to only include compatible ones
    if "selected_kbs" in st.session_state:
        old_selected = st.session_state.selected_kbs.copy()
        st.session_state.selected_kbs = [kb for kb in st.session_state.selected_kbs if kb in compatible_kbs]

        if old_selected != st.session_state.selected_kbs:
            logger.info(f"Filtered KBs from {old_selected} to {st.session_state.selected_kbs}")

    # Update active KB if it's not compatible
    if st.session_state.get('active_kb') and st.session_state.active_kb not in compatible_kbs:
        if compatible_kbs:
            st.session_state.active_kb = compatible_kbs[0]
            logger.info(f"Updated active KB to: {compatible_kbs[0]}")
        # else:
        #     st.session_state.active_kb = None
        #     st.session_state.direct_chat_mode = True
        #     logger.info("No compatible KBs, switching to direct chat mode")

    # Knowledge base selection UI
    if compatible_kbs:
        # Create a multiselect for knowledge bases
        default_selections = st.session_state.selected_kbs if "selected_kbs" in st.session_state else [
            st.session_state.active_kb] if st.session_state.active_kb else []

        # Select all/none buttons
        col1, col2 = st.sidebar.columns([1, 1])

        with col1:
            if st.button("Select All", key="select_all_kbs", use_container_width=True, type="primary"):
                st.session_state.selected_kbs = compatible_kbs.copy()
                st.rerun()

        with col2:
            if st.button("Clear All", key="clear_all_kbs", use_container_width=True):
                st.session_state.selected_kbs = []
                st.rerun()

        # Display the multiselect
        selected_kbs = st.sidebar.multiselect(
            "Select knowledge bases to use",
            options=compatible_kbs,
            default=default_selections,
            key="kb_multiselect",
            label_visibility="collapsed"
        )

        # Update the selected KBs in session state
        if selected_kbs != st.session_state.selected_kbs:
            st.session_state.selected_kbs = selected_kbs

            # If there are selected KBs, set the first one as active
            if selected_kbs:
                st.session_state.active_kb = selected_kbs[0]
                set_active_knowledge_base(selected_kbs[0])
                st.session_state.direct_chat_mode = False
            else:
                # If no KBs selected, switch to direct chat mode
                st.session_state.direct_chat_mode = True

            st.rerun()

        # Display individual KB options
        if st.session_state.selected_kbs:
            st.sidebar.markdown("### Active Knowledge Bases")
            for i, kb_name in enumerate(st.session_state.selected_kbs):
                kb_active = kb_name == st.session_state.active_kb

                col1, col2 = st.sidebar.columns([4, 1])

                with col1:
                    button_label = f"{'📌' if kb_active else '📄'} {kb_name}"
                    if st.button(button_label, key=f"sidebar_activate_{kb_name}_{i}",
                                 use_container_width=True,
                                 type="primary" if kb_active else "secondary"):
                        st.session_state.active_kb = kb_name
                        set_active_knowledge_base(kb_name)
                        st.session_state.direct_chat_mode = False
                        st.rerun()

                with col2:
                    if st.button("❌", key=f"sidebar_remove_{kb_name}_{i}",
                                 help=f"Remove {kb_name} from selection"):
                        st.session_state.selected_kbs.remove(kb_name)
                        if kb_name == st.session_state.active_kb and st.session_state.selected_kbs:
                            st.session_state.active_kb = st.session_state.selected_kbs[0]
                            set_active_knowledge_base(st.session_state.selected_kbs[0])
                        elif not st.session_state.selected_kbs:
                            st.session_state.direct_chat_mode = True
                        st.rerun()
    else:
        st.sidebar.info("No knowledge bases found. Upload documents to create one.")

    # Professional plan indicator
    st.sidebar.markdown("<hr style='margin-top:20px; margin-bottom:15px; border-color:rgba(255,255,255,0.1);'>",
                        unsafe_allow_html=True)
    # st.sidebar.markdown(
    #     "<div style='display:flex; align-items:center;'><span style='color:#a78bfa;margin-right:8px;'>👤</span> <span style='font-weight:500;'>Professional Plan</span></div>",
    #     unsafe_allow_html=True)

    # Chat History Section
    st.sidebar.markdown("""
    <div class="sidebar-section-title" style="margin-top:20px;">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
        <span>Chat History</span>
    </div>
    """, unsafe_allow_html=True)

    for conv_id, title, created_at in st.session_state.conversations:
        col1, col2 = st.sidebar.columns([5, 1])

        with col1:
            is_active = conv_id == st.session_state.current_conversation_id
            button_type = "primary" if is_active else "secondary"
            display_title = f"📝 {title}" if is_active else title

            if st.button(
                    display_title,
                    key=f"conv_{conv_id}",
                    use_container_width=True,
                    type=button_type
            ):
                logger.info(f"Switching to conversation: {conv_id}")
                st.session_state.current_conversation_id = conv_id
                st.session_state.messages = get_messages(conv_id)
                st.rerun()

        with col2:
            if st.button("🗑️", key=f"delete_{conv_id}", help="Delete this conversation"):
                logger.info(f"Deleting conversation: {conv_id}")
                delete_conversation(conv_id)
                st.session_state.conversations = get_conversations(current_user)

                if st.session_state.conversations:
                    if conv_id == st.session_state.current_conversation_id:
                        st.session_state.current_conversation_id = st.session_state.conversations[0][0]
                        st.session_state.messages = get_messages(st.session_state.current_conversation_id)
                else:
                    new_id = create_conversation(created_by=current_user)
                    st.session_state.current_conversation_id = new_id
                    st.session_state.conversations = get_conversations(current_user)
                    st.session_state.messages = []

                st.rerun()

    # LLM Selection Section





def chat_interface():
    # Get current chat model
    current_chat_model = st.session_state.get('selected_chat_model', ChatModel.GPT_4O_MINI.value)

    # Mode indicator with model info
    if st.session_state.direct_chat_mode:
        mode_text = f"Direct Chat: {current_chat_model.replace('gpt-', 'GPT-').replace(':', ' ').title()}"
        mode_class = "openai" if current_chat_model.startswith("gpt") else "ollama"
    else:
        if len(st.session_state.selected_kbs) > 1:
            mode_text = f"Multiple KBs + {current_chat_model.replace('gpt-', 'GPT-').replace(':', ' ').title()}"
        else:
            mode_text = f"KB: {st.session_state.active_kb} + {current_chat_model.replace('gpt-', 'GPT-').replace(':', ' ').title()}"
        mode_class = "rag"

    st.markdown(f"""
    <div class='toggle-container' style='margin-bottom:20px;'>
        <h3 style='margin:0;'>{mode_text}</h3>
        <span class='mode-indicator {mode_class}' style='font-weight:600;'>{mode_class.upper()}</span>
    </div>
    """, unsafe_allow_html=True)

    # If multiple KBs are selected, show them
    if not st.session_state.direct_chat_mode and len(st.session_state.selected_kbs) > 1:
        kb_list = ", ".join([f"'{kb}'" for kb in st.session_state.selected_kbs])
        st.markdown(
            f"<p style='font-size:14px; color:#6b7280; margin-bottom:20px;'>Using knowledge bases: {kb_list}</p>",
            unsafe_allow_html=True)

    # Option to show sources (only in RAG mode) - better styling
    if not st.session_state.direct_chat_mode:
        show_sources = st.checkbox("📄 Show Sources", value=st.session_state.show_sources,
                                   help="Show the source documents for each response")
        if show_sources != st.session_state.show_sources:
            st.session_state.show_sources = show_sources
            st.rerun()

    # Upload documents section (in the main chat window) - improved UI
    # Upload documents section (only show in RAG mode)
    if not st.session_state.direct_chat_mode:
        with st.expander("📁 Upload Documents", expanded=False):
            # Add placeholder to the top of the list
            embedding_options = ["__select__"] + [model.value for model in EmbeddingModel]

            embedding_choice = st.selectbox(
                "🧠 Embedding Model:",
                options=embedding_options,
                format_func=lambda x: {
                    "__select__": "🔍 Select an embedding model...",
                    "text-embedding-3-small": "OpenAI (text-embedding-3-small)",
                    "deepseek-r1:latest": "DeepSeek (deepseek-r1:latest)"
                }.get(x, x),
                index=0,
                help="Choose the embedding model for processing documents"
            )

            if embedding_choice == "__select__":
                st.warning("⚠️ Please select an embedding model to proceed.")
            else:
                if embedding_choice == EmbeddingModel.OPEN_AI.value:
                    chunking_choice = "semantic_percentile"
                    # st.info(f"📌 Chunking strategy: `{chunking_choice}`")
                    st.write(f"Selected Chunking Strategy: `{chunking_choice}`")
                else:
                    chunking_choice = "recursive"
                    # st.info(f"📌 Chunking strategy: `{chunking_choice}`")
                    st.write(f"Selected Chunking Strategy: `{chunking_choice}`")

                # Optionally store or display it
                st.session_state["selected_embedding_model"] = embedding_choice



            # Upload area with better styling
            st.markdown("<div class='upload-area' style='padding:25px;'>", unsafe_allow_html=True)
            uploaded_files = st.file_uploader(
                "Drag & drop PDF or DOCX files here",
                type=["pdf", "docx"],
                accept_multiple_files=True,
                key="main_file_uploader",
                label_visibility="collapsed"
            )
            st.markdown("""
            <div style='text-align:center; margin-top:10px; font-size:14px; color:#6b7280;'>
                Supported formats: PDF, DOCX
            </div>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # Display upload status if any - better styling
            if st.session_state.upload_status:
                status_type = st.session_state.upload_status["type"]
                status_msg = st.session_state.upload_status["message"]
                icon = "✅" if status_type == "success" else "❌"
                st.markdown(
                    f"<div class='upload-status {status_type}' style='display:flex; align-items:center;'><span style='margin-right:5px;'>{icon}</span> {status_msg}</div>",
                    unsafe_allow_html=True)

            # Auto-process files when uploaded
            if uploaded_files and not st.session_state.processing_file:
                with st.spinner("Processing files..."):
                    process_uploaded_files(uploaded_files, embedding_choice, chunking_choice)

    # Knowledge Base Selector (only show in RAG mode)
    if not st.session_state.direct_chat_mode and st.session_state.kb_names and len(st.session_state.kb_names) > 0:
        with st.expander("📚 Select Knowledge Base", expanded=True):
            st.write("### Available Knowledge Bases")
            st.write("Select and activate knowledge bases for your questions:")

            # Use a dropdown for selecting the active KB
            selected_kb = st.selectbox(
                "Set Active Knowledge Base:",
                options=st.session_state.kb_names,
                index=st.session_state.kb_names.index(
                    st.session_state.active_kb) if st.session_state.active_kb in st.session_state.kb_names else 0,
                key="kb_dropdown"
            )

            if st.button("🎯 Activate Selected KB", key="activate_from_dropdown"):
                st.session_state.active_kb = selected_kb
                st.session_state.direct_chat_mode = False
                if selected_kb not in st.session_state.selected_kbs:
                    st.session_state.selected_kbs.append(selected_kb)
                set_active_knowledge_base(selected_kb)
                st.rerun()

            # Multi-select for choosing which KBs to use
            multi_select = st.multiselect(
                "Select Knowledge Bases to Use:",
                options=st.session_state.kb_names,
                default=st.session_state.selected_kbs,
                key="kb_multiselect_main"
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button("💾 Save Selection", key="save_kb_selection"):
                    st.session_state.selected_kbs = multi_select
                    if not multi_select:
                        st.session_state.direct_chat_mode = True
                    elif st.session_state.active_kb not in multi_select and multi_select:
                        st.session_state.active_kb = multi_select[0]
                        set_active_knowledge_base(multi_select[0])
                    st.rerun()

            with col2:
                if st.button("🔄 Select All KBs", key="select_all_kbs_main"):
                    st.session_state.selected_kbs = st.session_state.kb_names.copy()
                    if not st.session_state.active_kb and st.session_state.selected_kbs:
                        st.session_state.active_kb = st.session_state.selected_kbs[0]
                        set_active_knowledge_base(st.session_state.selected_kbs[0])
                    st.session_state.direct_chat_mode = False
                    st.rerun()

    # Suggested prompts (only show when no messages yet AND not in direct mode)
    if not st.session_state.messages and not st.session_state.direct_chat_mode:
        st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
        st.markdown("### Example Questions to Get Started:")

        # Show suggestions in columns
        col1, col2 = st.columns(2)
        suggestions = get_suggested_prompts()
        user_name = st.session_state.get('name', 'Anonymous')
        with col1:
            for i in range(0, len(suggestions), 2):
                if i < len(suggestions):
                    if st.button(f"💡 {suggestions[i]}", key=f"sugg_{i}", use_container_width=True):
                        user_name = st.session_state.get('name', 'Anonymous')
                        message_id = add_message(st.session_state.current_conversation_id, "user", suggestions[i],
                                                 user_name)
                        st.session_state.messages = get_messages(st.session_state.current_conversation_id)
                        title = suggestions[i][:30] + ('...' if len(suggestions[i]) > 30 else '')
                        update_conversation_title(st.session_state.current_conversation_id, title)
                        st.session_state.is_thinking = True
                        st.rerun()

        with col2:
            for i in range(1, len(suggestions), 2):
                if i < len(suggestions):
                    if st.button(f"💡 {suggestions[i]}", key=f"sugg_{i}", use_container_width=True):
                        message_id = add_message(st.session_state.current_conversation_id, "user", suggestions[i],
                                                 user_name)
                        st.session_state.messages = get_messages(st.session_state.current_conversation_id)
                        title = suggestions[i][:30] + ('...' if len(suggestions[i]) > 30 else '')
                        update_conversation_title(st.session_state.current_conversation_id, title)
                        st.session_state.conversations = get_conversations()
                        logger.info(f"Updated conversation title to: {title}")
                        st.session_state.is_thinking = True
                        st.rerun()

        # Chat messages - with improved styling
    message_container = st.container()

    with message_container:
        # Display existing messages
        for msg_id, role, content, user_name, timestamp in st.session_state.messages:
            if role == "system":
                continue  # Skip system messages
            formatted_time = timestamp.strftime("%H:%M")

            with st.chat_message(role):
                if user_name and user_name != role:
                    st.markdown(f"**{user_name}:**")
                st.write(content)
                st.markdown(
                    f"<div style='font-size:11px; color:#6b7280; text-align:right; margin-top:5px;'>{formatted_time}</div>",
                    unsafe_allow_html=True)

                # Show sources for assistant messages (only in RAG mode) - improved styling
                # In chat_interface() function where it displays sources:

                # Show sources for assistant messages (only in RAG mode) - improved styling with tabs
                if role == "assistant" and st.session_state.show_sources and not st.session_state.direct_chat_mode:
                    sources = get_sources(msg_id)
                    if sources:
                        with st.expander("📄 Sources", expanded=False):
                            # Create tabs for different source views
                            source_tabs = st.tabs(["📚 Query-Relevant Sources", "🗂️ Selected Knowledge Bases"])

                            # First tab: Query-relevant sources (sorted by relevance)
                            with source_tabs[0]:
                                # Group sources by unique document/page to avoid duplicates
                                unique_sources = {}
                                for source in sources:
                                    key = (source.get('source', 'Unknown'), source.get('page', 0))
                                    # Only keep the source with the highest score
                                    if key not in unique_sources or source.get('score', 0) > unique_sources[
                                        key].get('score', 0):
                                        unique_sources[key] = source

                                # Sort by relevance score
                                sorted_sources = sorted(unique_sources.values(), key=lambda x: x.get('score', 0),
                                                        reverse=True)

                                for i, source in enumerate(sorted_sources):
                                    source_name = source.get('source', 'Unknown')
                                    page_number = source.get('page', 0)
                                    score = source.get('score', 0)
                                    kb_name = source.get('kb_name', 'Unknown KB')
                                    score_percentage = int(score * 100)

                                    # Better source display with color-coded relevance
                                    relevance_color = "#10b981"  # Green for high relevance
                                    if score_percentage < 70:
                                        relevance_color = "#f59e0b"  # Yellow for medium relevance
                                    if score_percentage < 50:
                                        relevance_color = "#ef4444"  # Red for low relevance

                                    st.markdown(f"""
                                    <div style='margin-bottom:12px; padding:10px; border-radius:6px; background-color:#f9fafb; border-left:4px solid {relevance_color};'>
                                        <div style='font-weight:600; font-size:15px;'>{i + 1}. {source_name}</div>
                                        <div style='display:flex; flex-wrap:wrap; justify-content:space-between; margin-top:5px;'>
                                            <span style='font-weight:500; margin-right:8px;'>KB: {kb_name}</span>
                                            <span style='background:#5b2d91; color:white; padding:2px 8px; border-radius:12px; font-size:12px; margin-right:8px;'>Page {page_number}</span>
                                            <span style='color:{relevance_color}; font-weight:500;'>Relevance: {score_percentage}%</span>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)

                            # Second tab: Group by knowledge base
                            with source_tabs[1]:
                                # Group sources by knowledge base
                                kb_groups = {}
                                for source in sources:
                                    kb_name = source.get('kb_name', 'Unknown KB')
                                    if kb_name not in kb_groups:
                                        kb_groups[kb_name] = []
                                    kb_groups[kb_name].append(source)

                                # Sort knowledge bases alphabetically for consistent display
                                for kb_name in sorted(kb_groups.keys()):
                                    kb_sources = kb_groups[kb_name]

                                    # Deduplicate sources within this KB
                                    unique_kb_sources = {}
                                    for source in kb_sources:
                                        key = (source.get('source', 'Unknown'), source.get('page', 0))
                                        if key not in unique_kb_sources or source.get('score', 0) > \
                                                unique_kb_sources[key].get('score', 0):
                                            unique_kb_sources[key] = source

                                    # Sort by source name and page
                                    sorted_kb_sources = sorted(unique_kb_sources.values(),
                                                               key=lambda x: (x.get('source', 'Unknown'),
                                                                              x.get('page', 0)))

                                    # Only display KB section if it has sources
                                    if sorted_kb_sources:
                                        st.markdown(f"### {kb_name}")

                                        for i, source in enumerate(sorted_kb_sources):
                                            source_name = source.get('source', 'Unknown')
                                            page_number = source.get('page', 0)
                                            score = source.get('score', 0)
                                            score_percentage = int(score * 100)

                                            # Color code relevance
                                            relevance_color = "#10b981"  # Green for high relevance
                                            if score_percentage < 70:
                                                relevance_color = "#f59e0b"  # Yellow for medium relevance
                                            if score_percentage < 50:
                                                relevance_color = "#ef4444"  # Red for low relevance

                                            st.markdown(f"""
                                            <div style='margin-bottom:8px; padding:8px; border-radius:4px; background-color:#f3f0f9;'>
                                                <div style='font-weight:500;'>{i + 1}. {source_name}</div>
                                                <div style='display:flex; justify-content:space-between; font-size:13px;'>
                                                    <span>Page {page_number}</span>
                                                    <span style='color:{relevance_color}; font-weight:500;'>Relevance: {score_percentage}%</span>
                                                </div>
                                            </div>
                                            """, unsafe_allow_html=True)

                                        st.markdown("---")
        # Display thinking indicator with animation
        if st.session_state.is_thinking:
            with st.chat_message("assistant"):
                st.markdown("""
                <div style='display:flex; align-items:center;'>
                    <div class='thinking-dot'></div>
                    <div class='thinking-dot'></div>
                    <div class='thinking-dot'></div>
                    <span>Thinking...</span>
                </div>
                """, unsafe_allow_html=True)

        # Chat input with better styling
    user_input = st.chat_input("Type your message here...")
    if current_chat_model == '__select__':
        st.error("Please Select Chat Model From Sidebar")
    if user_input:
        logger.info(f"Received user input: {user_input[:50]}...")
        user_name = st.session_state.get('name', 'Anonymous')  # Use 'name' not 'username'
        logger.info(f"Adding message from user: {user_name}")

        # Get the authenticated user's name


        # Add user message with name
        message_id = add_message(
            st.session_state.current_conversation_id,
            "user",  # Keep for LangChain compatibility
            user_input,
            user_name  # This should be the actual user name like "user1"
        )

        # Add user message to database

        # Update conversation title if this is the first message
        if len(st.session_state.messages) == 0:
            # Use first few words (up to 30 chars) as the title
            title = user_input[:30] + ('...' if len(user_input) > 30 else '')
            update_conversation_title(st.session_state.current_conversation_id, title)
            st.session_state.conversations = get_conversations()
            logger.info(f"Updated conversation title to: {title}")

        # Set thinking state and refresh
        st.session_state.messages = get_messages(st.session_state.current_conversation_id)
        st.session_state.is_thinking = True
        st.rerun()


def handle_ai_response():
    """Process the AI response when in thinking state"""
    if st.session_state.is_thinking and st.session_state.messages:
        # Get the last user message
        last_message = None

        for msg_id, role, content, user_name, timestamp in st.session_state.messages:
            if role == "user":
                last_message = content

        if not last_message:
            logger.warning("No user message found to respond to")
            st.session_state.is_thinking = False
            return

        logger.info(f"Processing response to: {last_message[:50]}...")

        # Get selected chat model
        chat_model = st.session_state.get('selected_chat_model', 'gpt-4o-mini')
        logger.info(f"Using chat model: {chat_model}")

        # Check if we're in direct chat mode
        if st.session_state.direct_chat_mode:
            logger.info("Using direct chat mode")
            try:
                # Query directly with selected model
                response = direct_openai_query(
                    conversation_id=st.session_state.current_conversation_id,
                    query=last_message,
                    model_name=chat_model
                )

                logger.info("Direct response received")
                st.session_state.messages = get_messages(st.session_state.current_conversation_id)
                st.session_state.is_thinking = False
                st.rerun()
            except Exception as e:
                logger.exception(f"Error in direct chat mode: {str(e)}")
                error_message = f"Error processing query: {str(e)}"
                add_message(st.session_state.current_conversation_id, "assistant", error_message, "AI Assistant")
                st.session_state.messages = get_messages(st.session_state.current_conversation_id)
                st.session_state.is_thinking = False
                st.rerun()

        # RAG mode with knowledge base(s)
        elif st.session_state.selected_kbs:
            try:
                # Get compatible embedding model based on selected chat model
                # chat_model = st.session_state.get('selected_chat_model', 'gpt-4o-mini')

                if chat_model.startswith("gpt"):
                    embedding_model = "text-embedding-3-small"
                elif chat_model.startswith("llama"):
                    embedding_model = "llama3.2:1b"
                elif chat_model.startswith("deepseek"):
                    embedding_model = "deepseek-r1:latest"
                elif chat_model.startswith("gemma"):
                    embedding_model = "gemma2:2b"
                else:
                    embedding_model = "text-embedding-3-small"

                retrieval_k = 4

                logger.info(f"Using embedding model: {embedding_model}")
                logger.info(f"Using chat model: {chat_model}")

                # Use selected knowledge bases and chat model
                if len(st.session_state.selected_kbs) > 0:
                    logger.info(f"Using selected knowledge bases: {', '.join(st.session_state.selected_kbs)}")
                    response = process_query(
                        conversation_id=st.session_state.current_conversation_id,
                        query=last_message,
                        kb_names=st.session_state.selected_kbs,
                        embedding_model=embedding_model,
                        chat_model=chat_model,
                        retrieval_k=retrieval_k
                    )

                logger.info("RAG response received")
                st.session_state.messages = get_messages(st.session_state.current_conversation_id)
                st.session_state.is_thinking = False
                st.rerun()
            except Exception as e:
                logger.exception(f"Error in RAG mode: {str(e)}")

                # Fallback to direct chat if KB error
                if "Knowledge base" in str(e) and "does not exist" in str(e):
                    try:
                        logger.info("Falling back to direct chat mode due to KB error")
                        st.session_state.direct_chat_mode = True
                        direct_response = direct_openai_query(
                            conversation_id=st.session_state.current_conversation_id,
                            query=last_message,
                            model_name=chat_model
                        )
                        st.session_state.messages = get_messages(st.session_state.current_conversation_id)
                        st.session_state.is_thinking = False
                        st.rerun()
                        return
                    except Exception as fallback_error:
                        logger.exception(f"Error in fallback mode: {str(fallback_error)}")

                error_message = f"Error processing query: {str(e)}"
                add_message(st.session_state.current_conversation_id, "assistant", error_message, "AI Assistant")
                st.session_state.messages = get_messages(st.session_state.current_conversation_id)
                st.session_state.is_thinking = False
                st.rerun()

        else:
            # No knowledge base selected - switch to direct chat mode
            logger.info("No knowledge base selected, switching to direct chat mode")
            st.session_state.direct_chat_mode = True

            try:
                # Use selected chat model instead of settings
                response = direct_openai_query(
                    conversation_id=st.session_state.current_conversation_id,
                    query=last_message,
                    model_name=chat_model
                )

                st.session_state.messages = get_messages(st.session_state.current_conversation_id)
                st.session_state.is_thinking = False
                st.rerun()
            except Exception as e:
                logger.exception(f"Error in direct fallback mode: {str(e)}")
                error_message = f"Error processing query: {str(e)}"
                add_message(st.session_state.current_conversation_id, "assistant", error_message, "AI Assistant")
                st.session_state.messages = get_messages(st.session_state.current_conversation_id)
                st.session_state.is_thinking = False
                st.rerun()


def main():
    logger.info("Application starting")

    # Apply custom CSS
    # add_custom_css()
    is_authenticated = authenticate_user()
    if is_authenticated:
    # Initialize session state
        init_session_state()

        # Render sidebar
        sidebar()

        # Check if OpenAI API key is configured
        if not st.session_state.openai_key_configured:
            logger.warning("OpenAI API key not configured, showing API key screen")
            # api_key_required_screen()
        else:
            chat_interface()

            # Process AI response if in thinking state
            if st.session_state.is_thinking:
                handle_ai_response()

        logger.debug("UI rendering complete")


if __name__ == "__main__":
    main()