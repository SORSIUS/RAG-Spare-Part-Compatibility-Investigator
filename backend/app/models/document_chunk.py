from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    document_id: str
    source: str
    page_number: int
    start_offset: int
    end_offset: int
    text: str
