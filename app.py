import streamlit as st
import os
import sys
import time
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
st.set_page_config(page_title="Ghana Financial Regulations Assistant", page_icon="🏦", layout="wide")

# Minimal Custom CSS (The rest is handled properly by .streamlit/config.toml)
st.markdown("""
<style>
    /* Hide Streamlit default elements for a cleaner look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Elegant Title */
    h1 {
        background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700 !important;
        letter-spacing: -1px;
        padding-bottom: 0.5rem;
    }
    
    /* Subtitle styling */
    .stMarkdown p {
        font-size: 1.05rem;
    }
    
    /* Force buttons to wrap text so they don't truncate */
    .stButton > button {
        white-space: normal !important;
        height: auto !important;
        min-height: 80px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        border-color: #38bdf8;
        transform: translateY(-2px);
    }
    
    /* Highlighted terms (bold) */
    strong {
        color: #38bdf8 !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("Ghana Financial Regulations Assistant 🏦")
st.markdown("Ask questions about Ghana's mobile money industry, banking capital, and cybersecurity directives.")

@st.cache_resource
def load_resources():
    VECTORDB_DIR = os.path.join(os.path.dirname(__file__), "data", "vectordb")
    db_path = Path(VECTORDB_DIR)
    
    if not db_path.exists():
        return None, None
        
    model = SentenceTransformer("BAAI/bge-large-en-v1.5")
    client_chroma = chromadb.PersistentClient(path=str(db_path))
    collection = client_chroma.get_collection(name="rag_documents")
    return model, collection

model, collection = load_resources()
if model is None:
    st.error("Vector database not found. Please run Step 3 (ingest/embed) first.")
    st.stop()

# --- Sidebar ---
with st.sidebar:
    st.header("Settings")
    use_routing = st.toggle("Enable Query Routing (Step 8)", value=True, help="Filters search to specific documents using Gemini before retrieval.")
    use_corrective = st.toggle("Enable Corrective RAG (Step 7)", value=True, help="Self-reflects on retrieved chunks and reformulates query if insufficient.")
    
    st.header("Source Documents")
    
    raw_dir = os.path.join(os.path.dirname(__file__), "data", "raw")
    if os.path.exists(raw_dir):
        available_pdfs = [f for f in os.listdir(raw_dir) if f.endswith('.pdf')]
    else:
        available_pdfs = []
        
    st.markdown(f"**{len(available_pdfs)} Documents Loaded**")
    with st.expander("View Document List"):
        for pdf in available_pdfs:
            st.markdown(f"- {pdf}")
    
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# --- Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Example Questions ---
if not st.session_state.messages:
    st.subheader("Try asking:")
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
                # When clicked, we add it to a temporary state and rerun to trigger chat input
                st.session_state.example_clicked = ex
                st.rerun()

# --- Chat Interface ---
# Display history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "sources" in msg and msg["sources"]:
            with st.expander("Sources"):
                for source in msg["sources"]:
                    st.markdown(f"- {source}")

# Get input from chat_input OR example button
prompt = st.chat_input("Ask a question about the regulations...")
if "example_clicked" in st.session_state:
    prompt = st.session_state.example_clicked
    del st.session_state.example_clicked

if prompt:
    # 1. Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Generate response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing query and retrieving documents..."):
            try:
                # --- PIPELINE LOGIC (Reused from generate.py) ---
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
                
                if routing_filter:
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=15,
                        include=["metadatas", "documents", "distances"],
                        where=routing_filter
                    )
                else:
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=15,
                        include=["metadatas", "documents", "distances"]
                    )
                
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
                        
                        # Re-run retrieval
                        query_embedding = model.encode(query).tolist()
                        
                        if routing_filter:
                            results = collection.query(
                                query_embeddings=[query_embedding],
                                n_results=15,
                                include=["metadatas", "documents", "distances"],
                                where=routing_filter
                            )
                        else:
                            results = collection.query(
                                query_embeddings=[query_embedding],
                                n_results=15,
                                include=["metadatas", "documents", "distances"]
                            )
                        
                        if results["ids"][0]:
                            metadatas = results["metadatas"][0]
                            documents = results["documents"][0]
                            context_prompt, retrieved_sources = build_context_prompt(query, documents, metadatas)

                # Final generation
                system_prompt = (
                    "Answer ONLY using the provided context. If the context does not contain the answer, "
                    "say so explicitly. Always cite which source document and page number your answer comes from."
                )
                
                answer = call_llm(context_prompt, system=system_prompt, model="gemini-3.5-flash")
                
                # Format detailed sources for the expander
                detailed_sources = []
                for i in range(len(documents)):
                    m = metadatas[i]
                    src = m.get('source_filename', 'Unknown')
                    pg = m.get('page_number', 'Unknown')
                    sec = m.get('section_title') or 'Unknown'
                    detailed_sources.append(f"**{src}** (Page {pg}) - *{sec}*")
                
                # De-duplicate detailed sources while preserving order
                unique_detailed_sources = list(dict.fromkeys(detailed_sources))

                # Display answer
                full_response = answer
                if reformulated:
                    full_response = f"*(Note: Query was reformulated to: '{query}' for better results)*\n\n" + full_response
                
                st.markdown(full_response)
                with st.expander("Sources"):
                    for s in unique_detailed_sources:
                        st.markdown(f"- {s}")
                        
                # Add to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response,
                    "sources": unique_detailed_sources
                })
                
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "Quota" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    st.error("API Rate Limit (429) hit. Please wait a minute and try again.")
                else:
                    st.error(f"An error occurred: {err_msg}")

st.markdown("---")
st.caption("Informational only, not legal advice. Verify against official documents.")
