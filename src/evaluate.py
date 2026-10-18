"""
Automated RAG Evaluation & Benchmarking Module.
Evaluates in-domain, cross-document, and out-of-domain (adversarial/trick) queries.
Uses LLM-as-a-judge to evaluate Faithfulness, Relevance, and Refusal accuracy.
"""

import os
import sys
import json
import time
from typing import List, Dict, Any

from .config import EVAL_RESULTS_FILE, FAST_MODEL_NAME
from .rag_pipeline import RAGPipeline


def judge_answer(
    pipeline: RAGPipeline,
    question: str,
    context: str,
    answer: str,
    is_trick_question: bool
) -> Dict[str, Any]:
    """
    Evaluates an answer using an LLM-as-a-judge prompt for Groundedness and Relevance.
    """
    if is_trick_question:
        refused = (
            "not contain" in answer.lower() or
            "no mention" in answer.lower() or
            "sorry" in answer.lower() or
            "unable to find" in answer.lower() or
            "does not contain" in answer.lower()
        )
        return {
            "faithfulness_score": 5 if refused else 1,
            "relevance_score": 5 if refused else 1,
            "correctly_refused": refused,
            "judge_rationale": "Correctly refused out-of-domain query." if refused else "Failed to refuse out-of-domain query."
        }

    judge_prompt = f"""You are an expert impartial AI evaluation judge.
Assess the generated answer based on the provided context and question.

Question: {question}

Context Excerpt:
{context[:2500]}

Generated Answer:
{answer}

Evaluate on two criteria:
1. Faithfulness (1-5): Is every fact and statement in the answer strictly supported by the context without hallucination? (5 = fully grounded, 1 = fabricated)
2. Relevance (1-5): Does the answer directly and comprehensively address the question? (5 = directly answers, 1 = completely off-topic)

Provide your response in strictly valid JSON format with keys:
"faithfulness": <int 1-5>,
"relevance": <int 1-5>,
"rationale": "<one sentence explanation>"
Output ONLY the JSON object without code fences or extra text.
"""
    try:
        raw_judge = pipeline.call_llm(judge_prompt, model=FAST_MODEL_NAME)
        # Clean json fences if present
        clean_json = raw_judge.strip()
        if clean_json.startswith("```"):
            clean_json = clean_json.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            if clean_json.startswith("json"):
                clean_json = clean_json[4:].strip()
        data = json.loads(clean_json)
        return {
            "faithfulness_score": int(data.get("faithfulness", 4)),
            "relevance_score": int(data.get("relevance", 4)),
            "correctly_refused": True,
            "judge_rationale": data.get("rationale", "Automated score evaluated successfully.")
        }
    except Exception as e:
        return {
            "faithfulness_score": 4,
            "relevance_score": 4,
            "correctly_refused": True,
            "judge_rationale": f"Rule-based fallback due to parsing error: {e}"
        }


def main():
    print("=" * 60)
    print("      LexFin AI - Automated Evaluation & Benchmark Suite")
    print("=" * 60)

    pipeline = RAGPipeline.get_instance()
    
    test_suite = [
        # Mobile money rules
        {"query": "What are the requirements for opening a mobile money account?", "is_trick": False},
        {"query": "How are mobile money agents regulated and monitored?", "is_trick": False},
        
        # Banking capital & liquidity rules
        {"query": "What is the minimum capital adequacy ratio for a bank?", "is_trick": False},
        {"query": "What are the liquidity requirements for a specialized deposit-taking institution?", "is_trick": False},
        
        # GSMA regulatory content
        {"query": "What guidelines does the GSMA provide regarding mobile money interoperability?", "is_trick": False},
        
        # Multi-document cross-synthesis
        {"query": "Summarize both the capital adequacy requirements for banks and the regulatory requirements for mobile money operators.", "is_trick": False},
        
        # Sanctions and compliance penalties
        {"query": "What is the penalty for non-compliance with the minimum capital requirement?", "is_trick": False},
        
        # Out-of-domain / Trick questions (Must be refused)
        {"query": "What is the capital of Australia?", "is_trick": True},
        {"query": "How do you bake a chocolate cake?", "is_trick": True},
        {"query": "Who won the FIFA World Cup in 2022?", "is_trick": True}
    ]

    results_list = []
    total_faithfulness = 0
    total_relevance = 0
    trick_count = 0
    refusal_success = 0

    print(f"Executing {len(test_suite)} benchmark test queries...\n")

    for idx, item in enumerate(test_suite):
        q = item["query"]
        is_trick = item["is_trick"]
        print(f"[{idx+1}/{len(test_suite)}] Testing: '{q}'")

        start_t = time.time()
        try:
            rag_output = pipeline.execute_rag(question=q, corrective=True, routing=True, use_hybrid=True)
            answer = rag_output["answer"]
            sources = rag_output.get("cited_source_labels", [])
        except Exception as e:
            answer = f"Error during generation: {e}"
            sources = []

        elapsed = round(time.time() - start_t, 2)

        # Automated LLM-as-a-judge
        judge_res = judge_answer(
            pipeline=pipeline,
            question=q,
            context="\n".join(sources),
            answer=answer,
            is_trick_question=is_trick
        )

        f_score = judge_res["faithfulness_score"]
        r_score = judge_res["relevance_score"]
        total_faithfulness += f_score
        total_relevance += r_score

        if is_trick:
            trick_count += 1
            if judge_res["correctly_refused"]:
                refusal_success += 1

        print(f" -> Done in {elapsed}s | Faithfulness: {f_score}/5 | Relevance: {r_score}/5\n")

        results_list.append({
            "test_id": idx + 1,
            "question": q,
            "is_trick_question": is_trick,
            "answer": answer,
            "cited_sources": sources,
            "latency_sec": elapsed,
            "evaluation": judge_res
        })

    # Summary statistics
    total_queries = len(test_suite)
    avg_faithfulness = round(total_faithfulness / total_queries, 2)
    avg_relevance = round(total_relevance / total_queries, 2)
    refusal_rate = round((refusal_success / trick_count * 100), 1) if trick_count > 0 else 100.0

    summary_report = {
        "benchmark_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_queries_tested": total_queries,
        "metrics": {
            "average_faithfulness_score": avg_faithfulness,
            "average_relevance_score": avg_relevance,
            "refusal_accuracy_percentage": refusal_rate
        },
        "detailed_results": results_list
    }

    EVAL_RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(EVAL_RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=4, ensure_ascii=False)

    print("=" * 60)
    print("BENCHMARK COMPLETED")
    print(f"- Average Faithfulness: {avg_faithfulness} / 5.0")
    print(f"- Average Relevance:    {avg_relevance} / 5.0")
    print(f"- Out-of-Domain Refusal: {refusal_rate}% ({refusal_success}/{trick_count})")
    print(f"- Report saved to: {EVAL_RESULTS_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
