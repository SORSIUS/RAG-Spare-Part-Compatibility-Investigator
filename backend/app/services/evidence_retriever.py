import math
import re
from collections import Counter


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", text.lower())


class EvidenceRetriever:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.term_counts = [Counter(tokenize(chunk["text"])) for chunk in chunks]
        self.document_frequency = Counter()
        for counts in self.term_counts:
            self.document_frequency.update(counts.keys())

    def search(self, question: str, limit: int = 5) -> list[dict]:
        if limit < 1:
            raise ValueError("Result limit must be positive.")
        terms = set(tokenize(question))
        ranked = []
        for chunk, counts in zip(self.chunks, self.term_counts):
            score = sum(
                (1 + math.log(counts[term]))
                * (1 + math.log((len(self.chunks) + 1) / (self.document_frequency[term] + 1)))
                for term in terms if counts[term]
            )
            if score:
                ranked.append({**chunk, "score": round(score, 6)})
        return sorted(ranked, key=lambda hit: (-hit["score"], hit["source"], hit["page_number"], hit["start_offset"]))[:limit]

    def part_evidence(self, part_number: str) -> list[dict]:
        hits = []
        for chunk in self.chunks:
            headers = list(re.finditer(r"^Part number:\s*([^\r\n]+)", chunk["text"], re.MULTILINE | re.IGNORECASE))
            for position, header in enumerate(headers):
                if header.group(1).strip().casefold() != part_number.casefold():
                    continue
                end = headers[position + 1].start() if position + 1 < len(headers) else len(chunk["text"])
                hits.append({**chunk, "record_text": chunk["text"][header.end():end]})
        return hits
