import os
from datetime import datetime, timezone

from pymongo import MongoClient

from services.resume_parser import ensure_candidate_name


_client = None
_db = None


def get_db():
    global _client, _db

    if _db is None:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGO_DB_NAME", "resume_parser")
        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        _db = _client[db_name]

    return _db


def save_candidate(candidate_data: dict) -> str:
    db = get_db()
    payload = {**candidate_data, "created_at": datetime.now(timezone.utc)}
    result = db.candidates.insert_one(payload)
    return str(result.inserted_id)


def get_recent_candidates(limit: int = 20) -> list[dict]:
    db = get_db()

    cursor = db.candidates.find().sort("created_at", -1).limit(limit)
    candidates: list[dict] = []

    for item in cursor:
        created_at = item.get("created_at")
        if hasattr(created_at, "isoformat"):
            created_at_value = created_at.isoformat()
        elif isinstance(created_at, str):
            created_at_value = created_at
        else:
            created_at_value = None

        parsed_item = ensure_candidate_name(
            {
                "name": item.get("name", ""),
                "email": item.get("email", ""),
            }
        )

        candidates.append(
            {
                "id": str(item.get("_id")),
                "name": parsed_item.get("name", "Candidate"),
                "email": item.get("email", ""),
                "phone": item.get("phone", ""),
                "skills": item.get("skills", []),
                "created_at": created_at_value,
            }
        )

    return candidates
