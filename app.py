import streamlit as st
import os
import sys
import json
import uuid
import time
from pathlib import Path

# Add src to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from src.config import CHAT_HISTORY_FILE
from src.rag_pipeline import RAGPipeline

# --- Page Configuration ---
st.set_page_config(
    page_title="LexFin AI - Regulatory Compliance Assistant",
    page_icon="🏦",
    layout="wide"
)

# --- Clean Custom Styling ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    body, p, div, span, button {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    [data-testid="stSidebar"] {
        background-color: #12141C;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    
    .sidebar-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #F8FAFC;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
    }

    .hero-title {
        text-align: center;
        font-size: 2.2rem;
        font-weight: 700;
        margin-top: 4vh;
        margin-bottom: 0.5rem;
        color: #F8FAFC;
    }
    
    .hero-subtitle {
        text-align: center;
        color: #94A3B8;
        font-size: 1rem;
        margin-bottom: 2.5rem;
    }

    .stButton > button {
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        background-color: transparent;
        transition: all 0.2s ease;
        text-align: left;
    }
    .stButton > button:hover {
        border-color: #38BDF8;
        background-color: rgba(56, 189, 248, 0.08);
    }

    .badge-routed {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        background: rgba(56, 189, 248, 0.15);
        color: #38BDF8;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


# --- History Management ---
def load_history():
    if CHAT_HISTORY_FILE.exists():
        try:
            with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_history(history):
    CHAT_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4)


if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_history()

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = str(uuid.uuid4())
    st.session_state.messages = []

# Synchronize messages for current session
if st.session_state.current_session_id in st.session_state.chat_history:
    st.session_state.messages = st.session_state.chat_history[st.session_state.current_session_id]
else:
    st.session_state.messages = []


# --- Singleton Pipeline Caching ---
@st.cache_resource(show_spinner="Initializing LexFin AI models & index...")
def get_pipeline():
    pipeline = RAGPipeline.get_instance()
    # Warm up collection & embedder
    _ = pipeline.chroma_collection
    _ = pipeline.embedder
    return pipeline


try:
    pipeline = get_pipeline()
    available_docs = pipeline.get_available_documents()
except Exception as e:
    st.error(f"Failed to initialize RAG Pipeline: {e}")
    st.stop()


# --- Sidebar Navigation & Settings ---
with st.sidebar:
    st.markdown('<div class="sidebar-title">🏦 LexFin AI</div>', unsafe_allow_html=True)
    st.caption("Ghana Regulatory Intelligence Assistant")

    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.current_session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown("**Conversation History**")

    history_keys = list(st.session_state.chat_history.keys())
    for s_id in reversed(history_keys):
        s_data = st.session_state.chat_history[s_id]
        if not s_data:
            continue

        title = "New Chat"
        for msg in s_data:
            if msg["role"] == "user":
                title = msg["content"][:28] + ("..." if len(msg["content"]) > 28 else "")
                break

        if st.button(f"💬 {title}", key=f"session_{s_id}", use_container_width=True):
            st.session_state.current_session_id = s_id
            st.rerun()

    st.markdown("---")
    st.markdown("**RAG Engine Controls**")
    use_hybrid = st.toggle("Hybrid Search (Dense + BM25)", value=True, help="Combines vector similarity with exact keyword matching")
    use_routing = st.toggle("Dynamic Query Routing", value=True, help="Filters search to specific legal acts when applicable")
    use_corrective = st.toggle("Corrective RAG (CRAG)", value=True, help="Enables self-reflection check and query reformulation")
    top_k_chunks = st.slider("Context Chunks (Top-K)", min_value=3, max_value=10, value=5)

    with st.expander(f"📚 {len(available_docs)} Regulatory Directives Indexed"):
        for doc in available_docs:
            st.caption(f"• {doc}")


# --- Main Chat Area ---
if not st.session_state.messages:
    st.markdown('<div class="hero-title">Ghana Regulatory Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Ask questions about Ghana\'s banking laws, capital adequacy, cybersecurity, and mobile money frameworks.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    example_queries = [
        "What is the minimum capital adequacy ratio for a bank?",
        "What are the requirements for opening a mobile money account?",
        "What is the penalty for non-compliance with minimum capital requirements?",
        "What guidelines does the GSMA provide regarding mobile money interoperability?"
    ]

    for i, ex in enumerate(example_queries):
        target_col = col1 if i % 2 == 0 else col2
        with target_col:
            if st.button(ex, key=f"ex_btn_{i}", use_container_width=True):
                st.session_state.example_selected = ex
                st.rerun()
else:
    # Render chat conversation
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                st.markdown("**LexFin AI**")
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander(f"📖 View Citations & Sources ({len(msg['sources'])})"):
                    for src in msg["sources"]:
                        st.markdown(f"- **{src.get('source_filename', 'Document')}** (Page {src.get('page_number', '?')}) — *{src.get('section_title', 'General')}*")


# Handle User Prompt Input
user_input = st.chat_input("Ask a question about banking regulations or directives...")
if "example_selected" in st.session_state:
    user_input = st.session_state.example_selected
    del st.session_state.example_selected

if user_input:
    # 1. Save and display user question
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.chat_history[st.session_state.current_session_id] = st.session_state.messages
    save_history(st.session_state.chat_history)

    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. Execute RAG Pipeline
    with st.chat_message("assistant"):
        st.markdown("**LexFin AI**")
        with st.spinner("Analyzing regulations & statutory clauses..."):
            try:
                # Prepare conversation history for contextual rewriting
                history_turns = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages[:-1]
                ]

                rag_result = pipeline.execute_rag(
                    question=user_input,
                    history=history_turns,
                    corrective=use_corrective,
                    routing=use_routing,
                    use_hybrid=use_hybrid,
                    top_k=top_k_chunks
                )

                answer_text = rag_result["answer"]
                sources = rag_result.get("sources", [])
                routed_to = rag_result.get("routed_to")
                reformulated = rag_result.get("reformulated_query")
                latency = rag_result.get("latency_sec", 0.0)

                # Show status badges if agentic steps triggered
                badges = []
                if routed_to:
                    badges.append(f"🎯 Routed to: {', '.join(routed_to)}")
                if reformulated:
                    badges.append(f"🔄 Search reformulated to: '{reformulated}'")
                if badges:
                    st.caption(" | ".join(badges))

                st.markdown(answer_text)

                if sources:
                    with st.expander(f"📖 View Citations & Sources ({len(sources)}) — Generated in {latency}s"):
                        for s in sources:
                            fn = s.get('source_filename', 'Document')
                            pg = s.get('page_number', '?')
                            sec = s.get('section_title', 'General')
                            txt = s.get('text', '')
                            st.markdown(f"**{fn}** (Page {pg}) — *{sec}*")
                            st.caption(f'"{txt[:280]}..."' if len(txt) > 280 else f'"{txt}"')
                            st.divider()

                # Save assistant response to session
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer_text,
                    "sources": sources,
                    "latency": latency
                })
                st.session_state.chat_history[st.session_state.current_session_id] = st.session_state.messages
                save_history(st.session_state.chat_history)

            except Exception as ex:
                err_text = str(ex)
                if "429" in err_text or "quota" in err_text.lower():
                    st.error("Rate limit hit from upstream model provider. Please wait 15 seconds and try again.")
                else:
                    st.error(f"Error generating answer: {err_text}")
