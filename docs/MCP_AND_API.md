# Agent access: MCP and REST

## Vehicle/year/engine lookup

`GET /api/fitments?make=Toyota&model=Corolla&year=2012&engine=1.8&axle=front&component=shock_absorber`

Category supports `suspension` (default) or `ignition`. Additional filters: `engine` (size, cc or engine code), `component`, `market`. Explicitly different known markets are excluded; an unspecified source market remains unknown, not confirmed.

MCP `search_catalogue` examples: `Toyota Corolla 2012 1.8 front shock absorbers` and `Toyota Corolla 2005 1ZZ-FE Taiwan spark plugs`. These use direct vehicle links before broad retrieval. Chat additionally asks for missing year/engine details and combines short replies with the saved question.

## Original-part replacement references

`GET /api/replacements?brand=Toyota&part=48609-12500` returns directed, qualified references from reviewed single-number KYB cells. Response includes `status`, `records`, `total`, `limit` and `notice`; records retain original and alternative numbers, application/production conditions, source hash/page and local PDF URL. Limit is 1–48. Results may be truncated to limit; total counts application rows, not unique products.

The existing MCP `search_catalogue` tool accepts `{"query":"Replacement for Toyota 48609-12500?","limit":6}` and returns indexed reference evidence without an LLM call. No new MCP tool or write permissions were added. Missing links mean not documented, not incompatible.

Added 2026-11-18. Both interfaces use CatalogueTools, CatalogueService, and the same local PDF repository. The calling agent must support MCP or be able to call HTTP APIs; exposing a server does not automatically connect every agent.

## What is MCP here?

