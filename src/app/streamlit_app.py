"""
VaultIQ — Streamlit Chat UI
Enterprise knowledge search with role-based access control.

Run: streamlit run src/app/streamlit_app.py
"""

import os
import sys
import streamlit as st
from loguru import logger

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.retrieval.embeddings import EmbeddingEngine, QdrantIndex
from src.retrieval.bm25 import BM25Index
from src.retrieval import HybridRetriever
from src.retrieval.rag_chain import RAGChain


# --- Page Config ---
st.set_page_config(
    page_title="VaultIQ — Enterprise Knowledge Search",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .sub-header {
        color: #888;
        font-size: 1rem;
        margin-top: -10px;
        margin-bottom: 20px;
    }
    .source-card {
        background: #f8f9fa;
        border-left: 3px solid #667eea;
        padding: 10px 15px;
        margin: 5px 0;
        border-radius: 4px;
        font-size: 0.9rem;
    }
    .role-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 2px;
    }
    .role-engineering { background: #dbeafe; color: #1e40af; }
    .role-hr { background: #fce7f3; color: #9d174d; }
    .role-leadership { background: #fef3c7; color: #92400e; }
    .role-all { background: #d1fae5; color: #065f46; }
    .stats-box {
        background: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_retrieval_components():
    """Load all retrieval components (cached across reruns)."""
    qdrant_path = os.path.join(project_root, "qdrant_storage")
    bm25_path = os.path.join(project_root, "bm25_index.pkl")

    if not os.path.exists(qdrant_path):
        return None, None, None, "Index not found. Run: python -m src.retrieval.build_index"

    try:
        embedder = EmbeddingEngine()
        qdrant = QdrantIndex(path=qdrant_path)
        bm25 = BM25Index()
        bm25.load(bm25_path)
        return embedder, qdrant, bm25, None
    except Exception as e:
        return None, None, None, str(e)


def get_rag_chain():
    """Get RAG chain if API key is available."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        api_key = st.session_state.get("groq_api_key", "").strip()
    if api_key:
        try:
            return RAGChain(api_key=api_key)
        except Exception as e:
            st.warning(f"Failed to initialize Groq: {e}")
    return None


def format_role_badge(role: str) -> str:
    """Create an HTML badge for an ACL role."""
    role_class = {
        "engineering": "role-engineering",
        "hr": "role-hr",
        "leadership": "role-leadership",
        "all-employees": "role-all",
    }.get(role, "role-all")
    return f'<span class="role-badge {role_class}">{role}</span>'


def main():
    # --- Header ---
    st.markdown('<p class="main-header">🔐 VaultIQ</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Enterprise Knowledge Search — RAG over Messy Multi-Modal Data</p>',
        unsafe_allow_html=True,
    )

    # --- Sidebar ---
    with st.sidebar:
        st.header("⚙️ Settings")

        # Role selector
        role = st.selectbox(
            "Your Role",
            ["engineering", "hr", "leadership", "all-employees"],
            index=0,
            help="Simulates ACL-based access control. Different roles see different documents.",
        )
        user_roles = [role, "all-employees"] if role != "all-employees" else ["all-employees"]

        st.divider()

        # API Key input
        groq_key = st.text_input(
            "Groq API Key",
            type="password",
            value=os.getenv("GROQ_API_KEY", ""),
            help="Get a free key at console.groq.com",
        )
        if groq_key:
            st.session_state["groq_api_key"] = groq_key

        st.divider()

        # Retrieval settings
        st.subheader("Retrieval Settings")
        top_k = st.slider("Results to retrieve", 3, 10, 5)
        show_sources = st.checkbox("Show source chunks", value=True)

        st.divider()

        # System info
        st.subheader("📊 System Info")
        embedder, qdrant, bm25, error = load_retrieval_components()
        if error:
            st.error(f"❌ {error}")
        else:
            st.success(f"✅ Qdrant: {qdrant.count()} vectors")
            st.success(f"✅ BM25: {len(bm25.chunks)} documents")
            st.info(f"🔑 Groq: {'Connected' if get_rag_chain() else 'No API key'}")

    # --- Main Chat Area ---
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources") and show_sources:
                with st.expander("📚 Sources", expanded=False):
                    for src in message["sources"]:
                        st.markdown(
                            f'<div class="source-card">'
                            f'📄 <strong>{src["file"]}</strong> ({src["type"]}) — {src["title"]}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

    # --- Query Input ---
    if prompt := st.chat_input("Ask a question about BigCorp..."):
        # Check if components are loaded
        if error:
            st.error(f"Cannot query: {error}")
            return

        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Process query
        with st.chat_message("assistant"):
            with st.spinner("Searching knowledge base..."):
                # Retrieve
                retriever = HybridRetriever(
                    embedding_engine=embedder,
                    qdrant_index=qdrant,
                    bm25_index=bm25,
                )
                results = retriever.retrieve(
                    query=prompt,
                    user_roles=user_roles,
                    top_k=top_k,
                )

                if not results:
                    answer = "I couldn't find any relevant documents matching your query and access level. Try a different question or check your role."
                    sources = []
                else:
                    # Generate answer with LLM if available
                    rag = get_rag_chain()
                    if rag:
                        response = rag.generate(prompt, results)
                        answer = response["answer"]
                        sources = response["sources"]

                        # Show token usage
                        if response.get("usage"):
                            usage = response["usage"]
                            st.caption(
                                f"📊 {usage.get('total_tokens', 'N/A')} tokens · "
                                f"Model: {response['model']}"
                            )
                    else:
                        # No LLM — show retrieved chunks directly
                        answer = "**⚠️ No Groq API key set — showing retrieved documents only.**\n\n"
                        for i, r in enumerate(results, 1):
                            score = r.get("rrf_score", r.get("score", 0))
                            answer += f"**[{i}] {r['source_file']}** (score: {score:.4f})\n"
                            answer += f"> {r['content'][:300]}...\n\n"
                        sources = [
                            {"file": r["source_file"], "type": r["source_type"], "title": r["title"]}
                            for r in results
                        ]

                st.markdown(answer)

                # Show sources
                if sources and show_sources:
                    with st.expander("📚 Sources", expanded=False):
                        for src in sources:
                            roles_html = " ".join(
                                format_role_badge(r)
                                for r in results[0].get("acl_roles", [])
                            ) if results else ""
                            st.markdown(
                                f'<div class="source-card">'
                                f'📄 <strong>{src["file"]}</strong> ({src["type"]}) — {src["title"]}'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                # Save to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                })


if __name__ == "__main__":
    main()
