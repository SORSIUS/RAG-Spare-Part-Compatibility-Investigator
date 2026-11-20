"""Indexed vehicle -> application -> part -> original PDF evidence links."""
import json
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

NOTICE = "Catalogue-listed candidates, not installation approval. Check the exact chassis, production month, engine, steering side and market. Coverage is limited to imported catalogue tables; missing parts are not proof of incompatibility."


class FitmentRepository:
    def __init__(self, runtime):
        self.path = Path(runtime) / "fitments.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""CREATE TABLE IF NOT EXISTS fitment_sources (sha TEXT PRIMARY KEY, name TEXT NOT NULL, schema TEXT NOT NULL, url TEXT NOT NULL, pages INTEGER NOT NULL);
              CREATE TABLE IF NOT EXISTS fitments (id TEXT PRIMARY KEY, sha TEXT NOT NULL, make TEXT NOT NULL, model TEXT NOT NULL, category TEXT NOT NULL, axle TEXT NOT NULL, component TEXT NOT NULL, part TEXT NOT NULL, start_year INTEGER NOT NULL, end_year INTEGER, body TEXT NOT NULL);
              CREATE INDEX IF NOT EXISTS fitment_vehicle ON fitments(make,model,category,start_year,end_year);
              CREATE INDEX IF NOT EXISTS fitment_part ON fitments(part);
              CREATE INDEX IF NOT EXISTS fitment_source ON fitments(sha);""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        try:
            with db:
                yield db
        finally:
            db.close()

    def imported(self, sha, schema):
        with self.connect() as db:
            return db.execute("SELECT 1 FROM fitment_sources WHERE sha=? AND schema=?", (sha, schema)).fetchone() is not None

    def replace_source(self, sha, name, schema, url, pages, records):
        with self.connect() as db:
            db.execute("DELETE FROM fitments WHERE sha=?", (sha,))
            db.executemany("INSERT INTO fitments VALUES(?,?,?,?,?,?,?,?,?,?,?)", [(r["id"], sha, r["make"], r["model"], r["category"], r["axle"], r["component"], r["part_number"], r["start_year"], r["end_year"], json.dumps(r, ensure_ascii=False)) for r in records])
            db.execute("INSERT OR REPLACE INTO fitment_sources VALUES(?,?,?,?,?)", (sha, name, schema, url, pages))
            # A changed source must invalidate derived links even if the parser
            # schema stayed the same. The next lookup rebuilds this source only.
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='replacement_builds'").fetchone():
                db.execute("DELETE FROM replacement_builds WHERE sha=?", (sha,))

    def options(self):
        with self.connect() as db:
            vehicles = [{"make": m, "model": v, "count": n} for m, v, n in db.execute("SELECT make,model,count(*) FROM fitments GROUP BY make,model ORDER BY make,model")]
            sources = [{"sha256": s, "name": n, "url": u, "application_pages": p} for s, n, u, p in db.execute("SELECT sha,name,url,pages FROM fitment_sources")]
        return {"vehicles": vehicles, "record_count": sum(v["count"] for v in vehicles), "sources": sources, "notice": NOTICE}

    def search(self, make="", model="", year=None, category="suspension", axle="", chassis="", part="", limit=24, offset=0, engine="", component="", market=""):
        started = time.perf_counter()
        clauses, args = (["category=?"], [category]) if category and category != "all" else (["1=1"], [])
        for column, value in (("make", make), ("model", model), ("axle", axle), ("part", part), ("component", component)):
            if value:
                clauses.append(column + "=? COLLATE NOCASE")
                args.append(value)
        if year:
            clauses.append("start_year<=? AND (end_year IS NULL OR end_year>=?)")
            args.extend([year, year])
        with self.connect() as db:
            from app.services.vehicle_lookup import matches_engine
            db.create_function("matches_engine", 2, lambda body, requested: matches_engine(json.loads(body), requested))
            if engine:
                clauses.append("matches_engine(body,?)")
                args.append(engine)
            if market:
                clauses.append("(json_extract(body,'$.market') IS NULL OR json_extract(body,'$.market')=? COLLATE NOCASE)")
                args.append(market)
            # Chassis filtering uses exact token boundaries, never substring LIKE.
            db.create_function("has_chassis", 2, lambda body, term: bool(re.search(r"(?<![A-Z0-9])" + re.escape(term.upper()) + r"(?![A-Z0-9])", json.loads(body)["application"].upper())))
            if chassis:
                clauses.append("has_chassis(body,?)")
                args.append(chassis)
            where = " AND ".join(clauses)
            total = db.execute("SELECT count(*) FROM fitments WHERE " + where, args).fetchone()[0]
            ordering = "row_number() OVER(PARTITION BY category ORDER BY make,model,start_year,part,axle,id),category,part" if not category or category == "all" else "make,model,start_year,part,axle,id"
            rows = db.execute("SELECT body FROM fitments WHERE " + where + " ORDER BY " + ordering + " LIMIT ? OFFSET ?", args + [limit, offset]).fetchall()
        records = []
        for (body,) in rows:
            r = json.loads(body)
            r["pdf_url"] = f"/api/documents/{r['source_sha256']}/pdf#page={r['page_number']}"
            r["status"] = "catalogue_listed"
            records.append(r)
        return {"records": records, "total": total, "limit": limit, "offset": offset, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2), "retrieval": "indexed vehicle-part lookup", "notice": NOTICE}

    @staticmethod
    def evidence(record):
        content = (f"Catalogue application: {record['make']} {record['vehicle_label']}; period {record['period']}; "
                   f"application {record['application']}; {record['axle']} {record['component'].replace('_', ' ')}; {record.get('brand', 'KYB')} {record['part_number']}. "
                   + ("OEM cell group (not individual cross-reference pairs): " + ", ".join(record['oem_group']) + ". " if record["oem_group"] else "") + NOTICE)
        return {"title": f"{record['make']} {record['model']} · {record.get('brand', 'KYB')} {record['part_number']}", "source": record["source"], "page_number": record["page_number"], "content": content, "fitment": {key: record[key] for key in ("make", "model", "vehicle_label", "part_number", "application", "period", "component", "axle", "brand") if key in record},
                "raw_excerpt": json.dumps(record["raw_row"], ensure_ascii=False, indent=2), "section": "vehicle_part_link", "chunk_id": record["id"], "source_sha256": record["source_sha256"], "document_id": record["source_sha256"], "pdf_url": record["pdf_url"], "retrieval_method": "indexed vehicle-part link"}

    def question_sources(self, question, limit):
        context = self.owner_context(question)
        if context:
            part = re.search(r"\b(?:KYB|DENSO)\s+([A-Z0-9-]*\d[A-Z0-9-]*)\b", question, re.I)
            result = self.search(context["make"], context["model"], context["year"], context["category"],
                                 context["axle"], context["chassis"], part[1] if part else "",
                                 limit, engine=context["engine"], component=context["component"], market=context["market"])
            market_unconfirmed = False
            if not result["records"] and context["market"]:
                # Broaden only the market; retain vehicle/year/engine/chassis filters.
                result = self.search(context["make"], context["model"], context["year"], context["category"],
                                     context["axle"], context["chassis"], part[1] if part else "",
                                     limit, engine=context["engine"], component=context["component"], market="")
                market_unconfirmed = True
            application = re.search(r"Application: (.+?)\. Preserve all qualifications\.", question, re.I)
            if application:
                result["records"] = [r for r in result["records"] if r["application"].casefold() == application[1].casefold()]
            return [{**self.evidence(record), "requested_market": context["market"], "market_unconfirmed": market_unconfirmed or bool(context["market"] and record.get("market", "").casefold() != context["market"].casefold())} for record in result["records"]]
        return []

    def owner_context(self, question):
        from app.services.vehicle_lookup import owner_query
        return owner_query(question, self.options()["vehicles"])


