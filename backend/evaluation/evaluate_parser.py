import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.resume_parser import parse_resume_file


@dataclass
class RecordScore:
    record_id: str
    file_path: str
    name_correct: bool
    email_correct: bool
    phone_correct: bool
    skill_precision: float
    skill_recall: float
    skill_f1: float
    missing_file: bool = False
    error: str = ""


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def normalize_email(value: str) -> str:
    return normalize_text(value)


def normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def normalize_skill(value: str) -> str:
    return normalize_text(value)


def safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def score_record(record: dict[str, Any], dataset_dir: Path) -> RecordScore:
    record_id = str(record.get("id") or "unknown")
    file_relative = str(record.get("file") or "")
    file_path = (dataset_dir / file_relative).resolve()

    if not file_relative or not file_path.exists():
        return RecordScore(
            record_id=record_id,
            file_path=str(file_path),
            name_correct=False,
            email_correct=False,
            phone_correct=False,
            skill_precision=0.0,
            skill_recall=0.0,
            skill_f1=0.0,
            missing_file=True,
            error="File not found",
        )

    expected = record.get("expected", {}) if isinstance(record.get("expected"), dict) else {}

    try:
        result = parse_resume_file(str(file_path), source_filename=file_path.name)
        parsed = result.get("parsed", {})
    except Exception as exc:
        return RecordScore(
            record_id=record_id,
            file_path=str(file_path),
            name_correct=False,
            email_correct=False,
            phone_correct=False,
            skill_precision=0.0,
            skill_recall=0.0,
            skill_f1=0.0,
            error=str(exc),
        )

    expected_name = normalize_text(str(expected.get("name", "")))
    expected_email = normalize_email(str(expected.get("email", "")))
    expected_phone = normalize_phone(str(expected.get("phone", "")))
    expected_skills = {
        normalize_skill(skill)
        for skill in expected.get("skills", [])
        if isinstance(skill, str) and normalize_skill(skill)
    }

    actual_name = normalize_text(str(parsed.get("name", "")))
    actual_email = normalize_email(str(parsed.get("email", "")))
    actual_phone = normalize_phone(str(parsed.get("phone", "")))
    actual_skills = {
        normalize_skill(skill)
        for skill in parsed.get("skills", [])
        if isinstance(skill, str) and normalize_skill(skill)
    }

    name_correct = actual_name == expected_name
    email_correct = actual_email == expected_email
    phone_correct = actual_phone == expected_phone

    true_positive = len(actual_skills.intersection(expected_skills))
    precision = safe_div(true_positive, len(actual_skills)) if actual_skills else 0.0
    recall = safe_div(true_positive, len(expected_skills)) if expected_skills else 0.0
    f1 = safe_div(2 * precision * recall, (precision + recall)) if (precision + recall) else 0.0

    return RecordScore(
        record_id=record_id,
        file_path=str(file_path),
        name_correct=name_correct,
        email_correct=email_correct,
        phone_correct=phone_correct,
        skill_precision=precision,
        skill_recall=recall,
        skill_f1=f1,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate resume parser extraction quality")
    parser.add_argument(
        "--dataset",
        default="evaluation/dataset.example.json",
        help="Path to evaluation dataset JSON (relative to backend directory or absolute)",
    )
    parser.add_argument(
        "--fail-on-threshold",
        action="store_true",
        help="Return non-zero exit code if thresholds are not met",
    )
    parser.add_argument("--name-threshold", type=float, default=0.9)
    parser.add_argument("--email-threshold", type=float, default=0.95)
    parser.add_argument("--phone-threshold", type=float, default=0.9)
    parser.add_argument("--skills-f1-threshold", type=float, default=0.75)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.is_absolute():
        dataset_path = (BACKEND_DIR / dataset_path).resolve()

    if not dataset_path.exists():
        print(f"Dataset file not found: {dataset_path}")
        return 2

    try:
        records = json.loads(dataset_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Failed to read dataset JSON: {exc}")
        return 2

    if not isinstance(records, list) or not records:
        print("Dataset must be a non-empty JSON array")
        return 2

    dataset_dir = dataset_path.parent
    results = [score_record(record, dataset_dir) for record in records]

    total = len(results)
    valid_results = [r for r in results if not r.missing_file and not r.error]

    name_acc = safe_div(sum(1 for r in valid_results if r.name_correct), len(valid_results))
    email_acc = safe_div(sum(1 for r in valid_results if r.email_correct), len(valid_results))
    phone_acc = safe_div(sum(1 for r in valid_results if r.phone_correct), len(valid_results))
    avg_skills_f1 = safe_div(sum(r.skill_f1 for r in valid_results), len(valid_results))

    print("=== Resume Parser Evaluation ===")
    print(f"Dataset: {dataset_path}")
    print(f"Total records: {total}")
    print(f"Valid records: {len(valid_results)}")
    print("")

    for result in results:
        print(f"[{result.record_id}] {result.file_path}")
        if result.missing_file:
            print("  status: missing file")
        elif result.error:
            print(f"  status: error ({result.error})")
        else:
            print(
                "  name: {0} | email: {1} | phone: {2} | skills_f1: {3:.2f}".format(
                    "ok" if result.name_correct else "x",
                    "ok" if result.email_correct else "x",
                    "ok" if result.phone_correct else "x",
                    result.skill_f1,
                )
            )
        print("")

    print("--- Aggregate Metrics ---")
    print(f"name_accuracy:  {name_acc:.2%}")
    print(f"email_accuracy: {email_acc:.2%}")
    print(f"phone_accuracy: {phone_acc:.2%}")
    print(f"skills_f1:      {avg_skills_f1:.2%}")

    thresholds_met = (
        name_acc >= args.name_threshold
        and email_acc >= args.email_threshold
        and phone_acc >= args.phone_threshold
        and avg_skills_f1 >= args.skills_f1_threshold
    )

    if args.fail_on_threshold:
        if thresholds_met:
            print("\nThreshold check: PASS")
            return 0
        print("\nThreshold check: FAIL")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
