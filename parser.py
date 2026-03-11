import re
import spacy
from pdfminer.high_level import extract_text
import docx

nlp = spacy.load("en_core_web_sm")

# Extract text
def extract_resume_text(file_path):

    if file_path.endswith(".pdf"):
        return extract_text(file_path)

    elif file_path.endswith(".docx"):
        doc = docx.Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])


# Extract details
def parse_resume(text):

    doc = nlp(text)

    name = ""
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            name = ent.text
            break

    email = re.findall(r'\S+@\S+', text)
    phone = re.findall(r'\+?\d[\d -]{8,12}\d', text)

    skills_db = [
        "Python","Java","SQL","Machine Learning",
        "HTML","CSS","JavaScript","Flask"
    ]

    skills_found = []

    for skill in skills_db:
        if skill.lower() in text.lower():
            skills_found.append(skill)

    return {
        "name": name,
        "email": email[0] if email else "",
        "phone": phone[0] if phone else "",
        "skills": ", ".join(skills_found)
    }