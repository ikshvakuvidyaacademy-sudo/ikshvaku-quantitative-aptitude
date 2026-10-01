#!/usr/bin/env python3
"""
detect_duplicates.py - Ikshvaku Aptitude Arena Duplicate Detection Engine
=========================================================================
Detects duplicate and near-duplicate questions across the repository:
  1. Exact duplicate questions (byte-for-byte or exact string)
  2. Case-insensitive and whitespace-normalized duplicates
  3. Highly similar questions (using SequenceMatcher and token Jaccard similarity >= threshold)
  4. Structural duplicates with identical phrasing but altered numbers/constants

Does NOT delete any questions automatically.
Generates an audit report detailing:
  - Question ID 1
  - Question ID 2
  - Similarity percentage
  - Reason / Classification
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from difflib import SequenceMatcher
from typing import List, Dict, Any, Tuple

# Ensure UTF-8 output encoding across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def normalize_text(text: str) -> str:
    """Normalize casing, whitespace, and punctuation for robust comparison."""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def extract_structural_skeleton(text: str) -> str:
    """
    Mask all numbers, decimals, fractions, and percentages to detect
    questions with identical grammatical/conceptual structure but different numerical values.
    """
    # Normalize basic casing & spaces
    s = text.lower().strip()
    # Mask currency symbols and common numbers
    s = re.sub(r"[\$₹£€]", " ", s)
    s = re.sub(r"\b\d+(\.\d+)?%?", "<NUM>", s)
    # Normalize punctuation and extra spaces
    s = re.sub(r"[^\w\s<>]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def compute_token_jaccard(s1: str, s2: str) -> float:
    """Compute token Jaccard similarity between two texts."""
    tokens1 = set(re.findall(r"\b\w+\b", s1.lower()))
    tokens2 = set(re.findall(r"\b\w+\b", s2.lower()))
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return len(intersection) / len(union)


def compute_similarity(s1: str, s2: str) -> float:
    """Combined SequenceMatcher and Jaccard similarity metric."""
    seq_ratio = SequenceMatcher(None, s1, s2).ratio()
    jaccard = compute_token_jaccard(s1, s2)
    return max(seq_ratio, jaccard)


class DuplicateDetector:
    def __init__(self, repo_root: Path, threshold: float = 0.85):
        self.repo_root = repo_root
        self.threshold = threshold
        self.questions: List[Dict[str, Any]] = []

    def load_all_questions(self, questions_dir: Path):
        for json_file in questions_dir.rglob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and "id" in item and "question" in item:
                        item["_source_file"] = str(json_file.relative_to(self.repo_root))
                        self.questions.append(item)
            except Exception as exc:
                print(f"[WARNING] Skipping unreadable file {json_file}: {exc}", file=sys.stderr)

    def scan_duplicates(self) -> List[Dict[str, Any]]:
        findings = []
        n = len(self.questions)

        for i in range(n):
            q1 = self.questions[i]
            id1 = q1["id"]
            text1 = q1["question"]
            norm1 = normalize_text(text1)
            skel1 = extract_structural_skeleton(text1)

            for j in range(i + 1, n):
                q2 = self.questions[j]
                id2 = q2["id"]
                text2 = q2["question"]
                norm2 = normalize_text(text2)
                skel2 = extract_structural_skeleton(text2)

                # Check 1: Exact match
                if text1 == text2:
                    findings.append({
                        "question_id_1": id1,
                        "question_id_2": id2,
                        "topic_1": q1.get("topic"),
                        "topic_2": q2.get("topic"),
                        "similarity": 1.0,
                        "reason": "Exact duplicate question text",
                        "file_1": q1["_source_file"],
                        "file_2": q2["_source_file"]
                    })
                    continue

                # Check 2: Case-insensitive / whitespace-normalized
                if norm1 == norm2:
                    findings.append({
                        "question_id_1": id1,
                        "question_id_2": id2,
                        "topic_1": q1.get("topic"),
                        "topic_2": q2.get("topic"),
                        "similarity": 0.99,
                        "reason": "Case-insensitive / whitespace-identical duplicate",
                        "file_1": q1["_source_file"],
                        "file_2": q2["_source_file"]
                    })
                    continue

                # Check 3: Structural duplicate with changed numbers
                if len(skel1) > 25 and skel1 == skel2:
                    findings.append({
                        "question_id_1": id1,
                        "question_id_2": id2,
                        "topic_1": q1.get("topic"),
                        "topic_2": q2.get("topic"),
                        "similarity": 0.95,
                        "reason": "Structural template clone (identical wording with altered numerical values)",
                        "file_1": q1["_source_file"],
                        "file_2": q2["_source_file"]
                    })
                    continue

                # Check 4: High similarity ratio
                sim = compute_similarity(norm1, norm2)
                if sim >= self.threshold:
                    findings.append({
                        "question_id_1": id1,
                        "question_id_2": id2,
                        "topic_1": q1.get("topic"),
                        "topic_2": q2.get("topic"),
                        "similarity": round(sim, 3),
                        "reason": f"High textual similarity ({sim * 100:.1f}%)",
                        "file_1": q1["_source_file"],
                        "file_2": q2["_source_file"]
                    })

        return findings


def print_report(findings: List[Dict[str, Any]], total_questions: int, threshold: float):
    print("=" * 88)
    print(" IKSHVAKU APTITUDE ARENA - DUPLICATE DETECTION REPORT")
    print("=" * 88)
    print(f" Total Questions Evaluated : {total_questions}")
    print(f" Similarity Threshold      : {threshold * 100:.0f}%")
    print(f" Potential Duplicates Found: {len(findings)}")
    print("-" * 88)

    if not findings:
        print(" [OK] No duplicate or suspiciously similar questions detected across the bank.")
        print("=" * 88)
        return

    # Print table header
    header_fmt = "{:<22} {:<22} {:<12} {:<30}"
    row_fmt = "{:<22} {:<22} {:<12} {:<30}"
    print(header_fmt.format("Question ID 1", "Question ID 2", "Similarity", "Reason"))
    print("-" * 88)

    for f in findings:
        sim_str = f"{f['similarity'] * 100:.1f}%"
        print(row_fmt.format(f["question_id_1"], f["question_id_2"], sim_str, f["reason"][:28]))
        print(f"   * Q1: {f['file_1']}")
        print(f"   * Q2: {f['file_2']}")
        print()

    print("=" * 88)


def main():
    parser = argparse.ArgumentParser(description="Scan question bank for duplicates and structural clones.")
    parser.add_argument("--threshold", type=float, default=0.85, help="Similarity threshold between 0.50 and 1.00 (default: 0.85)")
    parser.add_argument("--output-json", type=str, default=None, help="Optional output JSON path for the report.")
    parser.add_argument("--output-markdown", type=str, default=None, help="Optional output Markdown path for the report.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    detector = DuplicateDetector(repo_root, threshold=args.threshold)
    detector.load_all_questions(repo_root / "questions")

    findings = detector.scan_duplicates()
    print_report(findings, len(detector.questions), args.threshold)

    if args.output_json:
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({
                "total_questions": len(detector.questions),
                "threshold": args.threshold,
                "duplicates_count": len(findings),
                "duplicates": findings
            }, f, indent=2)
        print(f"Report saved to JSON: {out_path}")

    if args.output_markdown:
        out_path = Path(args.output_markdown)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("# Ikshvaku Aptitude Arena - Duplicate Detection Report\n\n")
            f.write(f"- **Total Questions Evaluated**: {len(detector.questions)}\n")
            f.write(f"- **Similarity Threshold**: {args.threshold * 100:.0f}%\n")
            f.write(f"- **Total Flagged Pairs**: {len(findings)}\n\n")
            if findings:
                f.write("| Question ID 1 | Question ID 2 | Similarity | Reason |\n")
                f.write("|---------------|---------------|------------|--------|\n")
                for item in findings:
                    f.write(f"| `{item['question_id_1']}` | `{item['question_id_2']}` | {item['similarity'] * 100:.1f}% | {item['reason']} |\n")
            else:
                f.write("No duplicate questions found. Repository maintains 100% question uniqueness.\n")
        print(f"Report saved to Markdown: {out_path}")


if __name__ == "__main__":
    main()
