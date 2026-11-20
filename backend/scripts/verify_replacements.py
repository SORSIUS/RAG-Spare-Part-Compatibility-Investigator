"""Read-only live checks for replacement API, PDF evidence and MCP routing."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from mcp import Client


async def main():
    base = "http://127.0.0.1:3201"
    async with httpx.AsyncClient(base_url=base, timeout=30) as http:
        response = await http.get("/api/replacements", params={"brand": "Toyota", "part": "48609-12500"})
        response.raise_for_status()
        data = response.json()
        assert data["status"] == "published_reference" and data["total"] == 5
        corolla = next(r for r in data["records"] if r["model"] == "Corolla")
        assert corolla["part_number"] == "SM7210" and corolla["page_number"] == 96
        pdf = await http.get(corolla["pdf_url"].split("#")[0])
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
        unknown = await http.get("/api/replacements", params={"brand": "Toyota", "part": "UNLISTED"})
        assert unknown.json()["status"] == "not_documented"
        invalid = await http.get("/api/replacements", params={"brand": "Toyota", "part": "4860912500", "limit": 100})
        assert invalid.status_code == 422
        library = (await http.get("/api/documents")).json()
        learning_names = ("A Complete List", "List of 22", "Automobile Engineering", "CATALOGUE-flipbook")
        learning = [r for r in library["documents"] if r["name"].startswith(learning_names)]
        assert len(learning) == 4 and all(r["status"] == "ready" and r["indexed"] > 0 for r in learning)
        # No Groq call: exercise the same indexed retrieval used by agents.
        result = await http.post("/api/catalogue/search", json={"query": "Replacement for Toyota 48609-12500?", "limit": 6})
        result.raise_for_status()
        sources = result.json()["sources"]
        assert sources and all(s["retrieval_method"] == "indexed original-part replacement reference" for s in sources)
        javascript = await http.get("/src/components/parts-finder.js")
        assert javascript.status_code == 200 and "Check alternatives" in javascript.text
        spark = (await http.get("/api/replacements", params={"brand": "Toyota", "part": "90919-01095"})).json()
        assert spark["total"] >= 1 and spark["records"][0]["part_number"] == "W16ETR-S"
        assert spark["records"][0]["reference_only"]
        spark_pdf = await http.get(spark["records"][0]["pdf_url"].split("#")[0])
        assert spark_pdf.status_code == 200 and spark_pdf.content.startswith(b"%PDF")
        new_names = {"denso_spark_plug_japan_2025.pdf", "denso_spark_plug_europe_2025.pdf", "denso_spark_plug_references_2025.pdf"}
        added = [r for r in library["documents"] if r["name"] in new_names]
        assert len(added) == 3 and all(r["status"] == "ready" for r in added)
        assert "model" in unknown.json()["message"] and unknown.json()["next_steps"]
    async with Client(base + "/mcp", read_timeout_seconds=30) as client:
        result = await client.call_tool("search_catalogue", {"query": "Replacement for Toyota 48609-12500?", "limit": 6})
        assert not result.is_error
        sources = result.structured_content["sources"]
        assert sources and any("SM7210" in s["content"] for s in sources)
        result = await client.call_tool("search_catalogue", {"query": "Toyota 90919-01095 replacement?", "limit": 6})
        assert not result.is_error
        assert any(s["section"] == "part_cross_reference" and "W16ETR-S" in s["content"] for s in result.structured_content["sources"])
    print(json.dumps({"http": "passed", "source_pdf": "passed", "unknown_and_limits": "passed",
                      "frontend_asset": "passed", "mcp_replacement_search": "passed",
                      "llm_calls": 0, "browser_visual_check": "not_run"}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
