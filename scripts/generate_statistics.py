#!/usr/bin/env python3
"""
generate_statistics.py - Ikshvaku Aptitude Arena Statistics Generator
======================================================================
Scans all question files under questions/ and:
  1. Computes total questions, per-topic counts, per-difficulty counts,
     per-type counts, and per-subtopic counts.
  2. Calculates time benchmarks (average estimated time overall & per difficulty).
  3. Updates metadata/question-counts.json with comprehensive metrics.
  4. Renders an ASCII statistical dashboard in the terminal.
"""

import sys
import os
import json
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any

# Ensure UTF-8 output encoding across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def generate_stats(repo_root: Path) -> Dict[str, Any]:
    questions_dir = repo_root / "questions"
    metadata_dir = repo_root / "metadata"

    total_questions = 0
    by_topic = defaultdict(int)
    by_difficulty = defaultdict(int)
    by_type = defaultdict(int)
    by_subtopic = defaultdict(lambda: defaultdict(int))
    topic_difficulty_matrix = defaultdict(lambda: defaultdict(int))
    total_time = 0
    time_by_difficulty = defaultdict(lambda: {"total": 0, "count": 0})

    for json_file in questions_dir.rglob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = data if isinstance(data, list) else [data]
            for q in items:
                if not isinstance(q, dict) or "id" not in q:
                    continue

                total_questions += 1
                topic = q.get("topic", "unknown")
                subtopic = q.get("subtopic", "unknown")
                diff = q.get("difficulty", "unknown")
                q_type = q.get("question_type", "unknown")
                t_sec = q.get("estimated_time_seconds", 0)

                by_topic[topic] += 1
                by_difficulty[diff] += 1
                by_type[q_type] += 1
                by_subtopic[topic][subtopic] += 1
                topic_difficulty_matrix[topic][diff] += 1

                total_time += t_sec
                time_by_difficulty[diff]["total"] += t_sec
                time_by_difficulty[diff]["count"] += 1

        except Exception as exc:
            print(f"[WARNING] Skipping unreadable file {json_file}: {exc}", file=sys.stderr)

    avg_time_overall = round(total_time / total_questions, 1) if total_questions > 0 else 0
    avg_time_by_diff = {}
    for d, info in time_by_difficulty.items():
        avg_time_by_diff[d] = round(info["total"] / info["count"], 1) if info["count"] > 0 else 0

    stats = {
        "repository": "ikshvaku-quantitative-aptitude",
        "system": "Ikshvaku Aptitude Arena Question Bank",
        "total_questions": total_questions,
        "difficulty_distribution": dict(by_difficulty),
        "question_type_distribution": dict(by_type),
        "topic_distribution": dict(by_topic),
        "topic_difficulty_matrix": {k: dict(v) for k, v in topic_difficulty_matrix.items()},
        "subtopic_distribution": {k: dict(v) for k, v in by_subtopic.items()},
        "time_metrics": {
            "total_estimated_seconds": total_time,
            "average_estimated_seconds_overall": avg_time_overall,
            "average_estimated_seconds_by_difficulty": avg_time_by_diff
        }
    }

    # Write to metadata/question-counts.json
    counts_file = metadata_dir / "question-counts.json"
    with open(counts_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    return stats


def print_dashboard(stats: Dict[str, Any]):
    print("=" * 86)
    print(" IKSHVAKU APTITUDE ARENA - QUESTION BANK REPOSITORY STATISTICS")
    print("=" * 86)
    print(f" Total Questions Indexed     : {stats['total_questions']}")
    print(f" Average Estimated Solve Time: {stats['time_metrics']['average_estimated_seconds_overall']}s")
    print("-" * 86)

    print("\n[DIFFICULTY BREAKDOWN]")
    diff_order = ["easy", "medium", "hard", "very_hard"]
    for diff in diff_order:
        cnt = stats["difficulty_distribution"].get(diff, 0)
        pct = (cnt / stats["total_questions"] * 100) if stats["total_questions"] else 0
        avg_t = stats["time_metrics"]["average_estimated_seconds_by_difficulty"].get(diff, 0)
        print(f"  * {diff.capitalize():<10} : {cnt:>4} questions ({pct:>5.1f}%) | Avg Time: {avg_t}s")

    print("\n[QUESTION TYPE BREAKDOWN]")
    for q_type, cnt in sorted(stats["question_type_distribution"].items()):
        pct = (cnt / stats["total_questions"] * 100) if stats["total_questions"] else 0
        print(f"  * {q_type:<18} : {cnt:>4} questions ({pct:>5.1f}%)")

    print("\n[TOPIC x DIFFICULTY MATRIX]")
    header_fmt = "{:<28} {:>8} {:>8} {:>8} {:>10} {:>8}"
    row_fmt = "{:<28} {:>8} {:>8} {:>8} {:>10} {:>8}"
    print(header_fmt.format("Topic", "Easy", "Medium", "Hard", "Very Hard", "Total"))
    print("-" * 86)

    matrix = stats["topic_difficulty_matrix"]
    for topic in sorted(matrix.keys()):
        easy_cnt = matrix[topic].get("easy", 0)
        med_cnt = matrix[topic].get("medium", 0)
        hard_cnt = matrix[topic].get("hard", 0)
        vhard_cnt = matrix[topic].get("very_hard", 0)
        total_topic = easy_cnt + med_cnt + hard_cnt + vhard_cnt
        print(row_fmt.format(topic[:27], easy_cnt, med_cnt, hard_cnt, vhard_cnt, total_topic))

    print("=" * 86)
    print(" Metadata updated: metadata/question-counts.json")
    print("=" * 86)


def main():
    repo_root = Path(__file__).resolve().parent.parent
    stats = generate_stats(repo_root)
    print_dashboard(stats)


if __name__ == "__main__":
    main()
