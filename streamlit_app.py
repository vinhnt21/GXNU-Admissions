import streamlit as st
import tempfile
import os
import time
import random
from typing import List
from langchain_core.documents import Document

# Import our modules
from agent.graph import get_answer
from agent.vectorstore import LANGCHAIN_VECTOR_STORES, load_document_and_chunk
from config import CONFIG
from utils import log

def add_documents_to_vectorstore(documents: List[Document], index_name: str) -> bool:
    """
    Add documents to the specified Pinecone vectorstore.
    
    Args:
        documents: List of Document objects to add
        index_name: Name of the Pinecone index to add documents to
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if index_name not in LANGCHAIN_VECTOR_STORES:
            log.error(f"Vectorstore for index '{index_name}' not found")
            return False
            
        vectorstore = LANGCHAIN_VECTOR_STORES[index_name]
        
        # Extract texts and metadatas from documents
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        
        # Add documents to vectorstore
        vectorstore.add_texts(texts=texts, metadatas=metadatas)
        
        log.success(f"Successfully added {len(documents)} documents to index '{index_name}'")
        return True
        
    except Exception as e:
        log.error(f"Error adding documents to vectorstore '{index_name}': {e}")
        return False

def initialize_session_state():
    """Initializes the session state for the chat application."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "processing" not in st.session_state:
        st.session_state.processing = False
    
    # Add welcome message if messages is empty
    if len(st.session_state.messages) == 0:
        welcome_msg = """
        🎉 **Welcome to Guangxi Normal University Admission Chatbot!**

        I am your AI assistant, ready to answer all questions about the 2025 admission. You can chat with me in Chinese or English.
        
        💡 You can ask any questions, for example:
        - *What are the admission requirements for international students?*
        - *How much is the tuition fee?*
        - *What majors does the university offer?*
        - *What are the admission requirements for international students?*
        
        **Let's start the conversation!**
        """
        st.session_state.messages = [{"role": "assistant", "content": welcome_msg}]

def reset_chat():
    """Resets the chat conversation."""
    st.session_state.messages = []
    st.session_state.processing = False
    # Re-initialize will add welcome message
    initialize_session_state()

def render_sidebar():
    """Renders the sidebar for document management and app info."""
    with st.sidebar:
        st.header("📄 Document Management")
        
        # --- Database selection ---
        database_options = {config.human_description: config.pinecone_index_name 
                            for config in CONFIG.RETRIEVER_TOOL_CONFIGS}
        
        selected_db_description = st.selectbox(
            "Select database to add documents:",
            options=list(database_options.keys()),
            key="db_selector"
        )
        selected_db_name = database_options[selected_db_description]
        st.info(f"Selected: **{selected_db_description}**")

        # --- File upload ---
        uploaded_file = st.file_uploader(
            "Upload .txt file to update bot knowledge:",
            type=['txt'],
            help="Only supports .txt files, each file contains a knowledge topic."
        )
        
        if st.button("📤 Add Document", disabled=not uploaded_file, use_container_width=True):
            if uploaded_file is not None:
                try:
                    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt", encoding="utf-8") as tmp_file:
                        tmp_file.write(uploaded_file.getvalue().decode("utf-8"))
                        tmp_file_path = tmp_file.name
                    
                    with st.spinner("Analyzing and loading document..."):
                        documents = load_document_and_chunk(tmp_file_path)
                        success = add_documents_to_vectorstore(documents, selected_db_name)
                    
                    if success:
                        st.success(f"✅ Successfully added {len(documents)} text chunks to the database!")
                    else:
                        st.error("❌ An error occurred while adding the document!")
                    
                    os.unlink(tmp_file_path) # Clean up
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

        st.markdown("---")

        # --- App Info ---
        st.header("ℹ️ Additional Information")
        with st.expander("📖 Usage Guide"):
            st.markdown("""
            - **Chat:** Enter your question in the chat box below and press Enter.
            - **Add Documents:** Use this sidebar to select a database and upload `.txt` files.
            - **Clear Conversation:** Press the button below to start over.
            """)
        
        with st.expander("❓ Sample Questions"):
            st.markdown("""
            - *What are the admission requirements for international students?*
            - *How much is the tuition fee?*
            - *What majors does the university offer?*
            - *What is the history of the university?*
            - *Are there scholarship opportunities?*
            """)

        st.markdown("---")
        if st.button("🗑️ Clear Conversation", use_container_width=True, type="secondary"):
            reset_chat()
            st.rerun()

