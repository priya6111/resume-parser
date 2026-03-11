import importlib
import re
from pathlib import Path
import docx
import spacy
from pdfminer.high_level import extract_text

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

_nlp = None
SKILLS_DB = [
    "Python",
    "Java",
    "SQL",
    "Machine Learning",
    "HTML",
    "CSS",
    "JavaScript",
    "Flask",
]
NAME_STOPWORDS = {
    "resume",
    "summary",
    "experience",
    "education",
    "skills",
    "projects",
    "profile",
    "contact",
    "objective",
    "intern",
    "developer",
    "engineer",
    "artificial",
    "intelligence",
    "machine",
    "learning",
    "data",
    "science",
    "technology",
    "information",
}

NON_NAME_PHRASES = {
    "artificial intelligence",
    "machine learning",
    "data science",
    "computer science",
    "information technology",
}

KNOWN_EMAIL_DOMAINS = (
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "icloud.com",
    "protonmail.com",
    "live.com",
)


def get_nlp():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError as exc:
            raise RuntimeError(
                "spaCy model 'en_core_web_sm' is not installed. Run: python -m spacy download en_core_web_sm"
            ) from exc
    return _nlp


def _extract_pdf_text_with_ocr(file_path: str) -> str:
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError:
        return ""

    try:
        pages = convert_from_path(file_path, dpi=300, first_page=1, last_page=3)
    except Exception:
        return ""

    page_texts: list[str] = []
    for page in pages:
        try:
            page_text = pytesseract.image_to_string(page)
        except Exception:
            continue

        if page_text and page_text.strip():
            page_texts.append(page_text.strip())

    return "\n".join(page_texts)


def _extract_pdf_text_primary(file_path: str) -> str:
    texts: list[str] = []

    fitz_spec = importlib.util.find_spec("fitz")
    if fitz_spec is not None:
        try:
            fitz_module = importlib.import_module("fitz")
            doc = fitz_module.open(file_path)
            fitz_pages = [page.get_text("text") or "" for page in doc]
            fitz_text = "\n".join(fitz_pages).strip()
            if fitz_text:
                texts.append(fitz_text)
        except Exception:
            pass

    try:
        miner_text = extract_text(file_path) or ""
    except Exception:
        miner_text = ""

    if miner_text.strip():
        texts.append(miner_text.strip())

    if PdfReader is not None:
        try:
            reader = PdfReader(file_path)
            page_texts = [page.extract_text() or "" for page in reader.pages]
            pypdf_text = "\n".join(page_texts).strip()
            if pypdf_text:
                texts.append(pypdf_text)
        except Exception:
            pass

    if not texts:
        return ""

    merged = "\n".join(texts)
    return merged


def _should_try_ocr(text: str) -> bool:
    normalized = " ".join(text.split())
    if len(normalized) < 120:
        return True

    alpha_count = len(re.findall(r"[A-Za-z]", normalized))
    has_phone = bool(re.search(r"\+?\d[\d -]{8,12}\d", normalized))
    has_email = bool(_extract_emails(normalized))

    return alpha_count < 80 or not (has_phone or has_email)


def extract_resume_content(file_path: str, force_ocr: bool = False) -> dict:
    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        text = _extract_pdf_text_primary(file_path)

        ocr_used = False
        ocr_attempted = False
        if force_ocr or _should_try_ocr(text):
            ocr_attempted = True
            ocr_text = _extract_pdf_text_with_ocr(file_path)
            if ocr_text and len(ocr_text.strip()) >= len(text.strip()):
                text = ocr_text
                ocr_used = True
            elif ocr_text:
                text = f"{text}\n{ocr_text}".strip()
                ocr_used = True

        return {"text": text, "ocr_used": ocr_used, "ocr_attempted": ocr_attempted}

    if suffix == ".docx":
        document = docx.Document(file_path)
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        return {"text": text, "ocr_used": False, "ocr_attempted": False}

    raise ValueError("Unsupported file format. Only PDF and DOCX are allowed.")


def extract_resume_text(file_path: str) -> str:
    return extract_resume_content(file_path).get("text", "")


