import streamlit as st
import os
import sys
import time
import json
import uuid
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb

# Ensure we can import from src directory
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
try:
    from generate import call_llm, build_context_prompt
except ImportError:
    st.error("Could not import generate.py. Make sure app.py is in the root directory and src/generate.py exists.")
    st.stop()

# --- Config & Setup ---
st.set_page_config(page_title="LexFin AI", page_icon="🏦", layout="wide")

# Minimal Custom CSS for ChatGPT-like feel
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* GPT-like typography */
    body, p, div, span, button {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #1E1E2E;
    }
    
    .sidebar-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #F8F8F2;
        margin-bottom: 1rem;
    }

    /* Main Chat Area */
    .hero-title {
        text-align: center;
        font-size: 2.5rem;
        font-weight: 700;
        margin-top: 5vh;
        margin-bottom: 2rem;
        color: #F8F8F2;
    }
    
    /* Example Buttons */
    .stButton > button {
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        transition: all 0.2s ease;
        background-color: transparent;
        text-align: left;
    }
    .stButton > button:hover {
        border-color: #38bdf8;
        background-color: rgba(56, 189, 248, 0.1);
    }
    
    /* History Buttons */
    .history-btn > button {
        border: none !important;
        background-color: transparent !important;
        text-align: left !important;
        padding-left: 0 !important;
        color: #A6ACCD !important;
        font-size: 0.9rem !important;
    }
    .history-btn > button:hover {
        color: #F8F8F2 !important;
        background-color: rgba(255,255,255,0.05) !important;
    }

    strong {
        color: #38bdf8 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- History Persistence ---
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "data", "chat_history.json")

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_history(history):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_history()

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = str(uuid.uuid4())
    st.session_state.messages = []

# Update active session in state
if st.session_state.current_session_id in st.session_state.chat_history:
    st.session_state.messages = st.session_state.chat_history[st.session_state.current_session_id]
else:
    st.session_state.messages = []

# --- Resources ---
@st.cache_resource
def load_resources():
    VECTORDB_DIR = os.path.join(os.path.dirname(__file__), "data", "vectordb")
    db_path = Path(VECTORDB_DIR)
    if not db_path.exists():
        return None, None
    model = SentenceTransformer("all-MiniLM-L6-v2")
    client_chroma = chromadb.PersistentClient(path=str(db_path))
    collection = client_chroma.get_collection(name="rag_documents")
    return model, collection

model, collection = load_resources()
if model is None:
    st.error("Vector database not found. Please run Step 3 (ingest/embed) first.")
    st.stop()

# --- Sidebar ---
with st.sidebar:
    st.markdown('<div class="sidebar-title">🏦 LexFin AI</div>', unsafe_allow_html=True)
    
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.current_session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()
        
    st.markdown("---")
    st.markdown("**Chat History**")
    
    history_keys = list(st.session_state.chat_history.keys())
    for session_id in reversed(history_keys):
        session_data = st.session_state.chat_history[session_id]
        if not session_data:
            continue
            
        title = "New Chat"
        for msg in session_data:
            if msg["role"] == "user":
                title = msg["content"][:30] + ("..." if len(msg["content"]) > 30 else "")
                break
                
        # Use a container to apply specific CSS class
        with st.container():
            st.markdown('<div class="history-btn">', unsafe_allow_html=True)
            if st.button(f"💬 {title}", key=f"session_{session_id}", use_container_width=True):
                st.session_state.current_session_id = session_id
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
    st.markdown("---")
    st.markdown("**Settings**")
    use_routing = st.toggle("Enable Query Routing", value=True)
    use_corrective = st.toggle("Enable Corrective RAG", value=True)
    
    raw_dir = os.path.join(os.path.dirname(__file__), "data", "raw")
    available_pdfs = [f for f in os.listdir(raw_dir) if f.endswith('.pdf')] if os.path.exists(raw_dir) else []
    
    with st.expander(f"📚 {len(available_pdfs)} Documents Loaded"):
        for pdf in available_pdfs:
            st.caption(f"- {pdf}")

