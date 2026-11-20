import json


def export_conversation(conversation, format):
    if format == "json":
        return json.dumps(conversation, ensure_ascii=False, indent=2), "application/json"
    lines = ["# Catalogue investigation", "", "Conversation: " + conversation["id"], ""]
    for index, message in enumerate(conversation["messages"], 1):
        lines.extend([f"## Question {index}", "", message["question"], "", "Status: " + message["status"], "", "Created: " + message["created_at"], ""])
        for field in ('assistant_text', 'generation_note'):
            if message.get(field):
                lines.extend([message[field], ''])
        for claim in message["claims"]:
            lines.extend([claim["text"] + " " + " ".join("[" + citation["source_id"] + "]" for citation in claim["citations"]), ""])
            for citation in claim["citations"]:
                lines.extend([f"Supporting quote [{citation['source_id']}]: {citation['quote']}", ""])
        if message.get("general_guidance"):
            lines.extend(["### General explanation", "", message["general_guidance"], ""])
        if message["unknowns"]:
            lines.extend(["### Unknowns", "", *["- " + text for text in message["unknowns"]], ""])
        lines.extend(["### Sources for this question", "", "Source IDs are scoped to this question.", ""])
        for source in message["sources"]:
            lines.extend([f"- {source['id']}: {source['source']} | PDF page {source['page_number']}", "", source["content"], "", "Extracted source: " + source["raw_excerpt"], "", "Local PDF link: " + source["pdf_url"], ""])
        lines.extend([message["notice"], ""])
    lines.extend(["Local PDF links require the running app and the same catalogue revision.", ""])
    return "\n".join(lines), "text/markdown"

