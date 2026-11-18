from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def create_sample_pdf(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = canvas.Canvas(str(destination), pagesize=A4, invariant=1)
    document.setTitle("Fictional bench fan specification manual")
    records = [
        ("FAN-12", "Original requirements", "12", "80", "2-pin", "30"),
        ("ALT-A", "Candidate with documented matching fields", "12", "80", "2-pin", "32"),
        ("ALT-B", "Candidate with a voltage conflict", "24", "80", "2-pin", "35"),
        ("ALT-C", "Candidate with missing connector evidence", "12", "80", "Not documented", "31"),
    ]
    for page_number, (part, title, voltage, width, connector, airflow) in enumerate(records, start=1):
        document.setFillColor(colors.HexColor("#253858"))
        document.rect(0, 760, A4[0], 82, fill=1, stroke=0)
        document.setFillColor(colors.white)
        document.setFont("Helvetica-Bold", 19)
        document.drawString(48, 794, "Sample specification manual")
        document.setFillColor(colors.black)
        document.setFont("Helvetica-Bold", 15)
        document.drawString(48, 713, title)
        lines = [
            "FICTIONAL TRAINING DATA - NOT FOR REAL EQUIPMENT",
            "Document revision: R1 | Category: bench ventilation fan",
            "",
            f"Part number: {part}",
            f"Supply voltage (V DC): {voltage}",
            f"Frame width (mm): {width}",
            f"Connector: {connector}",
            f"Airflow (CFM): {airflow}",
            "",
            "Compare voltage, width, and connector by exact agreement.",
            "Candidate airflow must meet or exceed the original minimum.",
            "Missing specifications remain unknown. No substitutions are certified.",
            "Physical depth, polarity, current draw, and installation are not covered.",
            "This legacy electronics fixture tests the pipeline, not automotive fitment.",
        ]
        text = document.beginText(48, 672)
        text.setFont("Helvetica", 10)
        text.setLeading(22)
        for line in lines:
            text.textLine(line)
        document.drawText(text)
        document.setFont("Helvetica", 9)
        document.setFillColor(colors.HexColor("#626b7a"))
        document.drawString(48, 45, f"Sample R1 | page {page_number} of {len(records)} | no real manufacturer claims")
        document.showPage()
    document.save()


if __name__ == "__main__":
    output = Path(__file__).resolve().parents[1] / "data/sample/pdf_manuals/sample_parts_manual.pdf"
    create_sample_pdf(output)
    print(output)