def _is_probable_name_line(line: str) -> bool:
    cleaned_line = line.strip()
    if not cleaned_line:
        return False

    lower_line = cleaned_line.lower()
    if "@" in cleaned_line or "http" in lower_line or "www" in lower_line:
        return False

    if lower_line in NON_NAME_PHRASES:
        return False

    words = re.findall(r"[A-Za-z]+", cleaned_line)
    if len(words) < 2 or len(words) > 4:
        return False

    if any(word.lower() in NAME_STOPWORDS for word in words):
        return False

    digit_count = len(re.findall(r"\d", cleaned_line))
    if digit_count > 1:
        return False

    return True


def extract_name(text: str, doc) -> str:
    header_lines = [line.strip() for line in text.splitlines() if line.strip()][:12]

    for index, line in enumerate(header_lines):
        if "@" not in line:
            continue

        if index > 0:
            candidate_line = header_lines[index - 1].strip()
            if _is_probable_name_line(candidate_line):
                words = re.findall(r"[A-Za-z]+", candidate_line)
                return " ".join(words)

    for line in header_lines:
        lead_match = re.match(
            r"^\s*([A-Z][A-Za-z]{1,20})(?:\s+([A-Z][A-Za-z]{0,20}|[A-Z]))(?:\s+([A-Z][A-Za-z]{0,20}|[A-Z]))?",
            line,
        )
        if lead_match:
            words = [word for word in lead_match.groups() if word]
            combined = " ".join(words).lower()
            if (
                words
                and combined not in NON_NAME_PHRASES
                and not any(word.lower() in NAME_STOPWORDS for word in words)
            ):
                return " ".join(words)

    for line in header_lines:
        if _is_probable_name_line(line):
            words = re.findall(r"[A-Za-z]+", line)
            combined = " ".join(words).lower()
            if combined not in NON_NAME_PHRASES:
                return " ".join(words)

    for entity in doc.ents:
        if entity.label_ != "PERSON":
            continue

        candidate = entity.text.strip()
        words = re.findall(r"[A-Za-z]+", candidate)
        if 2 <= len(words) <= 4 and not any(word.lower() in NAME_STOPWORDS for word in words):
            return " ".join(words)

    early_text = " ".join(text.split())[:180]
    early_match = re.search(r"\b([A-Z][a-z]{1,20})\s+([A-Z][a-z]{1,20}|[A-Z])\b", early_text)
    if early_match:
        words = [early_match.group(1), early_match.group(2)]
        if not any(word.lower() in NAME_STOPWORDS for word in words):
            return " ".join(words)

    return ""


def _name_from_email(email: str) -> str:
    if not email or "@" not in email:
        return ""

    local_part = email.split("@", 1)[0]
    cleaned = re.sub(r"[^A-Za-z]+", " ", local_part).strip()
    if not cleaned:
        return ""

    parts = [part for part in cleaned.split() if part]
    if not parts:
        return ""

    if len(parts) == 1:
        return parts[0].capitalize()

    return " ".join(part.capitalize() for part in parts[:3])


def _name_from_filename(filename: str) -> str:
    if not filename:
        return ""

    stem = Path(filename).stem
    cleaned = re.sub(r"[_\-.]+", " ", stem)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not cleaned:
        return ""

    junk_words = {
        "resume",
        "cv",
        "profile",
        "final",
        "latest",
        "updated",
        "new",
        "copy",
        "document",
        "doc",
        "file",
    }

    parts = [
        token
        for token in cleaned.split()
        if token and token.lower() not in junk_words and not token.isdigit()
    ]

    if not parts:
        return ""

    normalized = [part.capitalize() for part in parts[:3]]
    return " ".join(normalized)


