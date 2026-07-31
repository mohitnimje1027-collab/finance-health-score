from fpdf import FPDF
from pathlib import Path

def create_sample_statement_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    pdf.cell(200, 10, text="Sample Bank Statement", ln=True, align="C")
    pdf.ln(5)

    headers = ["Date", "Particulars", "Debit", "Credit"]
    rows = [
        ["01/07/2026", "SWIGGY BANGALORE", "450.00", ""],
        ["02/07/2026", "SALARY CREDIT XYZ CORP", "", "45000.00"],
        ["03/07/2026", "NETFLIX SUBSCRIPTION", "499.00", ""],
        ["05/07/2026", "ZOMATO ORDER", "320.00", ""],
    ]

    col_width = 45
    pdf.set_font("Helvetica", "B", 10)
    for h in headers:
        pdf.cell(col_width, 10, h, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", size=10)
    for row in rows:
        for item in row:
            pdf.cell(col_width, 10, item, border=1)
        pdf.ln()

    project_root = Path(__file__).resolve().parent.parent
    output_path = project_root / "data" / "sample_statement.pdf"
    pdf.output(str(output_path))
    print(f"Created test PDF at {output_path}")

if __name__ == "__main__":
    create_sample_statement_pdf()