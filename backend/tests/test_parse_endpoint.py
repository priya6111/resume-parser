import io

import routes.parse as parse_routes


def test_parse_resume_rejects_missing_file_field(client):
    response = client.post("/parse-resume", data={}, content_type="multipart/form-data")

    assert response.status_code == 400
    assert response.get_json()["error"] == "No file provided."


def test_parse_resume_rejects_empty_filename(client):
    data = {"file": (io.BytesIO(b""), "")}

    response = client.post("/parse-resume", data=data, content_type="multipart/form-data")

    assert response.status_code == 400
    assert response.get_json()["error"] == "Empty file name."


def test_parse_resume_rejects_unsupported_extension(client):
    data = {"file": (io.BytesIO(b"hello"), "resume.txt")}

    response = client.post("/parse-resume", data=data, content_type="multipart/form-data")

    assert response.status_code == 400
    assert response.get_json()["error"] == "Only PDF and DOCX files are supported."


def test_parse_resume_success_returns_data_and_meta(client, monkeypatch):
    captured = {}

    def fake_parse_resume_file(file_path, source_filename=""):
        captured["file_path"] = file_path
        captured["source_filename"] = source_filename
        return {
            "parsed": {
                "name": "Jane Doe",
                "email": "jane@example.com",
                "phone": "+911234567890",
                "skills": ["Python", "Flask"],
            },
            "meta": {
                "quality": "high",
                "confidence": 95,
                "ocr_used": False,
                "ocr_attempted": False,
                "missing_fields": [],
                "warnings": [],
            },
        }

    def fake_save_candidate(candidate_data):
        captured["saved_candidate_data"] = candidate_data
        return "abc123"

    monkeypatch.setattr(parse_routes, "parse_resume_file", fake_parse_resume_file)
    monkeypatch.setattr(parse_routes, "save_candidate", fake_save_candidate)

    data = {"file": (io.BytesIO(b"%PDF-1.4"), "resume.pdf")}
    response = client.post("/parse-resume", data=data, content_type="multipart/form-data")

    assert response.status_code == 200

    body = response.get_json()
    assert body["data"]["id"] == "abc123"
    assert body["data"]["name"] == "Jane Doe"
    assert body["data"]["email"] == "jane@example.com"
    assert body["data"]["phone"] == "+911234567890"
    assert body["data"]["skills"] == ["Python", "Flask"]
    assert body["meta"]["quality"] == "high"

    assert captured["source_filename"] == "resume.pdf"
    assert captured["file_path"].endswith(".pdf")
    assert captured["saved_candidate_data"]["meta"]["quality"] == "high"
