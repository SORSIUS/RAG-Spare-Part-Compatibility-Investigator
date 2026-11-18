import json
import asyncio
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

from mcp import Client, StdioServerParameters


def fetch(url, payload=None):
    request = urllib.request.Request(url, data=None if payload is None else json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = response.read()
            return response.status, json.loads(body) if "application/json" in response.headers.get("Content-Type", "") else body
    except urllib.error.HTTPError as error:
        body = error.read()
        return error.code, json.loads(body) if "application/json" in error.headers.get("Content-Type", "") else body


async def verify_mcp(url, backend):
    transports = [url + "/mcp", StdioServerParameters(command=sys.executable, args=["-X", "utf8", str(backend / "mcp_entry.py")], cwd=backend.parent, env={**os.environ, "GROQ_API_KEY": ""})]
    for transport in transports:
        async with Client(transport, read_timeout_seconds=30) as client:
            listed = await client.list_tools()
            assert {tool.name for tool in listed.tools} == {"catalogue_info", "search_catalogue", "lookup_part", "compare_parts"}
            result = await client.call_tool("catalogue_info", {})
            assert not result.is_error and result.structured_content["pages"] == 141
            result = await client.call_tool("search_catalogue", {"query": "DCF002K dimensions", "limit": 2})
            assert not result.is_error and result.structured_content["sources"][0]["page_number"] == 97
            result = await client.call_tool("compare_parts", {"original": "DCF009P", "candidate": "DCF031P"})
            assert not result.is_error and result.structured_content["status"] == "conflict"
            result = await client.read_resource("catalogue://metadata")
            assert json.loads(result.contents[0].text)["pages"] == 141


def main():
    project = Path(__file__).resolve().parents[2]
    temporary_parent = project / "backend/data/runtime"
    temporary_parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="app-http-check-", dir=temporary_parent)).resolve()
    if not temporary.is_relative_to(temporary_parent.resolve()):
        raise ValueError("Test workspace escaped the runtime directory.")
    process = None
    try:
        for relative in ["frontend", "backend/app"]:
            shutil.copytree(project / relative, temporary / relative, ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
        shutil.copy2(project / "backend/run.py", temporary / "backend/run.py")
        shutil.copy2(project / "backend/mcp_entry.py", temporary / "backend/mcp_entry.py")
        pdf_relative = "backend/data/sources/automotive/denso_cabin_air_filters_2026.pdf"
        (temporary / pdf_relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(project / pdf_relative, temporary / pdf_relative)
        for filename in ["denso_catalogue.json", "denso_page_chunks.json"]:
            source = temporary_parent / filename
            if source.exists():
                (temporary / "backend/data/runtime").mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, temporary / "backend/data/runtime" / filename)
        model_cache = temporary_parent / "models"
        if model_cache.exists():
            destination = str(temporary / "backend/data/runtime/models")
            shutil.copytree(model_cache, "\\\\?\\" + destination if os.name == "nt" else destination)
        process = subprocess.Popen(["node", "server.mjs"], cwd=temporary / "frontend", env={**os.environ, "PORT": "0", "PYTHON_BIN": sys.executable, "GROQ_API_KEY": ""}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        lines = queue.Queue()
        threading.Thread(target=lambda: [lines.put(line) for line in process.stdout], daemon=True).start()
        while True:
            line = lines.get(timeout=75).strip()
            if line.startswith("PROJECT_READY="):
                url = line.split("=", 1)[1]
                break
        assert fetch(url + "/")[0] == 200
        for asset in ["styles.css", "comparison.css", "src/app.js", "src/services/api.js", "src/components/sources.js", "src/components/comparison.js"]:
            assert fetch(url + "/" + asset)[0] == 200
        status, configuration = fetch(url + "/api/status")
        assert status == 200 and configuration["catalogue_ready"] and not configuration["llm_configured"]
        status, evidence = fetch(url + "/api/chat", {"question": "What are the dimensions of DCF002K?", "mode": "evidence"})
        assert status == 200 and evidence["status"] == "evidence_only"
        assert evidence["sources"][0]["page_number"] == 97
        assert "282 mm" in evidence["sources"][0]["content"]
        status, history = fetch(url + "/api/conversations/" + evidence["conversation_id"])
        assert status == 200 and len(history["messages"]) == 1
        status, follow_up = fetch(url + "/api/chat", {"question": "What about its width?", "conversation_id": evidence["conversation_id"], "mode": "evidence"})
        assert status == 200 and follow_up["sources"]
        status, missing_key = fetch(url + "/api/chat", {"question": "What are the dimensions of DCF002K?"})
        assert status == 503 and missing_key["error"]["code"] == "configuration_missing"
        status, pdf = fetch(url + evidence["sources"][0]["pdf_url"].split("#")[0])
        assert status == 200 and pdf.startswith(b"%PDF")
        assert fetch(url + "/api/catalogue/pdf?version=" + "0" * 64)[0] == 409
        assert fetch(url + "/api/chat", {"question": " "})[0] == 422
        assert fetch(url + "/.env")[0] == 404
        status, comparison = fetch(url + "/api/catalogue/compare", {"original": "DCF009P", "candidate": "DCF031P"})
        assert status == 200 and comparison["status"] == "conflict"
        assert all(check["evidence"] for check in comparison["dimension_checks"])
        status, reference = fetch(url + "/api/catalogue/compare", {"original": "C30001", "candidate": "DCF357P", "brand": "1A FIRST AUTOMOTIVE"})
        assert status == 200 and reference["status"] == "documented_reference"
        assert fetch(url + "/api/conversations/" + evidence["conversation_id"] + "/export")[0] == 200
        status, exported = fetch(url + "/api/conversations/" + evidence["conversation_id"] + "/export?format=json")
        assert status == 200 and len(exported["messages"]) == 2
        assert "/api/catalogue/compare" in fetch(url + "/openapi.json")[1]["paths"]
        asyncio.run(verify_mcp(url, temporary / "backend"))
        watched_file = temporary / "backend/app/ask.py"
        watched_file.write_text(watched_file.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        while "Backend reloaded." not in lines.get(timeout=30):
            pass
        assert fetch(url + "/api/status")[1]["catalogue_ready"]
        assert fetch(url + "/api/conversations/" + evidence["conversation_id"])[0] == 200
        result = {"main_node_python_http": "passed", "static_assets": "passed", "real_catalogue_evidence": "passed", "chat_history_and_follow_up": "passed", "pdf_citation_route": "passed", "missing_key_handling": "passed", "python_auto_reload": "passed", "comparison_matrix_api": "passed", "conversation_exports": "passed", "mcp_http_and_stdio": "passed", "live_groq": "not run: isolated checks explicitly disable Groq", "browser_visual_qa": "not run by this script; see docs/VERIFICATION.md"}
        (temporary_parent / "main_app_verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
    finally:
        if process is not None:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
            else:
                process.terminate()
            process.wait(timeout=10)
        if temporary.is_relative_to(temporary_parent.resolve()) and temporary.name.startswith("app-http-check-"):
            shutil.rmtree("\\\\?\\" + str(temporary) if os.name == "nt" else temporary)


if __name__ == "__main__":
    main()
