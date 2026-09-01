#!/usr/bin/env python3
"""Generate knowledge base PDF documents from Glancy Fawcett markdown sources.

Usage:
    python scripts/generate_kb_pdfs.py

Output:
    knowledge/pdf/*.pdf  — one PDF per markdown topic file
    knowledge/pdf/glancy_fawcett_knowledge_base_complete.pdf — combined reference
"""

from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
MD_DIR = ROOT / "knowledge" / "glancy_faq"
PDF_DIR = ROOT / "knowledge" / "pdf"

# Brand colours (RGB)
NAVY = (26, 35, 50)
GOLD = (180, 145, 85)
BODY = (45, 45, 45)
MUTED = (100, 100, 100)


class KnowledgeBasePDF(FPDF):
  """PDF document styled for Glancy Fawcett CRM knowledge base."""

  def __init__(self, title: str = "Glancy Fawcett Knowledge Base") -> None:
    super().__init__()
    self.doc_title = title
    self.set_auto_page_break(auto=True, margin=20)

  def header(self) -> None:
    self.set_font("Helvetica", "B", 9)
    self.set_text_color(*MUTED)
    self.cell(0, 8, self._clean("Glancy Fawcett - CRM Enquiry Knowledge Base"), align="L")
    self.cell(0, 8, self._clean(self.doc_title), align="R", new_x="LMARGIN", new_y="NEXT")
    self.set_draw_color(*GOLD)
    self.line(10, self.get_y(), 200, self.get_y())
    self.ln(4)

  def footer(self) -> None:
    self.set_y(-15)
    self.set_font("Helvetica", "I", 8)
    self.set_text_color(*MUTED)
    self.cell(0, 10, f"Page {self.page_no()}/{{nb}} | Source: glancyfawcett.com", align="C")

  def cover_page(self, title: str, subtitle: str, meta: list[str]) -> None:
    self.add_page()
    self.set_font("Helvetica", "B", 28)
    self.set_text_color(*NAVY)
    self.ln(40)
    self.multi_cell(0, 14, self._clean(title), align="C")
    self.ln(6)
    self.set_font("Helvetica", "", 14)
    self.set_text_color(*GOLD)
    self.multi_cell(0, 8, self._clean(subtitle), align="C")
    self.ln(20)
    self.set_font("Helvetica", "", 10)
    self.set_text_color(*MUTED)
    for line in meta:
      self.cell(0, 7, self._clean(line), align="C", new_x="LMARGIN", new_y="NEXT")
    self.ln(10)
    self.set_draw_color(*GOLD)
    self.line(60, self.get_y(), 150, self.get_y())

  def add_h1(self, text: str) -> None:
    self.ln(4)
    self.set_font("Helvetica", "B", 16)
    self.set_text_color(*NAVY)
    self.multi_cell(0, 9, self._clean(text))
    self.ln(2)

  def add_h2(self, text: str) -> None:
    self.ln(3)
    self.set_font("Helvetica", "B", 13)
    self.set_text_color(*NAVY)
    self.multi_cell(0, 8, self._clean(text))
    self.ln(1)

  def add_h3(self, text: str) -> None:
    self.ln(2)
    self.set_font("Helvetica", "B", 11)
    self.set_text_color(*GOLD)
    self.multi_cell(0, 7, self._clean(text))
    self.ln(1)

  def add_body(self, text: str) -> None:
    self.set_font("Helvetica", "", 10)
    self.set_text_color(*BODY)
    self.multi_cell(0, 6, self._clean(text))
    self.ln(1)

  def add_bullet(self, text: str) -> None:
    self.set_font("Helvetica", "", 10)
    self.set_text_color(*BODY)
    x = self.get_x()
    self.cell(6, 6, "-")
    self.multi_cell(0, 6, self._clean(text))
    self.set_x(x)

  def add_meta_line(self, text: str) -> None:
    self.set_font("Helvetica", "I", 9)
    self.set_text_color(*MUTED)
    self.multi_cell(0, 5, self._clean(text))
    self.ln(1)

  def add_hr(self) -> None:
    self.ln(2)
    self.set_draw_color(220, 220, 220)
    self.line(10, self.get_y(), 200, self.get_y())
    self.ln(4)

  @staticmethod
  def _clean(text: str) -> str:
    text = text.replace("\u2014", " - ").replace("\u2013", " - ")
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    # fpdf core fonts are latin-1; replace unsupported chars
    return text.encode("latin-1", errors="replace").decode("latin-1")