def _extract_emails(text: str) -> list[str]:
    strict_pattern = re.compile(r"[a-z0-9._%+-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,10}")
    known_domain_pattern = "|".join(re.escape(domain) for domain in KNOWN_EMAIL_DOMAINS)

    normalized_text = text.lower().replace("＠", "@")
    normalized_text = re.sub(r"\(at\)|\[at\]", "@", normalized_text)
    normalized_text = re.sub(r"\(dot\)|\[dot\]", ".", normalized_text)
    normalized_text = re.sub(r"\s+at\s+", "@", normalized_text)
    normalized_text = re.sub(r"\s+dot\s+", ".", normalized_text)
    normalized_text = re.sub(r"\s*@\s*", "@", normalized_text)
    normalized_text = re.sub(r"\s*\.\s*", ".", normalized_text)

    def clean_local_part(local_part: str) -> str:
        cleaned = re.sub(r"[^a-z0-9._%+-]", "", local_part)
        cleaned = cleaned.lstrip("._%+-")
        cleaned = cleaned.rstrip("._%+-")

        if re.search(r"\d{7,}", cleaned):
            digit_run = re.search(r"\d{7,}", cleaned)
            if digit_run and digit_run.end() < len(cleaned):
                tail = cleaned[digit_run.end() :]
                if re.search(r"[a-z]", tail):
                    cleaned = tail

        if len(cleaned) > 32:
            suffix = re.search(r"([a-z][a-z0-9._%+-]{2,27})$", cleaned)
            if suffix:
                cleaned = suffix.group(1)

        return cleaned

    def add_candidate(raw_local: str, raw_domain: str, bucket: list[str]) -> None:
        local_part = clean_local_part(raw_local)
        domain_part = raw_domain.strip(".,;:)")
        candidate = f"{local_part}@{domain_part}"

        if not local_part or len(local_part) > 35:
            return
        if ".." in local_part or ".." in domain_part:
            return
        if not strict_pattern.fullmatch(candidate):
            return

        bucket.append(candidate)

    candidates: list[str] = []

    for match in strict_pattern.findall(normalized_text):
        candidates.append(match.strip(".,;:)").lower())

    noisy_at_pattern = re.compile(rf"([a-z0-9._%+-]{{3,90}})@({known_domain_pattern})", re.IGNORECASE)
    for local_part, domain_part in noisy_at_pattern.findall(normalized_text):
        add_candidate(local_part, domain_part.lower(), candidates)

    missing_at_pattern = re.compile(rf"([a-z0-9._%+-]{{3,90}})({known_domain_pattern})", re.IGNORECASE)
    for local_part, domain_part in missing_at_pattern.findall(normalized_text):
        if local_part.endswith("@"):
            local_part = local_part[:-1]
        add_candidate(local_part, domain_part.lower(), candidates)

    spaced_local_pattern = re.compile(
        rf"([a-z0-9._%+-]{{2,30}}(?:\s+[a-z0-9._%+-]{{1,30}}){{0,3}})\s*({known_domain_pattern})",
        re.IGNORECASE,
    )
    for local_part, domain_part in spaced_local_pattern.findall(normalized_text):
        compact_local = re.sub(r"\s+", "", local_part)
        add_candidate(compact_local, domain_part.lower(), candidates)

    deduped: list[str] = []
    seen: set[str] = set()
    for email in candidates:
        normalized = email.lower().strip(".,;:)")
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(normalized)

    deduped.sort(key=lambda value: (value.split("@", 1)[1] in KNOWN_EMAIL_DOMAINS, -len(value.split("@", 1)[0])), reverse=True)
    return deduped


def extract_emails_from_pdf_binary(file_path: str) -> list[str]:
    try:
        data = Path(file_path).read_bytes()
    except Exception:
        return []

    text_candidates: list[str] = []
    for encoding in ("latin-1", "utf-8", "utf-16-le"):
        try:
            text_candidates.append(data.decode(encoding, errors="ignore"))
        except Exception:
            continue

    found: list[str] = []
    seen: set[str] = set()
    for blob_text in text_candidates:
        for email in _extract_emails(blob_text):
            normalized = email.lower().strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                found.append(normalized)

    return found

def parse_resume(text: str) -> dict:
    nlp = get_nlp()
    doc = nlp(text)

    name = extract_name(text, doc)

    emails = _extract_emails(text)
    phones = re.findall(r"\+?\d[\d -]{8,12}\d", text)

    if not name and emails:
        name = _name_from_email(emails[0])

    found_skills = [skill for skill in SKILLS_DB if skill.lower() in text.lower()]

    return {
        "name": name,
        "email": emails[0] if emails else "",
        "phone": phones[0] if phones else "",
        "skills": found_skills,
    }


