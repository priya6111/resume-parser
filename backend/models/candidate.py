from dataclasses import dataclass, field
from typing import List


@dataclass
class Candidate:
    name: str = ""
    email: str = ""
    phone: str = ""
    skills: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "skills": self.skills,
        }
