"""
RAG Generation Module & Interactive CLI Tester.
Integrates unified RAGPipeline for hybrid retrieval, corrective reflection, and document routing.
"""

import sys
import argparse
from typing import List, Dict, Any, Tuple

from .config import SYSTEM_PROMPT, GENERATION_MODEL_NAME
from .rag_pipeline import RAGPipeline


def call_llm(prompt: str, system: str = None, model: str = GENERATION_MODEL_NAME) -> str:
    """Legacy helper function delegating to RAGPipeline for backwards compatibility."""
    pipeline = RAGPipeline.get_instance()
    return pipeline.call_llm(prompt=prompt, system=system, model=model)


def build_context_prompt(question: str, documents: List[str], metadatas: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
    """Legacy helper function delegating to RAGPipeline for backwards compatibility."""
    pipeline = RAGPipeline.get_instance()
    return pipeline.format_context_prompt(question, documents, metadatas)


def main():
    parser = argparse.ArgumentParser(description="LexFin AI - RAG Generation Tester")
    parser.add_argument("--corrective", action="store_true", help="Enable corrective retrieval (self-reflection)")
    parser.add_argument("--routing", action="store_true", help="Enable dynamic query routing to specific documents")
    parser.add_argument("--no-hybrid", action="store_true", help="Disable BM25 hybrid search and use pure vector search")
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve (default: 5)")
    args = parser.parse_args()

    pipeline = RAGPipeline.get_instance()
    # Trigger collection and model warmup
    _ = pipeline.chroma_collection
    _ = pipeline.embedder

    print("\n" + "=" * 60)
    print("      LexFin AI - Ghana Regulatory Intelligence Tester")
    print("=" * 60)
    print(f"Embedding Model: {pipeline.embedder.__class__.__name__}")
    print(f"Hybrid Search:   {'Disabled' if args.no_hybrid else 'Enabled (Dense + BM25)'}")
    print(f"Corrective RAG:  {'Enabled' if args.corrective else 'Disabled'}")
    print(f"Query Routing:   {'Enabled' if args.routing else 'Disabled'}")
    print(f"Top K Chunks:    {args.top_k}")
    print("\nType your legal/banking query below. Type 'exit' to quit.\n")

    while True:
        try:
            query = input("Enter query: ").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit"):
                print("Exiting...")
                break

            print("\nProcessing request through RAG Pipeline...")
            result = pipeline.execute_rag(
                question=query,
                corrective=args.corrective,
                routing=args.routing,
                use_hybrid=not args.no_hybrid,
                top_k=args.top_k
            )

            print("\n" + "=" * 60)
            print("ANSWER:")
            print("=" * 60)
            if result.get("reformulated_query"):
                print(f"[Note: Search reformulated to: '{result['reformulated_query']}']\n")
            if result.get("routed_to"):
                print(f"[Note: Routed to document(s): {', '.join(result['routed_to'])}]\n")
            print(result["answer"])
            print("\n" + "-" * 60)
            print(f"SOURCES RETRIEVED (Latency: {result['latency_sec']}s):")
            for src in result.get("cited_source_labels", []):
                print(f"- {src}")
            print("=" * 60 + "\n")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\n[Error] {e}\n")


if __name__ == "__main__":
    main()