# --- Main Layout ---
if not st.session_state.messages:
    st.markdown('<div class="hero-title">How can I help you today?</div>', unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #A6ACCD;'>Ask questions about Ghana's financial regulations, banking capital, and cybersecurity.</p>", unsafe_allow_html=True)
    
    st.write("")
    st.write("")
    
    col1, col2 = st.columns(2)
    examples = [
        "What is the minimum capital adequacy ratio for a bank?",
        "What are the requirements for opening a mobile money account?",
        "What is the penalty for non-compliance with the minimum capital requirement?",
        "What guidelines does the GSMA provide regarding mobile money interoperability?"
    ]
    
    for i, ex in enumerate(examples):
        with (col1 if i % 2 == 0 else col2):
            if st.button(ex, key=f"ex_{i}", use_container_width=True):
                st.session_state.example_clicked = ex
                st.rerun()
else:
    # Display history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                st.markdown("**LexFin AI**")
            st.markdown(msg["content"])
            if "sources" in msg and msg["sources"]:
                with st.expander("View Sources"):
                    for source in msg["sources"]:
                        st.markdown(f"- {source}")

# Get input from chat_input OR example button
prompt = st.chat_input("Message the Assistant...")
if "example_clicked" in st.session_state:
    prompt = st.session_state.example_clicked
    del st.session_state.example_clicked

if prompt:
    # 1. Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Save to history file
    st.session_state.chat_history[st.session_state.current_session_id] = st.session_state.messages
    save_history(st.session_state.chat_history)
    
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Generate response
    with st.chat_message("assistant"):
        st.markdown("**LexFin AI**")
        with st.spinner("Analyzing regulations..."):
            try:
                query = prompt
                reformulated = False
                routing_filter = None
                
                if use_routing and available_pdfs:
                    pdf_list_str = "\n".join([f"- {pdf}" for pdf in available_pdfs])
                    routing_prompt = (
                        f"Given this question: '{query}' and this list of available documents:\n"
                        f"{pdf_list_str}\n\n"
                        "Which document(s) is this question most likely about? Reply with EXACT filename(s) (comma-separated if multiple) or ALL if unclear. Output ONLY the filename(s) or ALL without quotes or preamble."
                    )
                    route_text = call_llm(routing_prompt, model="gemini-3.5-flash-lite")
                    
                    if "ALL" not in route_text.upper():
                        selected = [f for f in available_pdfs if f in route_text]
                        if selected:
                            if len(selected) == 1:
                                routing_filter = {"source_filename": selected[0]}
                            else:
                                routing_filter = {"source_filename": {"$in": selected}}

                query_embedding = model.encode(query).tolist()
                
                search_kwargs = {"query_embeddings": [query_embedding], "n_results": 15, "include": ["metadatas", "documents", "distances"]}
                if routing_filter:
                    search_kwargs["where"] = routing_filter
                    
                results = collection.query(**search_kwargs)
                
                if not results["ids"][0]:
                    st.error("No context found in the database.")
                    st.stop()
                    
                metadatas = results["metadatas"][0]
                documents = results["documents"][0]
                
                context_prompt, retrieved_sources = build_context_prompt(query, documents, metadatas)
                
                if use_corrective:
                    check_prompt = f"Given this question: '{query}' and these chunks:\n{context_prompt}\n\nAre they sufficient to answer confidently? Reply YES or NO with one-line reason."
                    check_text = call_llm(check_prompt, model="gemini-3.5-flash-lite")
                    
                    if check_text.upper().startswith("NO"):
                        reformulate_prompt = f"The user asked: '{prompt}'. The initial retrieval was insufficient. Rewrite this query into a single, more descriptive search query that might yield better document matches. Output ONLY the new query string without quotes or preamble."
                        query = call_llm(reformulate_prompt, model="gemini-3.5-flash-lite")
                        reformulated = True
                        
                        query_embedding = model.encode(query).tolist()
                        search_kwargs["query_embeddings"] = [query_embedding]
                        results = collection.query(**search_kwargs)
                        
                        if results["ids"][0]:
                            metadatas = results["metadatas"][0]
                            documents = results["documents"][0]
                            context_prompt, retrieved_sources = build_context_prompt(query, documents, metadatas)

                system_prompt = (
                    "Answer ONLY using the provided context. If the context does not contain the answer, "
                    "say so explicitly. Always cite which source document and page number your answer comes from. Format cleanly with markdown."
                )
                
                answer = call_llm(context_prompt, system=system_prompt, model="gemini-3.5-flash")
                
                detailed_sources = []
                for i in range(len(documents)):
                    m = metadatas[i]
                    src = m.get('source_filename', 'Unknown')
                    pg = m.get('page_number', 'Unknown')
                    sec = m.get('section_title') or 'Unknown'
                    detailed_sources.append(f"**{src}** (Page {pg}) - *{sec}*")
                
                unique_detailed_sources = list(dict.fromkeys(detailed_sources))

                full_response = answer
                if reformulated:
                    full_response = f"*(Note: Query was reformulated to: '{query}' for better results)*\n\n" + full_response
                
                st.markdown(full_response)
                with st.expander("View Sources"):
                    for s in unique_detailed_sources:
                        st.markdown(f"- {s}")
                        
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response,
                    "sources": unique_detailed_sources
                })
                
                # Save updated history
                st.session_state.chat_history[st.session_state.current_session_id] = st.session_state.messages
                save_history(st.session_state.chat_history)
                
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "Quota" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    st.error("API Rate Limit (429) hit. Please wait a minute and try again.")
                else:
                    st.error(f"An error occurred: {err_msg}")
