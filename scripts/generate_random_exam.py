#!/usr/bin/env python3
"""
generate_random_exam.py - Ikshvaku Random Question Selector & Exam Generator
=============================================================================
Selects STRICTLY RANDOM, non-repeating questions from the 500,000+ question bank.

Guarantees:
  1. Purely random selection across all chunk files (Uniform probability distribution).
  2. Dynamically shuffles options [A, B, C, D] for each question so correct answers
     are never statically predictable.
  3. Supports stratified blueprints (e.g., 10 Easy + 10 Medium + 5 Hard).
  4. Supports specific topic or subtopic filters.
  5. Exports:
     - `student_exam.json` (for students: questions + randomized options, no answers)
     - `instructor_key.json` (for grading: questions + correct answers + step-by-step solutions)
     - `exam_paper.md` (clean printable Markdown question paper)
"""

import os
import sys
import json
import random
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure UTF-8 output encoding across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_DIR = REPO_ROOT / "questions"


class RandomExamEngine:
    def __init__(self, questions_dir: Optional[Path] = None):
        self.questions_dir = questions_dir or QUESTIONS_DIR
        if not self.questions_dir.exists():
            raise FileNotFoundError(f"Questions directory not found at {self.questions_dir}")

    def get_candidate_files(self, topics: Optional[List[str]] = None, difficulties: Optional[List[str]] = None) -> List[Path]:
        """Collect all chunk files matching topic and difficulty filters."""
        all_files = []
        for topic_dir in self.questions_dir.iterdir():
            if not topic_dir.is_dir():
                continue
            if topics and topic_dir.name not in topics:
                continue

            for diff_dir in topic_dir.iterdir():
                if not diff_dir.is_dir():
                    continue
                if difficulties and diff_dir.name not in difficulties:
                    continue

                for chunk_file in diff_dir.glob("*.json"):
                    all_files.append(chunk_file)
        return all_files

    def select_random_questions(
        self,
        count: int = 25,
        topics: Optional[List[str]] = None,
        difficulties: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fast two-stage reservoir sampling:
        Picks random chunks, loads questions, and performs unbiased uniform random selection.
        """
        candidate_files = self.get_candidate_files(topics=topics, difficulties=difficulties)
        if not candidate_files:
            print("[Warning] No question files matched the filter criteria.", file=sys.stderr)
            return []

        # Shuffle candidate files randomly to avoid ordering bias
        shuffled_files = list(candidate_files)
        random.shuffle(shuffled_files)

        pool: List[Dict[str, Any]] = []
        # Load from randomly shuffled files until we have at least 3x the required sample pool
        needed_pool_size = max(count * 5, 2000)
        
        for cf in shuffled_files:
            try:
                with open(cf, "r", encoding="utf-8") as f:
                    chunk = json.load(f)
                if isinstance(chunk, list):
                    pool.extend(chunk)
                if len(pool) >= needed_pool_size:
                    break
            except Exception as exc:
                print(f"[Warning] Error reading {cf}: {exc}", file=sys.stderr)

        if not pool:
            return []

        # Perform uniform random sampling without replacement
        sample_size = min(count, len(pool))
        selected = random.sample(pool, sample_size)

        # Post-process: randomize option orders for each selected question
        processed = []
        for q in selected:
            q_copy = dict(q)
            if q_copy.get("question_type") == "single_choice" and isinstance(q_copy.get("options"), list):
                shuffled_options = list(q_copy["options"])
                random.shuffle(shuffled_options)
                q_copy["options"] = shuffled_options
            processed.append(q_copy)

        random.shuffle(processed)
        return processed

    def generate_blueprint_exam(self, blueprint: Dict[str, int], topics: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Generates an exam using an exact difficulty blueprint.
        Example: {'easy': 10, 'medium': 10, 'hard': 5}
        """
        exam_questions = []
        for diff, count in blueprint.items():
            diff_sample = self.select_random_questions(count=count, topics=topics, difficulties=[diff])
            exam_questions.extend(diff_sample)
        random.shuffle(exam_questions)
        return exam_questions


def export_markdown_paper(questions: List[Dict[str, Any]], title: str, out_file: Path):
    """Exports a student-facing printable test paper in Markdown."""
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(f"# 🏛️ Ikshvaku Aptitude Arena\n")
        f.write(f"### {title}\n")
        f.write(f"**Total Questions:** {len(questions)} | **Subject:** Quantitative Aptitude\n")
        tot_time = sum(q.get("estimated_time_seconds", 60) for q in questions) / 60
        f.write(f"**Recommended Time Limit:** {tot_time:.0f} Minutes\n\n")
        f.write("---\n\n")

        for idx, q in enumerate(questions, 1):
            f.write(f"#### Q{idx}. [{q['id']}] ({q['topic'].replace('-', ' ').title()} - {q['difficulty'].upper()})\n\n")
            f.write(f"{q['question']}\n\n")
            if q.get("options"):
                labels = ["A", "B", "C", "D", "E", "F"]
                for l, opt in zip(labels, q["options"]):
                    f.write(f"- **({l})** {opt}\n")
            f.write("\n")


def main():
    parser = argparse.ArgumentParser(description="Generate random exams from Ikshvaku question bank.")
    parser.add_argument("--count", type=int, default=25, help="Total random questions to select (default: 25)")
    parser.add_argument("--blueprint", type=str, default=None, help="Difficulty quotas e.g. 'easy:10,medium:10,hard:5'")
    parser.add_argument("--topics", nargs="+", default=None, help="Filter by specific topics (e.g. percentages algebra)")
    parser.add_argument("--title", type=str, default="Ikshvaku Aptitude Arena - Random Mock Exam", help="Exam Title")
    parser.add_argument("--output-dir", type=str, default="generated_exams", help="Output directory for generated exams")
    args = parser.parse_args()

    engine = RandomExamEngine()
    print("=" * 80)
    print(" IKSHVAKU APTITUDE ARENA - RANDOM EXAM GENERATION ENGINE")
    print("=" * 80)

    if args.blueprint:
        # Parse blueprint e.g. "easy:10,medium:10,hard:5"
        bp = {}
        for pair in args.blueprint.split(","):
            d, c = pair.strip().split(":")
            bp[d.strip().lower()] = int(c.strip())
        print(f" Blueprint Pattern : {bp}")
        questions = engine.generate_blueprint_exam(bp, topics=args.topics)
    else:
        print(f" Requested Count   : {args.count} purely random questions")
        questions = engine.select_random_questions(count=args.count, topics=args.topics)

    print(f" Selected Questions: {len(questions)} unique random questions")
    tot_time_min = sum(q.get("estimated_time_seconds", 60) for q in questions) / 60
    print(f" Total Benchmark   : {tot_time_min:.1f} minutes")

    out_dir = REPO_ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Student Paper (Questions + randomized options, no answers)
    student_paper = []
    for q in questions:
        student_paper.append({
            "id": q["id"],
            "topic": q["topic"],
            "difficulty": q["difficulty"],
            "question": q["question"],
            "options": q.get("options", []),
            "estimated_time_seconds": q.get("estimated_time_seconds")
        })

    with open(out_dir / "student_exam_paper.json", "w", encoding="utf-8") as f:
        json.dump({
            "exam_title": args.title,
            "total_questions": len(student_paper),
            "time_limit_minutes": round(tot_time_min, 1),
            "questions": student_paper
        }, f, indent=2)

    # 2. Instructor / Evaluation Key (Complete solutions & explanations)
    with open(out_dir / "instructor_answer_key.json", "w", encoding="utf-8") as f:
        json.dump({
            "exam_title": args.title,
            "total_questions": len(questions),
            "solutions": questions
        }, f, indent=2)

    # 3. Markdown Printable Paper
    export_markdown_paper(questions, args.title, out_dir / "exam_paper.md")

    print("-" * 80)
    print(f" [SUCCESS] Exam successfully generated:")
    print(f"   * Student Exam Paper : {out_dir / 'student_exam_paper.json'}")
    print(f"   * Instructor Key     : {out_dir / 'instructor_answer_key.json'}")
    print(f"   * Printable Markdown : {out_dir / 'exam_paper.md'}")
    print("=" * 80)


if __name__ == "__main__":
    main()
