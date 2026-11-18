import hashlib
import re

from app.models.document_chunk import DocumentChunk


class TextChunker:
    def __init__(self, chunk_words: int = 180, overlap_words: int = 30):
        if chunk_words < 1 or not 0 <= overlap_words < chunk_words:
            raise ValueError("Require chunk_words > 0 and 0 <= overlap_words < chunk_words.")
        self.chunk_words = chunk_words
        self.overlap_words = overlap_words

    def chunk_page(self, page: dict, document_id: str) -> list[DocumentChunk]:
        text = page["text"]
        words = list(re.finditer(r"\S+", text))
        chunks = []
        step = self.chunk_words - self.overlap_words

        for first_word in range(0, len(words), step):
            last_word = min(first_word + self.chunk_words, len(words))
            start = words[first_word].start()
            end = words[last_word - 1].end()
            identity = f"{document_id}:{page['source']}:{page['page_number']}:{start}:{end}"
            chunks.append(DocumentChunk(
                chunk_id=hashlib.sha256(identity.encode()).hexdigest(),
                document_id=document_id,
                source=page["source"],
                page_number=page["page_number"],
                start_offset=start,
                end_offset=end,
                text=text[start:end],
            ))
            if last_word == len(words):
                break

        return chunks
