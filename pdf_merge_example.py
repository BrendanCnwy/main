"""Demonstration of PdfMerger usage with PyPDF2.

This script will:
- create two small sample PDFs if they don't exist
- merge them using PdfMerger, showing bookmarks and page ranges
- write `merged_demo.pdf` in the current directory
"""
from pathlib import Path
from PyPDF2 import PdfMerger, PdfWriter


def create_sample_pdf(path: Path, pages: int = 2) -> None:
    if path.exists():
        return
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72 * 8.5, height=72 * 11)
    with path.open("wb") as f:
        writer.write(f)


def main() -> None:
    base = Path(__file__).parent
    a = base / "sample_a.pdf"
    b = base / "sample_b.pdf"

    # Create sample PDFs if missing
    create_sample_pdf(a, pages=3)
    create_sample_pdf(b, pages=2)

    out = base / "merged_demo.pdf"

    # Basic merge with bookmarks and a page range
    with PdfMerger() as merger:
        merger.append(str(a), bookmark="Sample A")
        # append all of B and add a bookmark
        merger.append(str(b), bookmark="Sample B")
        # append only the first page of B (pages are zero-based, end-exclusive)
        merger.append(str(b), pages=(0, 1), bookmark="B - first page")
        merger.write(str(out))

    print(f"Wrote merged file: {out}")


if __name__ == "__main__":
    main()
