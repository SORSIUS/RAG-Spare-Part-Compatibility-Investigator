import argparse
import hashlib
import json
import re
import sqlite3
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader


def fetch(base, path, body=None):
    payload = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(base + path, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=100) as response:
            data = response.read()
            return response.status, json.loads(data) if "application/json" in response.headers.get("Content-Type", "") else data
    except urllib.error.HTTPError as error:
        data = error.read()
        return error.code, json.loads(data) if "application/json" in error.headers.get("Content-Type", "") else data.decode("utf-8", errors="replace")


def normalize(value):
    return " ".join(value.casefold().split())


def main():
    parser = argparse.ArgumentParser(description="Explicit live Groq verification; sends up to six questions to the configured provider.")
    parser.add_argument("--url", default="http://127.0.0.1:3201")
    parser.add_argument("--delay", type=float, default=0, help="Seconds between questions to respect provider quotas (0–60).")
    arguments = parser.parse_args()
    if not re.fullmatch(r"http://127\.0\.0\.1:\d+", arguments.url):
        parser.error("Use the loopback PROJECT_READY URL.")
    if not 0 <= arguments.delay <= 60:
        parser.error("Use a delay of 0–60 seconds.")
    backend = Path(__file__).resolve().parents[1]
    runtime = backend / "data/runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    pdf_path = backend / "data/sources/automotive/denso_cabin_air_filters_2026.pdf"
    reader = PdfReader(pdf_path)
    fingerprint = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    status, setup = fetch(arguments.url, "/api/status")
    if status != 200 or not setup["llm_configured"] or not setup["catalogue_ready"]:
        parser.exit(1, "The app must have a configured local key and a ready catalogue.\n")
    cases = [
        ("dimensions", "What are the dimensions of DCF002K?", ["282", "206", "30"], True),
        ("follow_up_width", "What about its width?", ["206"], True),
        ("follow_up_height", "And its height?", ["30"], True),
        ("cross_reference", "Does the catalogue cross-reference C30001 to DCF357P? Identify the published brand.", ["DCF357P", "1A FIRST AUTOMOTIVE"], False),
        ("comparison", "Compare the dimensions of DCF009P and DCF031P. Explain any conflicts.", ["DCF009P", "DCF031P"], False),
        ("applications", "Which cabin filters are listed for Toyota Corolla? Keep model generations, dates, and qualifiers separate.", ["COROLLA"], False),
        ("unknown_part", "What are the dimensions of DCF999P?", [], False),
        ("unrelated", "Give me a quantum banana recipe.", [], False),
    ]
    conversation_id = None
    results = []
    for name, question, expected, follow in cases:
        if results and arguments.delay:
            time.sleep(arguments.delay)
        request = {"question": question}
        if follow and conversation_id:
            request["conversation_id"] = conversation_id
        started = time.monotonic()
        code, response = fetch(arguments.url, "/api/chat", request)
        entry = {"case": name, "question": question, "http_status": code, "elapsed_seconds": round(time.monotonic() - started, 2), "response": response}
        if code == 200:
            if name == "dimensions":
                conversation_id = response["conversation_id"]
            sources = {source["id"]: source for source in response["sources"]}
            text = " ".join(claim["text"] for claim in response["claims"])
            checked = []
            for claim in response["claims"]:
                for citation in claim["citations"]:
                    source = sources[citation["source_id"]]
                    page = source["page_number"]
                    pdf_text = reader.pages[page - 1].extract_text(extraction_mode="layout")
                    checked.append({"source_id": source["id"], "page": page, "quote_in_record": normalize(citation["quote"]) in normalize(source["content"]), "page_in_range": 1 <= page <= len(reader.pages), "page_has_text": bool(pdf_text.strip()), "fingerprint_in_link": fingerprint in source["pdf_url"]})
            insufficient = name in {"unknown_part", "unrelated"}
            entry["checks"] = {"expected_status": response["status"] == ("insufficient_evidence" if insufficient else "answered"), "expected_facts": all(value.casefold() in text.casefold() for value in expected), "cited_claims": all(claim["citations"] for claim in response["claims"]), "citation_records": checked, "no_model_for_missing_evidence": not insufficient or response["model"] is None}
            entry["passed"] = all(value for key, value in entry["checks"].items() if key != "citation_records") and all(all(value for key, value in item.items() if key not in {"source_id", "page"}) for item in checked)
        else:
            entry["passed"] = False
        results.append(entry)
        print(json.dumps({"case": name, "http": code, "status": response.get("status") if isinstance(response, dict) else None, "passed": entry["passed"], "elapsed_seconds": entry["elapsed_seconds"]}), flush=True)
        if code in {429, 503, 504}:
            break
    feature_checks = {}
    code, comparison = fetch(arguments.url, "/api/catalogue/compare", {"original": "DCF009P", "candidate": "DCF031P"})
    feature_checks["dimension_conflict"] = code == 200 and comparison["status"] == "conflict"
    code, reference = fetch(arguments.url, "/api/catalogue/compare", {"original": "C30001", "candidate": "DCF357P", "brand": "1A FIRST AUTOMOTIVE"})
    feature_checks["documented_reference"] = code == 200 and reference["status"] == "documented_reference" and reference["vehicle_fitment"] == "unknown"
    code, search = fetch(arguments.url, "/api/catalogue/search", {"query": "DCF002K dimensions", "limit": 2})
    feature_checks["read_only_search"] = code == 200 and search["sources"][0]["page_number"] == 97
    code, pdf = fetch(arguments.url, f"/api/catalogue/pdf?version={fingerprint}")
    feature_checks["actual_pdf_route"] = code == 200 and pdf.startswith(b"%PDF") and hashlib.sha256(pdf).hexdigest() == fingerprint
    if conversation_id:
        code, history = fetch(arguments.url, "/api/conversations/" + conversation_id)
        feature_checks["saved_follow_ups"] = code == 200 and len(history["messages"]) == 3
        code, exported = fetch(arguments.url, "/api/conversations/" + conversation_id + "/export?format=json")
        feature_checks["json_export"] = code == 200 and exported["messages"] == history["messages"]
        code, markdown = fetch(arguments.url, "/api/conversations/" + conversation_id + "/export")
        feature_checks["markdown_export"] = code == 200 and b"PDF page 97" in markdown
    database = runtime / "conversations.sqlite3"
    with sqlite3.connect(database) as connection:
        feature_checks["sqlite_integrity"] = connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        feature_checks["sqlite_foreign_keys"] = not connection.execute("PRAGMA foreign_key_check").fetchall()
        if conversation_id:
            feature_checks["sqlite_saved_messages"] = connection.execute("SELECT COUNT(*) FROM messages WHERE conversation_id=?", (conversation_id,)).fetchone()[0] == 3
    report = {"tested_at": datetime.now(timezone.utc).isoformat(), "url": arguments.url, "model": setup["model"], "source_sha256": fingerprint, "cases": results, "features": feature_checks, "all_passed": len(results) == len(cases) and all(entry["passed"] for entry in results) and all(feature_checks.values()), "limitations": "Automated quote membership and page checks do not establish semantic entailment. Review the saved answer text against the actual PDF. No browser visual pass is implied."}
    path = runtime / "live_answer_verification.json"
    if path.exists():
        previous = runtime / ("live_answer_verification-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
        previous.write_bytes(path.read_bytes())
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"all_passed": report["all_passed"], "features": feature_checks, "report": str(path)}, indent=2))
    if not report["all_passed"]:
        parser.exit(1, "Some live checks did not pass. Review the saved report; no automatic provider retries were made.\n")


if __name__ == "__main__":
    main()
