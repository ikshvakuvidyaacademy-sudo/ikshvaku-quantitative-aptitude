#!/usr/bin/env python3
"""
validate_questions.py - Ikshvaku Aptitude Arena Question Bank Validator
========================================================================
Validates all question JSON files in the repository against:
  1. Malformed JSON syntax
  2. Missing required fields
  3. Valid difficulty enum ('easy', 'medium', 'hard', 'very_hard')
  4. Valid question_type enum ('single_choice', 'multiple_choice', 'numerical', 'true_false')
  5. Duplicate question IDs across the repository
  6. Duplicate question texts across the repository
  7. Missing answers or empty answer strings/arrays
  8. Invalid options structures and lengths
  9. Answer correctness:
     - For 'single_choice' & 'true_false': answer MUST be exact member of options
     - For 'multiple_choice': answer MUST be a list whose items are all members of options
  10. Empty explanations (min 10 characters)
  11. Valid estimated_time_seconds (positive integer between 10 and 600)
  12. Valid topic and subtopic verified against metadata/topics.json
  13. ID format conformance: QA-[TOPIC_CODE]-[6 DIGIT NUMBER]
  14. Valid tags (non-empty list of strings)

Exit Code:
  0: All questions pass validation successfully.
  1: Validation errors found (detailed diagnostics emitted to stderr).
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple

# Ensure UTF-8 output encoding across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

REQUIRED_FIELDS = [
    "id",
    "subject",
    "topic",
    "subtopic",
    "difficulty",
    "question_type",
    "question",
    "options",
    "answer",
    "explanation",
    "estimated_time_seconds",
    "tags"
]

VALID_DIFFICULTIES = {"easy", "medium", "hard", "very_hard"}
VALID_QUESTION_TYPES = {"single_choice", "multiple_choice", "numerical", "true_false"}
ID_REGEX = re.compile(r"^QA-([A-Z0-9]+)-([0-9]{6})$")


def load_metadata_taxonomy(metadata_dir: Path) -> Tuple[Dict[str, str], Dict[str, Set[str]]]:
    """
    Loads topics.json and returns:
      - topic_slug_to_code: e.g. {'percentages': 'PERCENTAGE', ...}
      - topic_subtopics: e.g. {'percentages': {'percentage_basics', ...}}
    """
    topics_file = metadata_dir / "topics.json"
    if not topics_file.exists():
        raise FileNotFoundError(f"Metadata topics file not found at: {topics_file}")

    with open(topics_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    topic_slug_to_code = {}
    topic_subtopics = {}

    for item in data.get("topics", []):
        slug = item["slug"]
        code = item["code"]
        topic_slug_to_code[slug] = code
        subtopics = {sub["slug"] for sub in item.get("subtopics", [])}
        topic_subtopics[slug] = subtopics

    return topic_slug_to_code, topic_subtopics


class QuestionValidator:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.metadata_dir = repo_root / "metadata"
        self.questions_dir = repo_root / "questions"
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.seen_ids: Dict[str, str] = {}  # id -> file_path
        self.seen_questions: Dict[str, str] = {}  # normalized text -> id
        self.total_questions = 0
        self.total_files = 0

        self.topic_slug_to_code, self.topic_subtopics = load_metadata_taxonomy(self.metadata_dir)

    def log_error(self, file_path: Path, q_id: str, message: str):
        rel_path = file_path.relative_to(self.repo_root) if file_path.is_relative_to(self.repo_root) else file_path
        prefix = f"[{rel_path} | {q_id}]" if q_id else f"[{rel_path}]"
        self.errors.append(f"ERROR {prefix}: {message}")

    def log_warning(self, file_path: Path, q_id: str, message: str):
        rel_path = file_path.relative_to(self.repo_root) if file_path.is_relative_to(self.repo_root) else file_path
        prefix = f"[{rel_path} | {q_id}]" if q_id else f"[{rel_path}]"
        self.warnings.append(f"WARNING {prefix}: {message}")

    def validate_single_question(self, q: Any, file_path: Path, index: int):
        if not isinstance(q, dict):
            self.log_error(file_path, f"Index #{index}", f"Question entry must be a JSON object, got {type(q).__name__}")
            return

        q_id = q.get("id", f"Index #{index}")

        # 1. Missing required fields
        for field in REQUIRED_FIELDS:
            if field not in q:
                self.log_error(file_path, q_id, f"Missing mandatory field '{field}'")

        # 2. Subject verification
        if q.get("subject") != "quantitative_aptitude":
            self.log_error(file_path, q_id, f"Invalid subject '{q.get('subject')}'. Must be 'quantitative_aptitude'")

        # 3. ID format & uniqueness
        if "id" in q:
            match = ID_REGEX.match(q["id"])
            if not match:
                self.log_error(file_path, q_id, f"ID '{q['id']}' does not match QA-[TOPIC_CODE]-[6_DIGIT_NUMBER] (e.g. QA-PERCENTAGE-000001)")
            else:
                code_in_id = match.group(1)
                topic = q.get("topic")
                expected_code = self.topic_slug_to_code.get(topic)
                if expected_code and code_in_id != expected_code:
                    self.log_error(file_path, q_id, f"ID topic code '{code_in_id}' does not match registered code '{expected_code}' for topic '{topic}'")

            if q["id"] in self.seen_ids:
                prev_file = self.seen_ids[q["id"]]
                self.log_error(file_path, q_id, f"Duplicate Question ID detected! Already used in '{prev_file}'")
            else:
                self.seen_ids[q["id"]] = str(file_path.relative_to(self.repo_root))

        # 4. Topic and Subtopic validation against metadata
        topic = q.get("topic")
        if topic not in self.topic_slug_to_code:
            self.log_error(file_path, q_id, f"Unknown topic '{topic}'. Must be one of registered topics in metadata/topics.json")
        else:
            subtopic = q.get("subtopic")
            allowed_subtopics = self.topic_subtopics[topic]
            if subtopic not in allowed_subtopics:
                self.log_error(file_path, q_id, f"Subtopic '{subtopic}' is not registered under topic '{topic}'. Allowed: {sorted(allowed_subtopics)}")

        # 5. Difficulty validation
        diff = q.get("difficulty")
        if diff not in VALID_DIFFICULTIES:
            self.log_error(file_path, q_id, f"Invalid difficulty '{diff}'. Allowed: {sorted(VALID_DIFFICULTIES)}")

        # 6. Question Type validation
        q_type = q.get("question_type")
        if q_type not in VALID_QUESTION_TYPES:
            self.log_error(file_path, q_id, f"Invalid question_type '{q_type}'. Allowed: {sorted(VALID_QUESTION_TYPES)}")

        # 7. Question statement validation & uniqueness
        q_text = q.get("question")
        if not isinstance(q_text, str) or len(q_text.strip()) < 10:
            self.log_error(file_path, q_id, "Question text must be a non-empty string with at least 10 characters")
        else:
            norm_text = re.sub(r"\s+", " ", q_text.strip().lower())
            if norm_text in self.seen_questions:
                orig_id = self.seen_questions[norm_text]
                self.log_error(file_path, q_id, f"Duplicate question text detected! Identical to question '{orig_id}'")
            else:
                self.seen_questions[norm_text] = q.get("id", "UNKNOWN")

        # 8. Options and Answer logic per question type
        options = q.get("options")
        answer = q.get("answer")

        if not isinstance(options, list):
            self.log_error(file_path, q_id, f"Field 'options' must be a list, got {type(options).__name__}")
        else:
            # Check individual options are strings
            for opt_idx, opt in enumerate(options):
                if not isinstance(opt, str) or not opt.strip():
                    self.log_error(file_path, q_id, f"Option index {opt_idx} is empty or not a string: {opt!r}")

            # Specific rules by question type
            if q_type == "single_choice":
                if len(options) < 3 or len(options) > 6:
                    self.log_error(file_path, q_id, f"single_choice question must have between 3 and 6 options, found {len(options)}")
                if not isinstance(answer, str) or not answer.strip():
                    self.log_error(file_path, q_id, "single_choice question answer must be a non-empty string")
                elif answer not in options:
                    self.log_error(file_path, q_id, f"Answer '{answer}' is NOT present among options: {options}")

            elif q_type == "multiple_choice":
                if len(options) < 3 or len(options) > 6:
                    self.log_error(file_path, q_id, f"multiple_choice question must have between 3 and 6 options, found {len(options)}")
                if not isinstance(answer, list) or len(answer) == 0:
                    self.log_error(file_path, q_id, "multiple_choice question answer must be a non-empty list of correct options")
                else:
                    for ans_item in answer:
                        if not isinstance(ans_item, str) or ans_item not in options:
                            self.log_error(file_path, q_id, f"multiple_choice answer item '{ans_item}' is not in options: {options}")

            elif q_type == "true_false":
                if len(options) != 2:
                    self.log_error(file_path, q_id, f"true_false question must have exactly 2 options (e.g. ['True', 'False']), found {len(options)}")
                if not isinstance(answer, str) or answer not in options:
                    self.log_error(file_path, q_id, f"true_false answer '{answer}' is not in options: {options}")

            elif q_type == "numerical":
                if len(options) != 0:
                    self.log_error(file_path, q_id, f"numerical question should have empty options list, found {len(options)}")
                if not isinstance(answer, (str, int, float)) or str(answer).strip() == "":
                    self.log_error(file_path, q_id, "numerical question answer must be a valid non-empty string or number")

        # 9. Explanation validation
        explanation = q.get("explanation")
        if not isinstance(explanation, str) or len(explanation.strip()) < 10:
            self.log_error(file_path, q_id, "Field 'explanation' must be a detailed string with at least 10 characters")

        # 10. Estimated time validation
        time_sec = q.get("estimated_time_seconds")
        if not isinstance(time_sec, int) or time_sec < 10 or time_sec > 600:
            self.log_error(file_path, q_id, f"Field 'estimated_time_seconds' must be an integer between 10 and 600, got {time_sec}")

        # 11. Tags validation
        tags = q.get("tags")
        if not isinstance(tags, list) or len(tags) == 0:
            self.log_error(file_path, q_id, "Field 'tags' must be a non-empty list of tag strings")
        else:
            for t in tags:
                if not isinstance(t, str) or len(t.strip()) < 2:
                    self.log_error(file_path, q_id, f"Tag '{t}' is too short or not a string")

        self.total_questions += 1

    def validate_file(self, file_path: Path):
        self.total_files += 1
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            self.log_error(file_path, "", f"Malformed JSON syntax: {exc}")
            return
        except Exception as exc:
            self.log_error(file_path, "", f"Failed to read file: {exc}")
            return

        if isinstance(data, list):
            for idx, item in enumerate(data):
                self.validate_single_question(item, file_path, idx)
        elif isinstance(data, dict):
            self.validate_single_question(data, file_path, 0)
        else:
            self.log_error(file_path, "", f"Root JSON element must be array of questions or single question object, got {type(data).__name__}")

    def run(self, target_path: Path = None) -> bool:
        scan_dir = target_path if target_path else self.questions_dir
        if not scan_dir.exists():
            self.log_error(scan_dir, "", f"Target directory does not exist: {scan_dir}")
            return False

        json_files = sorted(list(scan_dir.rglob("*.json"))) if scan_dir.is_dir() else [scan_dir]
        if not json_files:
            self.log_warning(scan_dir, "", "No JSON question files found to validate.")

        for jf in json_files:
            self.validate_file(jf)

        print("=" * 80)
        print(" IKSHVAKU APTITUDE ARENA - QUESTION BANK VALIDATION REPORT")
        print("=" * 80)
        print(f" Files Scanned     : {self.total_files}")
        print(f" Questions Checked : {self.total_questions}")
        print(f" Unique IDs Logged : {len(self.seen_ids)}")
        print(f" Total Warnings    : {len(self.warnings)}")
        print(f" Total Errors      : {len(self.errors)}")
        print("-" * 80)

        if self.warnings:
            print("\nWARNINGS:")
            for w in self.warnings:
                print(f"  * {w}")

        if self.errors:
            print("\nERRORS DETECTED:")
            for e in self.errors:
                print(f"  * {e}", file=sys.stderr)
            print("\nFAILED: Repository has validation violations. Please rectify errors above.", file=sys.stderr)
            return False

        print("\nSUCCESS: All questions passed strict schema, taxonomic, and logic validation!")
        print("=" * 80)
        return True


def main():
    parser = argparse.ArgumentParser(description="Validate Ikshvaku Quantitative Aptitude Question Bank.")
    parser.add_argument("--path", type=str, default=None, help="Optional specific file or directory path to validate.")
    args = parser.parse_args()

    # Determine repository root (one level up from scripts directory)
    repo_root = Path(__file__).resolve().parent.parent
    validator = QuestionValidator(repo_root)

    target_path = Path(args.path).resolve() if args.path else None
    success = validator.run(target_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
