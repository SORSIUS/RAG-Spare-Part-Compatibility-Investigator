"""Directed OEM-to-aftermarket references, derived from reviewed table cells.

Never pair grouped cells or infer reverse/transitive interchangeability.
"""
import json
import re

from app.repositories.fitments import FitmentRepository, NOTICE
from app.services.kyb_fitment_parser import COLUMNS, SCHEMA


def normalize(value):
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def direct_reference(record):
    """Accept only a single OEM and single aftermarket number in matching cells."""
    column = next((c for c, axle, component, oe in COLUMNS
                   if oe is not None and axle == record["axle"]
                   and component == record["component"]), None)
    columns = record.get("raw_row", {}).get("columns", [])
    if column is None or len(columns) <= column - 2:
        return None
    alternatives = str(columns[column - 2]).split()
    originals = record.get("oem_group", [])
    if len(originals) != 1 or len(alternatives) != 1 or alternatives[0] != record["part_number"]:
        return None
    return normalize(originals[0])


class ReplacementRepository:
    def __init__(self, runtime):
        self.fitments = FitmentRepository(runtime)
        with self.fitments.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS replacement_builds
                  (sha TEXT PRIMARY KEY, version TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS replacement_links
                  (id TEXT PRIMARY KEY, sha TEXT NOT NULL, brand TEXT NOT NULL,
                   original TEXT NOT NULL, alternative TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS replacement_original
                  ON replacement_links(brand, original);
                CREATE TABLE IF NOT EXISTS external_reference_sources
                  (sha TEXT PRIMARY KEY, schema TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS external_references
                  (id TEXT PRIMARY KEY, sha TEXT NOT NULL, brand TEXT NOT NULL,
                   original TEXT NOT NULL, body TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS external_original ON external_references(brand,original);
            """)

    def replace_external_source(self, sha, schema, records):
        with self.fitments.connect() as db:
            db.execute("DELETE FROM external_references WHERE sha=?", (sha,))
            db.executemany("INSERT INTO external_references VALUES(?,?,?,?,?)",
                           [(r["id"], sha, r["original_brand"], normalize(r["original_part"]), json.dumps(r)) for r in records])
            db.execute("INSERT OR REPLACE INTO external_reference_sources VALUES(?,?)", (sha, schema))

    def refresh(self):
        # Only the reviewed adapter can establish cell alignment. New adapters
        # must explicitly opt in; arbitrary uploaded PDFs cannot create links.
        with self.fitments.connect() as db:
            sources = db.execute("SELECT sha,schema FROM fitment_sources").fetchall()
            db.execute("DELETE FROM replacement_links WHERE sha NOT IN (SELECT sha FROM fitment_sources)")
            db.execute("DELETE FROM replacement_builds WHERE sha NOT IN (SELECT sha FROM fitment_sources)")
            for sha, schema in sources:
                version = schema + ":single-cell-v1"
                if db.execute("SELECT 1 FROM replacement_builds WHERE sha=? AND version=?", (sha, version)).fetchone():
                    continue
                db.execute("DELETE FROM replacement_links WHERE sha=?", (sha,))
                if schema == SCHEMA:
                    for identifier, body in db.execute("SELECT id,body FROM fitments WHERE sha=?", (sha,)).fetchall():
                        record = json.loads(body)
                        original = direct_reference(record)
                        if original:
                            db.execute("INSERT INTO replacement_links VALUES(?,?,?,?,?)",
                                       (identifier, sha, record["make"], original, record["part_number"]))
                db.execute("INSERT OR REPLACE INTO replacement_builds VALUES(?,?)", (sha, version))

    def search(self, brand, part, limit=24):
        self.refresh()
        with self.fitments.connect() as db:
            args = (brand.strip(), normalize(part))
            total = db.execute("SELECT count(*) FROM replacement_links WHERE brand=? COLLATE NOCASE AND original=?", args).fetchone()[0]
            rows = db.execute("""SELECT f.body,r.original FROM replacement_links r
                JOIN fitments f ON f.id=r.id
                WHERE r.brand=? COLLATE NOCASE AND r.original=?
                ORDER BY f.make,f.model,f.start_year,f.id LIMIT ?""", (*args, limit)).fetchall()
            external_total = db.execute("SELECT count(*) FROM external_references WHERE brand=? COLLATE NOCASE AND original=?", args).fetchone()[0]
            external_rows = db.execute("SELECT body,original FROM external_references WHERE brand=? COLLATE NOCASE AND original=? ORDER BY id LIMIT ?", (*args, max(0, limit-len(rows)))).fetchall()
            total += external_total
            rows.extend(external_rows)
        records = []
        for body, original in rows:
            record = json.loads(body)
            record.update(original_part=original, original_brand=record["make"],
                          relationship=record.get("relationship", "published_single_cell_reference"),
                          pdf_url=f"/api/documents/{record['source_sha256']}/pdf#page={record['page_number']}")
            records.append(record)
        return {"records": records, "total": total, "limit": limit,
                "status": "published_reference" if records else "not_documented",
                "message": "I found published alternatives below. Check each reference's vehicle conditions before choosing." if records else "I checked the imported original-number reference tables but could not confirm a replacement for this number. Check the number on the part, or ask the chat with your car model, year, engine and component so it can search the application catalogues too.",
                "next_steps": [] if records else ["Check the original brand and number, including any suffix.", "Ask using model, year, engine, market and the component name; a part number is optional.", "Add the vehicle's OEM parts diagram or a manufacturer application catalogue if these are missing."],
                "notice": NOTICE + " These are directed references within the printed application, not universal substitutes. No result means no documented link in this index."}

    def question_sources(self, question, limit):
        # Require an explicit make and original identifier; never guess a part
        # from a generic vehicle name or confuse it with an aftermarket number.
        brands = {v["make"] for v in self.fitments.options()["vehicles"]}
        with self.fitments.connect() as db:
            brands.update(row[0] for row in db.execute("SELECT DISTINCT brand FROM external_references"))
        matches = [brand for brand in brands if re.search(r"\b" + re.escape(brand) + r"\b", question, re.I)]
        if len(matches) != 1:
            return []
        tokens = re.findall(r"(?<![A-Z0-9])[A-Z0-9]{4,6}-?[A-Z0-9]{4,6}(?![A-Z0-9])", question.upper())
        sources = []
        for token in dict.fromkeys(tokens):
            if not any(c.isdigit() for c in token):
                continue
            for record in self.search(matches[0], token, limit)["records"]:
                if record.get("reference_only"):
                    content = f"Published OEM cross-reference: {record['original_brand']} original {record['original_printed']} → DENSO {record['part_number']}. " + record["application"]
                    sources.append({"title": f"{record['original_brand']} {record['original_printed']} → DENSO {record['part_number']}", "source": record["source"], "page_number": record["page_number"], "content": content, "section": "part_cross_reference", "raw_excerpt": json.dumps(record["raw_row"]), "chunk_id": record["id"], "source_sha256": record["source_sha256"], "document_id": record["source_sha256"], "pdf_url": record["pdf_url"], "retrieval_method": "indexed original-part replacement reference", "replacement": {"original": record["original_printed"], "original_brand": record["original_brand"], "alternative": record["part_number"], "brand": "DENSO"}})
                    if len(sources) >= limit:
                        return sources
                    continue
                evidence = self.fitments.evidence(record)
                evidence["content"] = evidence["content"].replace("OEM cell group (not individual cross-reference pairs): " + ", ".join(record["oem_group"]) + ". ", "")
                evidence["content"] = (f"Published single-cell reference: {record['original_brand']} original {record['original_part']} → {record['brand']} {record['part_number']}, only for the following printed application. " + evidence["content"])
                evidence["fitment"]["original_part"] = record["original_part"]
                evidence["retrieval_method"] = "indexed original-part replacement reference"
                sources.append(evidence)
                if len(sources) >= limit:
                    return sources
        return sources
