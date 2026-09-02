"""General utility functions."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from report_formatter import ReportSection, sections_to_markdown


OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


def ensure_output_dir() -> Path:
    """Create the report output directory if needed."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    return OUTPUT_DIR


def safe_filename(name: str) -> str:
    """Return a filesystem-safe patient/report filename stem."""
    cleaned = "".join(char for char in name.strip().lower().replace(" ", "-") if char.isalnum() or char == "-")
    return cleaned or "patient"


def export_report(patient: dict[str, object], sections: list[ReportSection]) -> tuple[Path, Path]:
    """Export a report to Markdown and CSV summary files."""
    output_dir = ensure_output_dir()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = f"{safe_filename(str(patient.get('full_name', 'patient')))}-{stamp}"
    markdown_path = output_dir / f"{stem}.md"
    csv_path = output_dir / f"{stem}.csv"

    markdown_path.write_text(sections_to_markdown(sections), encoding="utf-8")

    rows = [{"section": section.title, "content": section.content} for section in sections]
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    return markdown_path, csv_path
