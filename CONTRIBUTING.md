# Contributing to Ikshvaku Quantitative Aptitude Question Bank

Thank you for your interest in contributing to the **Ikshvaku Quantitative Aptitude** repository, the official open question bank for the **Ikshvaku Aptitude Arena** by **Ikshvaku Vidya Academy** ("Practice. Think. Compete.").

This repository serves strictly as a **data bank**. It does not contain frontend UI, exam timers, user auth, or exam-generation application logic. All contributions must adhere to our strict JSON schema, mathematical validation, and pedagogical standards.

---

## 1. Guiding Principles for Question Design

Every quantitative question in this bank must test **genuine cognitive aptitude**, reasoning, and conceptual depth.

### Avoid:
- Meaningless rote arithmetic without reasoning.
- Trivial questions with obvious single-step giveaways.
- Repeated template questions with merely altered variables.
- Ambiguous or misleading phrasing.
- Multiple correct options for `single_choice` questions.
- Mathematically contradictory or impossible conditions.

### Prefer:
- Competitive exam calibre (CAT, GMAT, GRE, Banking PO, SSC CGL).
- Real-world scenarios (finance, engineering, logistics, demographics).
- Plausible distractors modeled after common cognitive misconceptions.
- Step-by-step, self-contained mathematical explanations that teach the core principle.

---

## 2. Question JSON Structure & Schema

All questions must adhere to `schema/question-schema.json`.

```json
{
  "id": "QA-PERCENTAGE-000001",
  "subject": "quantitative_aptitude",
  "topic": "percentages",
  "subtopic": "percentage_increase",
  "difficulty": "medium",
  "question_type": "single_choice",
  "question": "A student's marks increase from 240 to 300. What is the percentage increase?",
  "options": [
    "20%",
    "25%",
    "30%",
    "35%"
  ],
  "answer": "25%",
  "explanation": "Increase = 300 - 240 = 60. Percentage increase = (60 / 240) × 100 = 25%.",
  "estimated_time_seconds": 30,
  "tags": [
    "percentage",
    "increase",
    "basic-arithmetic"
  ]
}
```

### Required Fields:
- `id`: Unique identifier formatted as `QA-[TOPIC_CODE]-[6 DIGIT NUMBER]` (e.g. `QA-PERCENTAGE-000001`). Never reuse an existing ID.
- `subject`: Must be `"quantitative_aptitude"`.
- `topic`: Registered topic slug from `metadata/topics.json`.
- `subtopic`: Registered subtopic slug from `metadata/topics.json`.
- `difficulty`: One of `"easy"`, `"medium"`, `"hard"`, `"very_hard"`.
- `question_type`: One of `"single_choice"`, `"multiple_choice"`, `"numerical"`, `"true_false"`.
- `question`: Unambiguous problem statement (minimum 10 characters).
- `options`: Array of option strings (empty for `"numerical"`).
- `answer`: String for `single_choice`, `true_false`, `numerical`; list of strings for `multiple_choice`.
- `explanation`: Detailed mathematical derivation and shortcut rationale (minimum 10 characters).
- `estimated_time_seconds`: Integer between 10 and 600 representing realistic solve duration.
- `tags`: Non-empty list of semantic tags.

---

## 3. Calibrating Difficulty

Difficulty is calibrated using the **Ikshvaku Cognitive Difficulty Framework (ICDF)** defined in `metadata/difficulty-levels.json`:

| Level | Reasoning Steps | Calculation Load | Benchmark Time | Distractors |
|---|---|---|---|---|
| **Easy** | 1 - 2 steps | Direct arithmetic / formula | 30s (15-45s) | Distinct; straightforward arithmetic errors |
| **Medium** | 2 - 3 steps | Moderate algebra / fractions | 60s (40-80s) | Plausible intermediate values |
| **Hard** | 3 - 5 steps | Strategic variable elimination / quadratic / geometry | 90s (70-130s) | Trap-prone; cognitive bias points |
| **Very Hard** | 5+ steps | Invariant detection / Diophantine / modular | 150s (110-240s) | Highly sophisticated near-miss derivations |

---

## 4. Chunking Strategy for Scale

To ensure the repository scales to **500,000+ questions** without creating unmanageable files or Git merge conflicts:
- Questions are organized by topic and difficulty:
  ```
  questions/<topic>/<difficulty>/<topic>_<difficulty>_<chunk_number>.json
  ```
- Each chunk file contains an array of question JSON objects (recommended 100-500 questions per chunk).
- When a chunk reaches capacity, create a new sequential file (e.g., `percentages_easy_002.json`).

---

## 5. Local Quality Assurance Workflow

Before submitting a Pull Request, run the validation and quality assurance scripts:

### Step 1: Validate Schema & Taxonomy
```bash
python scripts/validate_questions.py
```
*Must pass with 0 errors and 0 warnings.*

### Step 2: Check for Duplicates & Structural Clones
```bash
python scripts/detect_duplicates.py --threshold 0.85
```
*Ensures no duplicate or clone questions exist across the entire repository.*

### Step 3: Refresh Repository Statistics
```bash
python scripts/generate_statistics.py
```
*Updates `metadata/question-counts.json` with your added questions.*

---

## 6. Pull Request Checklist

When submitting a PR:
- [ ] Added question(s) strictly adhere to `schema/question-schema.json`.
- [ ] Question ID matches registered topic code in `metadata/topics.json`.
- [ ] Answer is verified and matches options exactly.
- [ ] Explanation contains full step-by-step mathematical reasoning.
- [ ] `validate_questions.py` passes with zero errors.
- [ ] `detect_duplicates.py` flags zero duplicates.
- [ ] `generate_statistics.py` has been executed to update `metadata/question-counts.json`.
- [ ] Commits follow Conventional Commits (e.g., `feat(percentages): add 50 hard interest questions`).