def ensure_candidate_name(parsed: dict, source_filename: str = "") -> dict:
    name = str(parsed.get("name", "")).strip()
    if name:
        return parsed

    email = str(parsed.get("email", "")).strip()
    fallback_name = _name_from_email(email) if email else ""

    if not fallback_name:
        fallback_name = _name_from_filename(source_filename)

    parsed["name"] = fallback_name or "Candidate"
    return parsed


def build_parse_metadata(parsed: dict, text: str, ocr_used: bool = False, ocr_attempted: bool = False) -> dict:
    name = str(parsed.get("name", "")).strip()
    email = str(parsed.get("email", "")).strip()
    phone = str(parsed.get("phone", "")).strip()
    skills = parsed.get("skills", []) if isinstance(parsed.get("skills", []), list) else []

    field_presence = {
        "name": bool(name),
        "email": bool(email),
        "phone": bool(phone),
        "skills": bool(skills),
    }

    score = 0
    if field_presence["name"]:
        score += 30
    if field_presence["email"]:
        score += 30
    if field_presence["phone"]:
        score += 20
    if field_presence["skills"]:
        score += min(20, len(skills) * 5)

    if ocr_used:
        score = min(100, score + 5)

    if score >= 85:
        quality = "high"
    elif score >= 60:
        quality = "medium"
    else:
        quality = "low"

    missing_fields = [field for field, found in field_presence.items() if not found]
    warnings: list[str] = []
    if missing_fields:
        warnings.append(f"Missing fields: {', '.join(missing_fields)}")
    if ocr_used:
        warnings.append("OCR fallback was used")
    elif ocr_attempted and (not email or not phone):
        # Show OCR setup guidance only when key contact fields remain incomplete.
        warnings.append(
            "OCR fallback attempted but no OCR text was recovered. Install Tesseract OCR and Poppler (pdftoppm) on the server PATH"
        )
    if len(" ".join(text.split())) < 120:
        warnings.append("Resume text quality is low")

    return {
        "quality": quality,
        "confidence": score,
        "ocr_used": ocr_used,
        "ocr_attempted": ocr_attempted,
        "missing_fields": missing_fields,
        "warnings": warnings,
    }


def parse_resume_file(file_path: str, source_filename: str = "") -> dict:
    suffix = Path(file_path).suffix.lower()

    extracted = extract_resume_content(file_path)
    text = extracted.get("text", "")
    parsed = parse_resume(text)

    if suffix == ".pdf" and not parsed.get("email"):
        forced_ocr_extracted = extract_resume_content(file_path, force_ocr=True)
        if forced_ocr_extracted.get("ocr_used"):
            ocr_text = forced_ocr_extracted.get("text", "")
            ocr_parsed = parse_resume(ocr_text)
            if ocr_parsed.get("email"):
                parsed["email"] = ocr_parsed.get("email", "")
            if not parsed.get("phone") and ocr_parsed.get("phone"):
                parsed["phone"] = ocr_parsed.get("phone", "")
            if len(parsed.get("skills", [])) < len(ocr_parsed.get("skills", [])):
                parsed["skills"] = ocr_parsed.get("skills", [])
            extracted = forced_ocr_extracted
            text = ocr_text

    if suffix == ".pdf" and not parsed.get("email"):
        binary_emails = extract_emails_from_pdf_binary(file_path)
        if binary_emails:
            parsed["email"] = binary_emails[0]

    parsed = ensure_candidate_name(parsed, source_filename=source_filename or Path(file_path).name)
    meta = build_parse_metadata(
        parsed,
        text,
        ocr_used=bool(extracted.get("ocr_used")),
        ocr_attempted=bool(extracted.get("ocr_attempted")),
    )

    return {
        "parsed": parsed,
        "meta": meta,
        "text": text,
        "ocr_used": bool(extracted.get("ocr_used")),
        "ocr_attempted": bool(extracted.get("ocr_attempted")),
    }
