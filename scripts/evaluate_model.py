from __future__ import annotations

import json
import math
import statistics
import time
from pathlib import Path

import matplotlib.pyplot as plt

from app.schemas import FinalAnswer
from app.service import ask_agent
from evals.cases import EVAL_CASES, EvalCase


REPORTS_DIR = Path("./reports")
PLOTS_DIR = REPORTS_DIR / "plots"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def normalize_text_list(values: list[str]) -> str:
    return " ".join(v.lower().strip() for v in values)


def keyword_recall(keywords: list[str], text: str) -> float:
    if not keywords:
        return 1.0
    haystack = text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in haystack)
    return hits / len(keywords)


def score_case(case: EvalCase, answer: FinalAnswer, latency_ms: float) -> dict:
    root_text = normalize_text_list(answer.likely_root_causes)
    action_text = normalize_text_list(answer.recommended_actions)

    schema_valid = True
    severity_correct = float(answer.severity == case.expected_severity)
    root_recall = keyword_recall(case.expected_root_cause_keywords, root_text)
    action_recall = keyword_recall(case.expected_action_keywords, action_text)
    evidence_count_score = float(len(answer.evidence) >= case.min_evidence_items)

    if case.require_human_followup is None:
        followup_score = 1.0
    else:
        followup_score = float(answer.needs_human_followup == case.require_human_followup)

    overall = round(
        (
            0.20 * severity_correct
            + 0.30 * root_recall
            + 0.25 * action_recall
            + 0.15 * evidence_count_score
            + 0.10 * followup_score
        )
        * 100,
        2,
    )

    return {
        "case_name": case.name,
        "question": case.question,
        "latency_ms": round(latency_ms, 2),
        "schema_valid": schema_valid,
        "severity_expected": case.expected_severity,
        "severity_actual": answer.severity,
        "severity_correct": severity_correct,
        "root_keyword_recall": round(root_recall, 3),
        "action_keyword_recall": round(action_recall, 3),
        "evidence_items": len(answer.evidence),
        "min_evidence_items": case.min_evidence_items,
        "evidence_count_score": evidence_count_score,
        "needs_human_followup_expected": case.require_human_followup,
        "needs_human_followup_actual": answer.needs_human_followup,
        "followup_score": followup_score,
        "overall_score": overall,
        "response": answer.model_dump(),
    }


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return ordered[int(k)]
    d0 = ordered[f] * (c - k)
    d1 = ordered[c] * (k - f)
    return d0 + d1


def save_bar_plot(
    labels: list[str],
    values: list[float],
    title: str,
    ylabel: str,
    output_path: Path,
    y_min: float | None = None,
    y_max: float | None = None,
) -> None:
    plt.figure(figsize=(10, 6))
    plt.bar(labels, values)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=25, ha="right")
    if y_min is not None or y_max is not None:
        plt.ylim(y_min, y_max)
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def save_histogram(
    values: list[float],
    bins: int,
    title: str,
    xlabel: str,
    ylabel: str,
    output_path: Path,
) -> None:
    plt.figure(figsize=(10, 6))
    plt.hist(values, bins=bins)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def generate_plots(report: dict) -> list[str]:
    plot_paths: list[str] = []
    cases = report["cases"]

    case_names = [c["case_name"] for c in cases]
    overall_scores = [c["overall_score"] for c in cases]
    latencies = [c["latency_ms"] for c in cases]
    root_recalls = [c["root_keyword_recall"] for c in cases]
    action_recalls = [c["action_keyword_recall"] for c in cases]

    overall_path = PLOTS_DIR / "model_eval_overall_scores.png"
    save_bar_plot(
        labels=case_names,
        values=overall_scores,
        title="Model Evaluation: Overall Score by Case",
        ylabel="Overall Score",
        output_path=overall_path,
        y_min=0,
        y_max=100,
    )
    plot_paths.append(str(overall_path))

    latency_path = PLOTS_DIR / "model_eval_latency_by_case.png"
    save_bar_plot(
        labels=case_names,
        values=latencies,
        title="Model Evaluation: Latency by Case",
        ylabel="Latency (ms)",
        output_path=latency_path,
        y_min=0,
    )
    plot_paths.append(str(latency_path))

    root_path = PLOTS_DIR / "model_eval_root_keyword_recall.png"
    save_bar_plot(
        labels=case_names,
        values=root_recalls,
        title="Model Evaluation: Root-Cause Keyword Recall by Case",
        ylabel="Recall",
        output_path=root_path,
        y_min=0,
        y_max=1.0,
    )
    plot_paths.append(str(root_path))

    action_path = PLOTS_DIR / "model_eval_action_keyword_recall.png"
    save_bar_plot(
        labels=case_names,
        values=action_recalls,
        title="Model Evaluation: Action Keyword Recall by Case",
        ylabel="Recall",
        output_path=action_path,
        y_min=0,
        y_max=1.0,
    )
    plot_paths.append(str(action_path))

    latency_hist_path = PLOTS_DIR / "model_eval_latency_histogram.png"
    save_histogram(
        values=latencies,
        bins=min(10, max(3, len(latencies))),
        title="Model Evaluation: Latency Distribution",
        xlabel="Latency (ms)",
        ylabel="Frequency",
        output_path=latency_hist_path,
    )
    plot_paths.append(str(latency_hist_path))

    return plot_paths


def run_eval() -> dict:
    case_results: list[dict] = []
    latencies: list[float] = []

    for case in EVAL_CASES:
        start = time.perf_counter()
        answer = ask_agent(case.question)
        latency_ms = (time.perf_counter() - start) * 1000.0

        if not isinstance(answer, FinalAnswer):
            answer = FinalAnswer.model_validate(answer)

        result = score_case(case, answer, latency_ms)
        case_results.append(result)
        latencies.append(latency_ms)

    overall_scores = [r["overall_score"] for r in case_results]
    schema_valid_rate = sum(1 for r in case_results if r["schema_valid"]) / len(case_results)
    severity_accuracy = sum(r["severity_correct"] for r in case_results) / len(case_results)
    avg_root_recall = statistics.mean(r["root_keyword_recall"] for r in case_results)
    avg_action_recall = statistics.mean(r["action_keyword_recall"] for r in case_results)
    avg_overall = statistics.mean(overall_scores)

    report = {
        "summary": {
            "num_cases": len(case_results),
            "schema_valid_rate": round(schema_valid_rate, 3),
            "severity_accuracy": round(severity_accuracy, 3),
            "avg_root_keyword_recall": round(avg_root_recall, 3),
            "avg_action_keyword_recall": round(avg_action_recall, 3),
            "avg_overall_score": round(avg_overall, 2),
            "latency_ms": {
                "mean": round(statistics.mean(latencies), 2),
                "median": round(statistics.median(latencies), 2),
                "p95": round(percentile(latencies, 95), 2),
                "p99": round(percentile(latencies, 99), 2),
            },
        },
        "cases": case_results,
    }

    report["plot_files"] = generate_plots(report)
    return report


if __name__ == "__main__":
    report = run_eval()
    out_path = REPORTS_DIR / "model_eval_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\nModel Evaluation Summary")
    print("=" * 80)
    for k, v in report["summary"].items():
        print(f"{k}: {v}")
    print("\nPlots:")
    for plot_file in report["plot_files"]:
        print(f"- {plot_file}")
    print(f"\nDetailed report written to: {out_path}")