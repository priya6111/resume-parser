# Resume Parser Evaluation

This folder provides a repeatable way to measure parser quality on real resumes.

## 1) Add sample resumes

Put test resume files in `backend/evaluation/samples/`.

## 2) Create your dataset file

Copy `dataset.example.json` and replace values with your own ground truth.

Dataset format:

```json
[
  {
    "id": "candidate-001",
    "file": "samples/resume-001.pdf",
    "expected": {
      "name": "Full Name",
      "email": "user@example.com",
      "phone": "+911234567890",
      "skills": ["Python", "Flask", "SQL"]
    }
  }
]
```

`file` is relative to the dataset JSON location.

## 3) Run evaluator

From `backend/` directory:

```powershell
python evaluation/evaluate_parser.py --dataset evaluation/dataset.example.json
```

Optional threshold check for CI/non-regression:

```powershell
python evaluation/evaluate_parser.py `
  --dataset evaluation/dataset.example.json `
  --fail-on-threshold `
  --name-threshold 0.90 `
  --email-threshold 0.95 `
  --phone-threshold 0.90 `
  --skills-f1-threshold 0.75
```

## Report output

The script prints:
- Per-resume status for name/email/phone/skills
- Aggregate metrics:
  - `name_accuracy`
  - `email_accuracy`
  - `phone_accuracy`
  - `skills_f1`

Use these metrics before and after parser changes to confirm improvements.