The web app is the human interface. MCP gives a compatible agent discoverable tools with typed arguments and structured results. REST exposes equivalent operations to ordinary HTTP clients. The MCP server uses the official Python SDK, pinned to mcp==2.3.0. See the [official SDK documentation](https://py.sdk.modelcontextprotocol.io/).

The four MCP tools are:

| Tool | Arguments | Result |
| --- | --- | --- |
| catalogue_info | none | Source fingerprint, counts, PDF URL, interpretation limits |
| search_catalogue | query, limit=8 | Ranked records/passages with page-specific evidence |
| lookup_part | part, optional brand, limit=8 | Exact lookup, ambiguity, bounded records and total counts |
| compare_parts | original, candidate, optional brand | Dimension matrix, direct reference evidence, conservative verdict |

Search and lookup limits must be 1–12. Lookup limits each section separately and reports the full count. Original identifiers can be external; the comparison candidate must be an explicit DENSO number. No numeric normalization removes leading zeros.

Resources: catalogue://metadata and catalogue://workflow. Tools are annotated read-only and return machine-readable structured content plus model-readable text. Catalogue loading may create ignored index caches; agent calls do not create chats, edit source documents, invoke Groq, or expose credentials. There are no arbitrary-file or chat-history MCP tools.

## HTTP: run with the main app

From the project root, launch START_PROJECT.cmd. Default MCP endpoint:

http://127.0.0.1:3201/mcp

Choose Streamable HTTP in your MCP client. This is a protocol endpoint, not a normal webpage. The Node proxy forwards MCP headers and responses to the mounted Python SDK app. JSON responses and stateless HTTP are enabled. The host app explicitly runs the MCP session manager during its lifespan.

Python client example, with this project's environment and the app running:

```python
import asyncio
from mcp import Client


async def main():
    async with Client("http://127.0.0.1:3201/mcp") as client:
        tools = await client.list_tools()
        print([tool.name for tool in tools.tools])
        result = await client.call_tool("compare_parts", {
            "original": "DCF009P", "candidate": "DCF031P"
        })
        if result.is_error:
            print(result.content)
        else:
            print(result.structured_content)


asyncio.run(main())
```

MCP v1 clients may expose fields using names such as structuredContent; use your client library's documented spelling. Protocol errors and tool-level errors differ: always inspect the tool error flag before using results.

## Stdio: an agent starts its own server

From backend:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m app.mcp_server
```

This waits for MCP messages on stdin. A silent terminal is expected. Normally the agent starts this process itself; you do not manually type catalogue questions into it.

Generate client configuration with exact local paths:

```powershell
.\.venv\Scripts\python.exe scripts/print_mcp_config.py
```

Copy the printed mcpServers configuration into your compatible client's configuration. It uses absolute Python/script paths and no API key; the entry script works independently of the client's working directory. Different clients may use a different configuration wrapper; follow their own schema. The helper only prints configuration and does not modify another app.

For a standalone local HTTP server without the frontend:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m app.mcp_server --transport streamable-http --port 8002
```

Connect to http://127.0.0.1:8002/mcp. Relative PDF links refer to the main web app's /api/catalogue/pdf route, so use that app to view the original pages. Stdio also returns relative PDF links; source filename, page, and fingerprint remain usable without the viewer.

## REST: ordinary API clients

Default base URL: http://127.0.0.1:3201. The OpenAPI schema is available at /openapi.json.

| Endpoint | Body / purpose |
| --- | --- |
| GET /api/catalogue/info | Current catalogue metadata |
| POST /api/catalogue/search | {"query":"DCF002K dimensions","limit":2} |
| POST /api/catalogue/lookup | {"part":"C30001","brand":"1A FIRST AUTOMOTIVE","limit":2} |
| POST /api/catalogue/compare | {"original":"DCF009P","candidate":"DCF031P"} |
| GET /api/conversations/{id}/export?format=markdown | Download a local investigation report |
| GET /api/conversations/{id}/export?format=json | Download complete saved response/source snapshots |

The existing POST /api/chat is also available for Groq-backed answers or saved evidence-only conversations. Unlike read-only catalogue tools, it persists conversation records and can call Groq when mode is answer. An agent can instead use search/lookup/compare with its own LLM.

PowerShell example:

```powershell
$comparisonBody = @{ original = 'DCF009P'; candidate = 'DCF031P' } | ConvertTo-Json
Invoke-RestMethod -Uri 'http://127.0.0.1:3201/api/catalogue/compare' -Method Post -ContentType 'application/json' -Body $comparisonBody
```

## Interpretation and deployment scope

Field match means the documented dimension agrees. Conflict means known dimensions differ. Missing or conflicting source values stay unknown. An overall documented_reference is a direct published relationship, never exact-vehicle approval. Preserve brands and application qualifiers in downstream answers. Review the PDF table before making a parts decision.

This is a local integration foundation, not a hosted commercial service. HTTP binds to loopback, SDK Host/Origin protection remains enabled, and the Node proxy rejects foreign browser origins. There is no account authentication, tenant isolation, public TLS domain, or remote authorization flow. Public deployment needs those features plus source licensing and measured quality evaluation. Do not expose the current local server directly to the internet.

## Verified scope

The official MCP client discovered the tools, invoked them, and read a resource against the real catalogue over HTTP through Node and through a separate stdio subprocess. Unit checks cover invalid input, structured output, read-only annotations, and foreign-origin rejection. No particular third-party agent UI was configured or tested. See VERIFICATION.md and the appended README change record.

## Appended document-library update — 2026-11-18

search_catalogue now combines exact/keyword DENSO records with Chroma search over ready reference documents. This includes user uploads. The metadata resource exposes library readiness/counts; it does not expose local filesystem paths. The four existing tools and both transports remain available. Generic uploaded document retrieval also works when the base DENSO file is absent; structured lookup/compare still require the DENSO-specific records.

New document management routes are ordinary REST endpoints: GET /api/documents, POST /api/documents/upload (multipart file, returns 202), POST /api/documents/{id}/retry, and GET /api/documents/{sha256}/pdf. The MCP tools remain read-only and do not initiate uploads or processing jobs. Source URLs for uploaded PDFs are relative to the same running web app.

Real integration checks uploaded a PDF through Node, waited for its background Chroma index, and retrieved it through an actual MCP client. The fictional verification fixture is excluded from ordinary answers afterward. Upload size/type, incremental history, and OCR limits are documented in DOCUMENT_LIBRARY.md.
