#!/usr/bin/env python3
import re, sys, textwrap
from pathlib import Path

# All code generate by Claude 4.5
# ---------- Heuristics you can tweak ----------
ARTIFACTS = [
    r"\bSignal\s+copy\b", r"\bSignal\s+Copy\b",
    r"\[Signal\s+copy\]", r"\[Control\s+copy\]", r"\[Special\s+copy\]",
    r"\bControl\s+copy\b", r"\bSpecial\s+copy\b", r"\[Page number\]",
]
MAX_HEADING_LEN = 120

def strip_artifacts(t: str) -> str:
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    for pat in ARTIFACTS:
        t = re.sub(pat, "", t, flags=re.IGNORECASE|re.MULTILINE)
    # drop standalone page numbers
    t = re.sub(r"^\s*\d+\s*$", "", t, flags=re.MULTILINE)
    return t

def is_section_heading(line: str) -> bool:
    return bool(re.match(r"^\s*SECTION\s+[IVXLCMD]+\b", line.strip()))

def is_allcaps_heading(line: str) -> bool:
    s = line.strip()
    return (0 < len(s) <= MAX_HEADING_LEN
            and re.search(r"[A-Za-z]", s)
            and not re.search(r"[a-z]", s))

def is_number_label(line: str) -> bool:
    return bool(re.match(r"^\s*No\.\s*\d+\b", line.strip(), flags=re.IGNORECASE))

def is_list_item(line: str) -> bool:
    return bool(re.match(r"^\s*(?:\d+\.\s+|[-*]\s+)", line))

def cleanup_toc(line: str) -> str:
    return re.sub(r"\.{5,}", " — ", line)

def txt_to_markdown(txt: str) -> str:
    txt = strip_artifacts(txt)
    lines = txt.split("\n")

    tagged = []
    for ln in lines:
        r = ln.rstrip()
        if is_section_heading(r):
            tagged.append((r.strip(), "H1"))
        elif is_allcaps_heading(r):
            tagged.append((r.strip(), "H2"))
        elif is_number_label(r):
            tagged.append((r.strip(), "LABEL"))
        elif is_list_item(r):
            tagged.append((r, "LIST"))
        elif re.search(r"footnote", r, re.IGNORECASE) or re.match(r"^\s*\[?Footnotes\]?:?", r, re.IGNORECASE):
            tagged.append((r.strip(), "FNHDR"))
        else:
            tagged.append((r, "TEXT"))

    # collapse wrapped text into paragraphs
    paras, buf = [], []
    def flush():
        nonlocal buf
        if buf:
            paras.append(("TEXT", " ".join(buf).strip()))
            buf = []
    for ln, kind in tagged:
        if kind in ("H1","H2","LABEL","LIST","FNHDR"):
            flush()
            paras.append((kind, ln))
        else:
            if ln.strip()=="":
                flush()
            else:
                buf.append(ln.strip())
    flush()

    # render to MD
    out = []
    for kind, content in paras:
        if kind=="H1":
            out += ["", "# " + content.title(), ""]
        elif kind=="H2":
            out += ["", "## " + content.title(), ""]
        elif kind=="LABEL":
            out += ["", f"**{content}**", ""]
        elif kind=="LIST":
            out.append(cleanup_toc(content))
        elif kind=="FNHDR":
            out += ["", "### Footnotes", ""]
        else:  # TEXT
            out.append(re.sub(r"\s{2,}", " ", content))
    md = "\n".join(out).strip() + "\n"
    # Optional: add a top title if none present
    if not md.startswith("# "):
        m = re.search(r"^## (.+)$", md, flags=re.MULTILINE)
        if m:
            md = "# " + m.group(1) + "\n\n" + md
    return md

def markdown_to_pdf(md: str, pdf_path: Path):
    # Minimal ReportLab renderer (headings + body)
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.units import inch

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="H1", parent=styles["Heading1"], spaceAfter=12))
    styles.add(ParagraphStyle(name="H2", parent=styles["Heading2"], spaceAfter=8))
    styles.add(ParagraphStyle(name="Body", parent=styles["BodyText"], leading=14))

    doc = SimpleDocTemplate(str(pdf_path), pagesize=LETTER,
                            leftMargin=0.9*inch, rightMargin=0.9*inch,
                            topMargin=0.9*inch, bottomMargin=0.9*inch)
    story = []
    for line in md.split("\n"):
        if line.startswith("# "):
            story += [Paragraph(line[2:].strip(), styles["H1"]), Spacer(1, 8)]
        elif line.startswith("## "):
            story += [Paragraph(line[3:].strip(), styles["H2"]), Spacer(1, 6)]
        elif line.strip()=="":
            story.append(Spacer(1, 6))
        elif re.match(r"^\*\*No\.\s*\d+\*\*$", line.strip()):
            story += [Paragraph(line.strip(), styles["H2"]), Spacer(1, 4)]
        elif re.match(r"^\s*(\d+\.\s+|[-*]\s+)", line):
            story.append(Paragraph(line, styles["Body"]))
        else:
            story.append(Paragraph(line, styles["Body"]))
    doc.build(story)

def main():
    if len(sys.argv) < 3:
        print("Usage: python txt_to_pdf.py INPUT.txt OUTPUT.pdf")
        sys.exit(2)
    in_path = Path(sys.argv[1])
    out_pdf = Path(sys.argv[2])
    md_path = out_pdf.with_suffix(".md")

    md = txt_to_markdown(in_path.read_text(encoding="utf-8", errors="ignore"))
    md_path.write_text(md, encoding="utf-8")
    print(f"Wrote Markdown: {md_path}")

    try:
        markdown_to_pdf(md, out_pdf)
        print(f"Wrote PDF: {out_pdf}")
    except ImportError:
        print("ReportLab not installed. PDF step skipped. Install with: pip install reportlab")

if __name__ == "__main__":
    main()
