#!/usr/bin/env python3
"""
exam_engine_loader.py - Reference Exam Engine Data Consumer
============================================================
Demonstrates how an external service, exam generation engine, or API
(e.g., Ikshvaku Aptitude Arena backend) consumes and queries this question bank:
  - 25 random questions
  - Stratified blueprint: 10 easy + 10 medium + 5 hard
  - Filtering by topic, subtopics, difficulty range, and question types
  - Fast in-memory indexing with O(1) attribute lookup
"""

import os
import sys
import json
import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

# Ensure UTF-8 output encoding across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


class QuestionBankLoader:
    def __init__(self, repo_root: Optional[Path] = None):
        if repo_root is None:
            self.repo_root = Path(__file__).resolve().parent.parent
        else:
            self.repo_root = Path(repo_root)

        self.questions_dir = self.repo_root / "questions"
        self.metadata_dir = self.repo_root / "metadata"

        self.questions: List[Dict[str, Any]] = []
        self.by_id: Dict[str, Dict[str, Any]] = {}
        self.by_topic: Dict[str, List[Dict[str, Any]]] = {}
        self.by_difficulty: Dict[str, List[Dict[str, Any]]] = {}
        self.by_topic_and_diff: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

        self.load()

    def load(self):
        """Load and index all questions into memory."""
        self.questions.clear()
        self.by_id.clear()
        self.by_topic.clear()
        self.by_difficulty.clear()
        self.by_topic_and_diff.clear()

        for jf in self.questions_dir.rglob("*.json"):
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                items = data if isinstance(data, list) else [data]
                for q in items:
                    if not isinstance(q, dict) or "id" not in q:
                        continue

                    self.questions.append(q)
                    self.by_id[q["id"]] = q

                    topic = q.get("topic", "misc")
                    diff = q.get("difficulty", "medium")

                    self.by_topic.setdefault(topic, []).append(q)
                    self.by_difficulty.setdefault(diff, []).append(q)
                    self.by_topic_and_diff.setdefault(topic, {}).setdefault(diff, []).append(q)

            except Exception as exc:
                print(f"[Warning] Error loading {jf}: {exc}")

    def query(
        self,
        topics: Optional[List[str]] = None,
        subtopics: Optional[List[str]] = None,
        difficulties: Optional[List[str]] = None,
        question_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Filter questions based on query criteria."""
        results = self.questions

        if topics:
            topics_set = set(topics)
            results = [q for q in results if q.get("topic") in topics_set]

        if subtopics:
            subtopics_set = set(subtopics)
            results = [q for q in results if q.get("subtopic") in subtopics_set]

        if difficulties:
            diff_set = set(difficulties)
            results = [q for q in results if q.get("difficulty") in diff_set]

        if question_types:
            type_set = set(question_types)
            results = [q for q in results if q.get("question_type") in type_set]

        if tags:
            tag_set = set(tags)
            results = [q for q in results if tag_set.intersection(set(q.get("tags", [])))]

        return results

    def get_random_sample(self, n: int = 25, topics: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Fetch N uniformly sampled random questions, optionally restricted to specific topics."""
        pool = self.query(topics=topics)
        if len(pool) <= n:
            shuffled = list(pool)
            random.shuffle(shuffled)
            return shuffled
        return random.sample(pool, n)

    def generate_exam_blueprint(self, blueprint: Dict[str, int], topics: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Generate exam based on a difficulty quota blueprint.
        Example: {'easy': 10, 'medium': 10, 'hard': 5}
        """
        selected: List[Dict[str, Any]] = []
        for diff, count in blueprint.items():
            pool = self.query(topics=topics, difficulties=[diff])
            if len(pool) < count:
                selected.extend(pool)
            else:
                selected.extend(random.sample(pool, count))
        random.shuffle(selected)
        return selected


def demo():
    loader = QuestionBankLoader()
    print("=" * 80)
    print(" IKSHVAKU APTITUDE ARENA - QUESTION BANK CONSUMER SDK DEMO")
    print("=" * 80)
    print(f" Loaded {len(loader.questions)} questions into memory.\n")

    # Demo 1: Blueprint 10 Easy + 10 Medium + 5 Hard
    blueprint = {"easy": 10, "medium": 10, "hard": 5}
    exam_paper = loader.generate_exam_blueprint(blueprint)
    print(f"[DEMO 1] Blueprint Test Paper ({blueprint}): Selected {len(exam_paper)} questions")
    for idx, q in enumerate(exam_paper[:5], 1):
        print(f"   {idx}. [{q['id']}] ({q['difficulty'].upper()}) [{q['topic']}]: {q['question'][:60]}...")
    print(f"   ... and {len(exam_paper) - 5} more questions.\n")

    # Demo 2: Topic specific query
    percentages_q = loader.query(topics=["percentages"], difficulties=["medium"])
    print(f"[DEMO 2] Query: Topic='percentages' AND Difficulty='medium': Found {len(percentages_q)} questions.")

    # Demo 3: Total estimated exam duration
    total_time_min = sum(q.get("estimated_time_seconds", 60) for q in exam_paper) / 60
    print(f"[DEMO 3] Calculated Test Paper Time Benchmark: {total_time_min:.1f} minutes")
    print("=" * 80)


if __name__ == "__main__":
    demo()
