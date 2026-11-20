"""Live owner conversation and model/year/engine retrieval, without LLM calls."""
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
        async def ask(question, conversation_id=None):
            payload = {"question": question}
            if conversation_id:
                payload["conversation_id"] = conversation_id
            response = await http.post("/api/chat", json=payload)
            response.raise_for_status()
            return response.json()
        first = await ask("Which suspension fits my Corolla?")
        assert first["answer_method"] == "vehicle_clarification" and first["model"] is None
        second = await ask("2012", first["conversation_id"])
        assert second["answer_method"] == "vehicle_clarification"
        result = await ask("1.8 front", first["conversation_id"])
        assert result["answer_method"] == "vehicle_catalogue" and result["claims"] and result["model"] is None
        assert all(s["fitment"]["axle"] == "front" for s in result["sources"])
        saved = (await http.get("/api/conversations/" + first["conversation_id"])).json()
        assert len(saved["messages"]) == 3
        spark = await ask("Which spark plugs for Toyota Corolla 2005 1ZZ-FE Taiwan?")
        assert spark["answer_method"] == "vehicle_catalogue" and spark["model"] is None
        assert any("DENSO K16R-U11" in s["content"] and "Taiwan" in s["content"] for s in spark["sources"])
        pdf = await http.get(spark["sources"][0]["pdf_url"].split("#")[0])
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
        response = await http.get("/api/fitments", params={"make": "Toyota", "model": "Corolla", "year": 2005, "category": "ignition", "engine": "1ZZFE", "market": "Pakistan"})
        assert response.status_code == 200 and response.json()["total"] == 0
        response = await http.get("/api/fitments", params={"make": "Toyota", "model": "Corolla", "year": 2012, "engine": "1.8", "component": "shock_absorber", "axle": "front"})
        assert response.status_code == 200 and response.json()["total"] > 0
    async with Client(base + "/mcp", read_timeout_seconds=30) as client:
        for query in ["Toyota Corolla 2012 1.8 front shock absorbers", "Toyota Corolla 2005 1ZZ-FE Taiwan spark plugs"]:
            result = await client.call_tool("search_catalogue", {"query": query, "limit": 6})
            assert not result.is_error
            assert result.structured_content["sources"]
            assert all(s["section"] == "vehicle_part_link" for s in result.structured_content["sources"])
    print(json.dumps({"owner_followups": "passed", "history": "passed", "engine_and_component_filters": "passed",
                      "spark_application_and_pdf": "passed", "market_exclusion": "passed", "mcp_vehicle_search": "passed",
                      "llm_calls": 0, "browser_visual_check": "not_run"}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