def render_chat_interface():
    """Renders the main chat interface, handles user input and bot responses."""
    st.header("💬 Chat with AI Assistant")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            # Use a special indicator for "typing"
            if message.get("typing"):
                # Random friendly messages
                search_messages = [
                    "🔍 **I'm searching for information for you...**",
                    "📚 **Looking up data...**",
                    "💭 **I'm thinking about your question...**",
                    "🔎 **Finding the most relevant information...**",
                    "📖 **I'm reading documents to answer you...**"
                ]
                
                friendly_endings = [
                    "*Please wait a moment! 😊*",
                    "*Just a second! 🤗*",
                    "*Processing... 🤔*",
                    "*Almost ready with the answer! ✨*",
                    "*I'll answer right away! 💫*"
                ]
                
                search_msg = random.choice(search_messages)
                ending_msg = random.choice(friendly_endings)
                
                st.markdown(f"""
                {search_msg}
                
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
                
                {ending_msg}
                """, unsafe_allow_html=True)
            else:
                st.markdown(message["content"])

    # Check if we need to process a typing message
    if (len(st.session_state.messages) > 0 and 
        st.session_state.messages[-1].get("typing") and 
        not st.session_state.get("processing", False)):
        
        # Set processing flag to prevent duplicate processing
        st.session_state.processing = True
        
        user_question = st.session_state.messages[-2]["content"]
        
        try:
            # Simulate processing time for better UX
            time.sleep(random.uniform(1.0, 2.5))
            
            # Get the actual answer from the agent
            response = get_answer(user_question)
            
            # Replace the typing indicator with the real response
            st.session_state.messages[-1] = {"role": "assistant", "content": response}
            
        except Exception as e:
            error_msg = f"😔 Sorry, I encountered an issue processing your request. Please try again later.\n\n*Error details: {str(e)}*"
            st.session_state.messages[-1] = {"role": "assistant", "content": error_msg}
        
        # Clear processing flag
        st.session_state.processing = False
        st.rerun()

    # Handle user input
    if prompt := st.chat_input("Enter your question here... / 在这里输入您的问题..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Add a typing indicator immediately
        st.session_state.messages.append({"role": "assistant", "typing": True})
        
        # Clear any previous processing flag
        st.session_state.processing = False
        st.rerun()

def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(
        page_title="Guangxi Normal University Admission Chatbot",
        page_icon="🎓",
        layout="wide"
    )

    # --- Custom CSS for a modern chat look ---
    st.markdown("""
    <style>
        /* General layout */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        /* Chat bubble styling */
        .stChatMessage {
            border-radius: 18px;
            padding: 16px 20px;
            margin-bottom: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border: none;
        }
        
        /* Typing indicator (bouncing dots) */
        .typing-indicator {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 18px;
            opacity: 0.8;
        }
        .typing-indicator span {
            height: 8px;
            width: 8px;
            float: left;
            margin: 0 2px;
            display: block;
            border-radius: 50%;
            opacity: 0.4;
            animation: bounce 1s infinite;
        }
        .typing-indicator span:nth-of-type(2) { animation-delay: 0.2s; }
        .typing-indicator span:nth-of-type(3) { animation-delay: 0.4s; }
        
        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1.0); }
        }
    </style>
    """, unsafe_allow_html=True)
    
    # --- Page Header ---
    col_logo, col_title = st.columns([1, 8])
    with col_logo:
        st.image("static/logo.png", width=80)
    with col_title:
        st.title("Guangxi Normal University")
        st.subheader("Admission Counseling Chatbot")
    
    st.markdown("---")

    initialize_session_state()
    render_sidebar()
    render_chat_interface()

if __name__ == "__main__":
    main()