import math
import re
from collections import Counter

from app.repositories.catalogue import CatalogueSnapshot


STOP_WORDS = set("a an and are as at be by can catalogue catalog could describe do does filter filters find for from give has have how i in is it its me my of on or please show tell that the their them these they this to use using what when where which will with would you your about according information details need want know compare comparison".split())
DIMENSION_TERMS = {"dimension", "dimensions", "size", "sizes", "measurement", "measurements", "length", "width", "height", "mm"}
REFERENCE_TERMS = {"replace", "replacement", "alternative", "alternatives", "reference", "references", "equivalent", "equivalents", "cross", "oe", "oem", "compatible", "compatibility", "interchangeable"}
APPLICATION_TERMS = {"vehicle", "vehicles", "car", "cars", "fit", "fits", "fitted", "application", "applications", "model", "models", "year", "years"}


def words(text):
    return re.findall(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", text.casefold())


class RagRetriever:
    def __init__(self, snapshot: CatalogueSnapshot):
        self.snapshot = snapshot
        self.units = []
        for record in snapshot.catalogue["dimensions"]:
            dimensions = record["dimensions_mm"]
            content = f"Part number: {record['part_number']}. Length: {dimensions['length']:g} mm; width: {dimensions['width']:g} mm; height: {dimensions['height']:g} mm. These are dimensions only, not vehicle fitment approval."
            self.add("Dimensions · " + record["part_number"], content, record["evidence"], [record["part_number"]])
        for record in snapshot.catalogue["cross_references"]:
            content = f"Published cross-reference: brand {record['brand']}; external part {record['external_part']}; DENSO part {record['denso_part']}. Direction: external brand/number to DENSO candidate. Vehicle suitability is not established by this row alone."
            self.add("Cross-reference · " + record["external_part"], content, record["evidence"], [record["external_part"], record["denso_part"]])
        for record in snapshot.catalogue["applications"]:
            content = f"Catalogue application: make {record['make']}; vehicle {record['vehicle']}; production range {record['production_range']}; qualifiers: {record['qualifiers'] or 'none printed in this extracted row'}; listed DENSO parts: {', '.join(record['parts'])}. This is a catalogue mention; exact-vehicle suitability has not been verified."
            self.add("Application · " + record["make"] + " " + record["vehicle"], content, record["evidence"], record["parts"])
        for chunk in snapshot.page_chunks:
            self.add("Catalogue passage · page " + str(chunk["page_number"]), chunk["text"], {"source": chunk["source"], "page_number": chunk["page_number"], "section": "page_text", "quote": chunk["text"]}, [])
        self.counts = [Counter(words(unit["content"])) for unit in self.units]
        self.frequency = Counter()
        self.identifiers = {}
        for index, (unit, counts) in enumerate(zip(self.units, self.counts)):
            self.frequency.update(counts.keys())
            for identifier in unit["identifiers"]:
                compact = " ".join(identifier.lower().split())
                self.identifiers.setdefault(compact, set()).add(index)
        self.average_length = sum(sum(count.values()) for count in self.counts) / max(1, len(self.counts))

    def add(self, title, content, evidence, identifiers):
        self.units.append({"title": title, "content": content, "source": evidence["source"], "page_number": evidence["page_number"], "section": evidence["section"], "raw_excerpt": evidence["quote"], "identifiers": identifiers})

    def retrieve(self, question: str, top_k: int = 8) -> list[dict]:
        tokens = words(question)
        terms = set(tokens) - STOP_WORDS
        if not terms:
            return []
        exact = []
        for size in [1, 2, 3]:
            for start in range(len(tokens) - size + 1):
                identifier = " ".join(tokens[start:start + size])
                if identifier in self.identifiers and not (identifier.isdecimal() and len(identifier) <= 4):
                    if identifier not in exact:
                        exact.append(identifier)
        candidates = set.union(*(self.identifiers[identifier] for identifier in exact)) if exact else range(len(self.units))
        dimension_intent = bool(terms & DIMENSION_TERMS)
        reference_intent = bool(terms & REFERENCE_TERMS)
        application_intent = bool(terms & APPLICATION_TERMS)
        ranking = []
        for index in candidates:
            unit, counts = self.units[index], self.counts[index]
            overlap = terms & counts.keys()
            if not overlap:
                continue
            length = sum(counts.values())
            score = sum(math.log(1 + (len(self.units) - self.frequency[term] + .5) / (self.frequency[term] + .5)) * (counts[term] * 2.2 / (counts[term] + 1.2 * (.25 + .75 * length / self.average_length))) for term in overlap)
            if dimension_intent and unit["section"] == "photo_guide":
                score += 12
            if reference_intent and unit["section"] == "cross_reference":
                score += 12
            if application_intent and unit["section"] == "application":
                score += 8
            if unit["section"] == "page_text":
                score *= .55
            if not exact:
                distinctive = terms - DIMENSION_TERMS - REFERENCE_TERMS - APPLICATION_TERMS - {"part", "parts", "number", "numbers", "denso", "cabin", "air"}
                if distinctive and not (distinctive & counts.keys()):
                    continue
            ranking.append((score, index))
        ranking.sort(key=lambda item: (-item[0], item[1]))
        selected = []
        for identifier in exact:
            match = next((index for score, index in ranking if index in self.identifiers[identifier] and index not in selected), None)
            if match is not None:
                selected.append(match)
        selected.extend(index for score, index in ranking if index not in selected)
        unique = set()
        sources = []
        for index in selected:
            unit = self.units[index]
            identity = (unit["page_number"], unit["content"])
            if identity in unique:
                continue
            unique.add(identity)
            sources.append({key: value for key, value in unit.items() if key != "identifiers"} | {"id": "S" + str(len(sources) + 1), "pdf_url": f"/api/catalogue/pdf?version={self.snapshot.fingerprint}#page={unit['page_number']}"})
            if len(sources) == top_k:
                break
        return sources
