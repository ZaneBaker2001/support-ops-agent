from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from pathlib import Path

import httpx
import matplotlib.pyplot as plt

from evals.cases import EVAL_CASES


REPORTS_DIR = Path("./reports")
PLOTS_DIR = REPORTS_DIR / "plots"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
PLOTS_DIR.mkdir(parents=True, exist_ok=True)


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


def validate_response_shape(payload: dict) -> tuple[bool, list[str]]:
    required_fields = {
        "summary": str,
        "severity": str,
        "likely_root_causes": list,
        "recommended_actions": list,
        "evidence": list,
        "needs_human_followup": bool,
    }

    errors: list[str] = []
    for field, expected_type in required_fields.items():
        if field not in payload:
            errors.append(f"missing:{field}")
            continue
        if not isinstance(payload[field], expected_type):
            errors.append(
                f"type:{field}:expected={expected_type.__name__}:actual={type(payload[field]).__name__}"
            )

    if "severity" in payload and payload.get("severity") not in {"low", "medium", "high", "critical"}:
        errors.append("invalid:severity")

    if "evidence" in payload and isinstance(payload["evidence"], list):
        for idx, item in enumerate(payload["evidence"]):
            if not isinstance(item, dict):
                errors.append(f"evidence[{idx}]:not_object")
                continue
            if "source" not in item or "snippet" not in item:
                errors.append(f"evidence[{idx}]:missing_source_or_snippet")

    return len(errors) == 0, errors


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


def generate_plots(report: dict, per_run_results: list[dict]) -> list[str]:
    plot_paths: list[str] = []

    latencies = [r["latency_ms"] for r in per_run_results]
    run_labels = [str(r["run"]) for r in per_run_results]
    status_counts = report["summary"]["status_code_counts"]
    status_labels = list(status_counts.keys())
    status_values = [status_counts[k] for k in status_labels]
    response_sizes = [r["response_size_bytes"] for r in per_run_results]

    latency_runs_path = PLOTS_DIR / "api_benchmark_latency_by_run.png"
    save_bar_plot(
        labels=run_labels,
        values=latencies,
        title="API Benchmark: Latency by Run",
        ylabel="Latency (ms)",
        output_path=latency_runs_path,
        y_min=0,
    )
    plot_paths.append(str(latency_runs_path))

    latency_hist_path = PLOTS_DIR / "api_benchmark_latency_histogram.png"
    save_histogram(
        values=latencies,
        bins=min(15, max(5, len(latencies) // 2 or 1)),
        title="API Benchmark: Latency Distribution",
        xlabel="Latency (ms)",
        ylabel="Frequency",
        output_path=latency_hist_path,
    )
    plot_paths.append(str(latency_hist_path))

    status_path = PLOTS_DIR / "api_benchmark_status_codes.png"
    save_bar_plot(
        labels=status_labels,
        values=status_values,
        title="API Benchmark: Status Code Counts",
        ylabel="Count",
        output_path=status_path,
        y_min=0,
    )
    plot_paths.append(str(status_path))

    response_size_path = PLOTS_DIR / "api_benchmark_response_sizes.png"
    save_bar_plot(
        labels=run_labels,
        values=response_sizes,
        title="API Benchmark: Response Size by Run",
        ylabel="Bytes",
        output_path=response_size_path,
        y_min=0,
    )
    plot_paths.append(str(response_size_path))

    return plot_paths


def run_benchmark(base_url: str, runs: int, timeout_s: float) -> dict:
    latencies: list[float] = []
    status_codes: list[int] = []
    valid_json_count = 0
    valid_schema_count = 0
    response_sizes: list[int] = []
    failures: list[dict] = []
    per_run_results: list[dict] = []

    with httpx.Client(base_url=base_url, timeout=timeout_s) as client:
        health = client.get("/health")
        health.raise_for_status()

        for i in range(runs):
            case = EVAL_CASES[i % len(EVAL_CASES)]

            start = time.perf_counter()
            response = client.post("/v1/ask", json={"question": case.question})
            latency_ms = (time.perf_counter() - start) * 1000.0

            latencies.append(latency_ms)
            status_codes.append(response.status_code)
            response_sizes.append(len(response.content))

            run_result = {
                "run": i + 1,
                "case_name": case.name,
                "status_code": response.status_code,
                "latency_ms": round(latency_ms, 2),
                "response_size_bytes": len(response.content),
                "json_valid": False,
                "schema_valid": False,
            }

            try:
                payload = response.json()
                valid_json_count += 1
                run_result["json_valid"] = True
            except Exception as exc:
                failures.append(
                    {
                        "run": i + 1,
                        "case_name": case.name,
                        "status_code": response.status_code,
                        "error": f"invalid_json:{exc}",
                        "body": response.text[:500],
                    }
                )
                per_run_results.append(run_result)
                continue

            schema_ok, schema_errors = validate_response_shape(payload)
            if schema_ok:
                valid_schema_count += 1
                run_result["schema_valid"] = True
            else:
                failures.append(
                    {
                        "run": i + 1,
                        "case_name": case.name,
                        "status_code": response.status_code,
                        "error": "schema_validation_failed",
                        "schema_errors": schema_errors,
                        "body": payload,
                    }
                )

            per_run_results.append(run_result)

    success_rate = sum(1 for s in status_codes if 200 <= s < 300) / len(status_codes)
    json_valid_rate = valid_json_count / len(status_codes)
    schema_valid_rate = valid_schema_count / len(status_codes)

    report = {
        "summary": {
            "base_url": base_url,
            "runs": runs,
            "success_rate": round(success_rate, 3),
            "json_valid_rate": round(json_valid_rate, 3),
            "schema_valid_rate": round(schema_valid_rate, 3),
            "latency_ms": {
                "mean": round(statistics.mean(latencies), 2),
                "median": round(statistics.median(latencies), 2),
                "min": round(min(latencies), 2),
                "max": round(max(latencies), 2),
                "p95": round(percentile(latencies, 95), 2),
                "p99": round(percentile(latencies, 99), 2),
            },
            "response_size_bytes": {
                "mean": round(statistics.mean(response_sizes), 2),
                "median": round(statistics.median(response_sizes), 2),
            },
            "status_code_counts": {
                str(code): status_codes.count(code) for code in sorted(set(status_codes))
            },
        },
        "runs": per_run_results,
        "failures": failures,
    }

    report["plot_files"] = generate_plots(report, per_run_results)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark the Support Ops Agent API.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    report = run_benchmark(
        base_url=args.base_url,
        runs=args.runs,
        timeout_s=args.timeout,
    )

    out_path = REPORTS_DIR / "api_benchmark_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\nAPI Benchmark Summary")
    print("=" * 80)
    for k, v in report["summary"].items():
        print(f"{k}: {v}")
    print("\nPlots:")
    for plot_file in report["plot_files"]:
        print(f"- {plot_file}")
    print(f"\nDetailed report written to: {out_path}")