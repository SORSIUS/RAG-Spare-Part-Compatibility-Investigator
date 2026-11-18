import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values


BACKEND = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    backend_dir: Path = BACKEND
    api_key: str = field(default="", repr=False)
    model: str = "openai/gpt-oss-120b"
    timeout_seconds: float = 45
    top_k: int = 8

    @property
    def pdf_path(self) -> Path:
        return self.backend_dir / "data/sources/automotive/denso_cabin_air_filters_2026.pdf"

    @property
    def runtime_dir(self) -> Path:
        return self.backend_dir / "data/runtime"

    @property
    def configured(self) -> bool:
        return bool(self.api_key and not self.api_key.lower().startswith(("your_", "replace", "example")))

    @classmethod
    def load(cls, backend_dir: Path = BACKEND):
        values = {**dotenv_values(backend_dir / ".env"), **os.environ}
        timeout = float(values.get("GROQ_TIMEOUT_SECONDS") or 45)
        top_k = int(values.get("RAG_TOP_K") or 8)
        if not 5 <= timeout <= 90 or not 2 <= top_k <= 12:
            raise ValueError("Use a Groq timeout of 5–90 seconds and RAG_TOP_K of 2–12.")
        return cls(backend_dir, str(values.get("GROQ_API_KEY") or "").strip(), str(values.get("GROQ_MODEL") or "openai/gpt-oss-120b").strip(), timeout, top_k)
