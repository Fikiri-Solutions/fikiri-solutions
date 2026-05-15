#!/usr/bin/env python3
"""
Extract text from every PDF in this folder and save each as a .txt file.

Naming choices:
  - Variables: what they hold (path_to_pdf, text_from_page) so you can read the code like a sentence.
  - No single letters (f, i) except in tiny loops; we use output_txt_file, page_index.
  - "current" in a loop = the one we're working on this time through.
"""

from pathlib import Path

from pypdf import PdfReader

# ---------------------------------------------------------------------------
# 1. Decide where to look for PDFs (same folder as this script)
# ---------------------------------------------------------------------------
# Rationale: So the script works no matter where you run it from (Terminal at
# project root vs elsewhere). We use the script's location, not the current
# working directory.
# Example: If script is at /Users/mac/Desktop/CAP 6629/extract_pdf_text.py,
#          script_directory becomes /Users/mac/Desktop/CAP 6629 - Reinforcement Learning
script_directory = Path(__file__).parent

# ---------------------------------------------------------------------------
# 2. Process each PDF in that folder
# ---------------------------------------------------------------------------
# .glob("*.pdf") returns an iterable of Paths—one per file whose name ends with .pdf.
# Rationale: We don't hardcode filenames; any new PDF you drop in is picked up.
# Example: script_directory.glob("*.pdf") might give [Path("Lecture 0114.pdf"), Path("Data Mining_....pdf")]
for path_to_current_pdf in script_directory.glob("*.pdf"):
    # Output file: same name as the PDF, extension changed to .txt (same folder).
    # Rationale: One-to-one mapping, easy to find: "Lecture 0114.pdf" -> "Lecture 0114.txt".
    # Example: path_to_current_pdf = Path("Lecture 0114.pdf") -> path_to_output_txt = Path("Lecture 0114.txt")
    path_to_output_txt = path_to_current_pdf.with_suffix(".txt")

    print(f"Converting: {path_to_current_pdf.name}")

    # Open the PDF for reading. PdfReader reads metadata and page list; it doesn't load every page into memory at once.
    # Rationale: Keeps memory use reasonable for large PDFs.
    pdf_reader = PdfReader(path_to_current_pdf)

    # Open the .txt file for writing. "w" overwrites if it exists. utf-8 handles accents and symbols.
    # Rationale: "with" guarantees the file is closed when we leave the block, even if something goes wrong.
    with open(path_to_output_txt, "w", encoding="utf-8") as output_txt_file:
        # Loop over every page. enumerate() gives us (0, page0), (1, page1), ... so we can show progress and detect "every 50th".
        for page_index, current_page in enumerate(pdf_reader.pages):
            # Extract text from this page. Can be empty for images-only or blank pages.
            text_from_page = current_page.extract_text()

            if text_from_page:
                output_txt_file.write(text_from_page)
                output_txt_file.write("\n\n")  # Blank line between pages so they don't run together.

            # Progress: print every 50 pages so we know it's still working on big PDFs.
            # Example: page_index 49 -> (49+1) % 50 == 0 -> print "... 50 pages"
            if (page_index + 1) % 50 == 0:
                print(f"  ... {page_index + 1} pages")

    print(f"  Saved: {path_to_output_txt.name}\n")

print("All done.")
