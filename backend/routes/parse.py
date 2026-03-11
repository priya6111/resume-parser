import os
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from db.mongo import get_recent_candidates, save_candidate
from models.candidate import Candidate
from services.resume_parser import (
    parse_resume_file,
)


parse_bp = Blueprint("parse", __name__)

ALLOWED_EXTENSIONS = {"pdf", "docx"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@parse_bp.post("/parse-resume")
def parse_resume_endpoint():
    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400

    file = request.files["file"]

    if not file or file.filename == "":
        return jsonify({"error": "Empty file name."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF and DOCX files are supported."}), 400

    extension = file.filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid4().hex}.{extension}"
    safe_name = secure_filename(unique_name)
    upload_path = os.path.join(current_app.config["UPLOAD_FOLDER"], safe_name)

    try:
        file.save(upload_path)

        result = parse_resume_file(upload_path, source_filename=file.filename)
        parsed = result.get("parsed", {})
        meta = result.get("meta", {})

        candidate = Candidate(
            name=parsed.get("name", ""),
            email=parsed.get("email", ""),
            phone=parsed.get("phone", ""),
            skills=parsed.get("skills", []),
        )

        candidate_data = candidate.to_dict()
        candidate_data["meta"] = meta
        candidate_id = save_candidate(candidate_data)
        candidate_data["id"] = candidate_id
        return jsonify({"data": candidate_data, "meta": meta}), 200

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    finally:
        if os.path.exists(upload_path):
            os.remove(upload_path)


@parse_bp.get("/candidates")
def candidates_history_endpoint():
    try:
        limit_query = request.args.get("limit", default=20, type=int)
        limit = max(1, min(limit_query, 100))
        candidates = get_recent_candidates(limit=limit)
        return jsonify({"count": len(candidates), "items": candidates}), 200
    except Exception:
        current_app.logger.exception("Failed to load candidate history")
        return jsonify(
            {
                "count": 0,
                "items": [],
                "warning": "Database is currently unavailable. Start MongoDB and click Refresh.",
            }
        ), 200
    