def parse_markdown(md_text: str) -> list[tuple[str, str]]:
  """Parse markdown into (type, content) blocks."""
  blocks: list[tuple[str, str]] = []
  for line in md_text.splitlines():
    stripped = line.strip()
    if not stripped:
      continue
    if stripped == "---":
      blocks.append(("hr", ""))
    elif stripped.startswith("# "):
      blocks.append(("h1", stripped[2:]))
    elif stripped.startswith("## "):
      blocks.append(("h2", stripped[3:]))
    elif stripped.startswith("### "):
      blocks.append(("h3", stripped[4:]))
    elif stripped.startswith("|") and "---" not in stripped:
      blocks.append(("body", stripped))
    elif stripped.startswith("- "):
      blocks.append(("bullet", stripped[2:]))
    elif stripped.startswith("**") and stripped.endswith("**"):
      blocks.append(("h3", stripped.strip("*")))
    else:
      blocks.append(("body", stripped))
  return blocks


def render_blocks(pdf: KnowledgeBasePDF, blocks: list[tuple[str, str]]) -> None:
  for kind, content in blocks:
    if kind == "h1":
      pdf.add_h1(content)
    elif kind == "h2":
      pdf.add_h2(content)
    elif kind == "h3":
      pdf.add_h3(content)
    elif kind == "bullet":
      pdf.add_bullet(content)
    elif kind == "hr":
      pdf.add_hr()
    elif content.startswith("**Source:**") or content.startswith("**Document") or content.startswith("**Tags:**"):
      pdf.add_meta_line(content.replace("**", ""))
    else:
      pdf.add_body(content)


def markdown_to_pdf(md_path: Path, pdf_path: Path, short_title: str) -> None:
  md_text = md_path.read_text(encoding="utf-8")
  blocks = parse_markdown(md_text)

  title = md_path.stem.replace("_", " ").title()
  for kind, content in blocks:
    if kind == "h1":
      title = content
      break

  pdf = KnowledgeBasePDF(title=short_title)
  pdf.alias_nb_pages()

  source = "https://www.glancyfawcett.com/"
  tags = ""
  for kind, content in blocks:
    if "Source:" in content:
      source = content.split("Source:**")[-1].strip() if "**" in content else content
    if "Tags:" in content:
      tags = content.split("Tags:**")[-1].strip() if "**" in content else content

  pdf.cover_page(
    title=title,
    subtitle="CRM Enquiry System Knowledge Base",
    meta=[
      f"Source: {source}",
      f"Tags: {tags}" if tags else "Glancy Fawcett FAQ Knowledge",
      "For use by CrewAI Response Crew — KnowledgeRetriever & ComplianceValidator",
    ],
  )

  pdf.add_page()
  render_blocks(pdf, blocks)

  pdf_path.parent.mkdir(parents=True, exist_ok=True)
  pdf.output(str(pdf_path))
  print(f"  Created: {pdf_path.relative_to(ROOT)}")


def build_combined_pdf(md_files: list[Path], pdf_path: Path) -> None:
  pdf = KnowledgeBasePDF(title="Complete Reference")
  pdf.alias_nb_pages()
  pdf.cover_page(
    title="Glancy Fawcett",
    subtitle="Complete Knowledge Base Reference",
    meta=[
      "Sources: glancyfawcett.com | /showrooms | /faqs",
      "CRM Enquiry System — FastAPI + CrewAI",
      f"Documents: {len(md_files)} sections",
    ],
  )

  for md_path in md_files:
    blocks = parse_markdown(md_path.read_text(encoding="utf-8"))
    pdf.add_page()
    section_title = md_path.stem.replace("_", " ").title()
    for kind, content in blocks:
      if kind == "h1":
        section_title = content
        break
    pdf.add_h1(section_title)
    pdf.add_hr()
    render_blocks(pdf, [b for b in blocks if b[0] != "h1"])

  pdf_path.parent.mkdir(parents=True, exist_ok=True)
  pdf.output(str(pdf_path))
  print(f"  Created: {pdf_path.relative_to(ROOT)}")


def main() -> None:
  print("Generating Glancy Fawcett knowledge base PDFs...")
  md_files = sorted(MD_DIR.glob("*.md"))
  if not md_files:
    raise SystemExit(f"No markdown files found in {MD_DIR}")

  PDF_DIR.mkdir(parents=True, exist_ok=True)

  short_titles = {
    "01_company_overview": "Company Overview",
    "02_about_and_clients": "About & Clients",
    "03_starting_your_project": "Starting Your Project",
    "04_in_house_product_design": "Designed by GF",
    "05_quality_logistics_delivery": "Quality & Delivery",
    "06_commercial_payment_terms": "Payment Terms",
    "07_showrooms": "Showrooms",
  }

  for md_path in md_files:
    stem = md_path.stem
    pdf_path = PDF_DIR / f"{stem}.pdf"
    markdown_to_pdf(md_path, pdf_path, short_titles.get(stem, stem))

  build_combined_pdf(md_files, PDF_DIR / "glancy_fawcett_knowledge_base_complete.pdf")
  print(f"\nDone. {len(md_files) + 1} PDF files in knowledge/pdf/")


if __name__ == "__main__":
  main()
