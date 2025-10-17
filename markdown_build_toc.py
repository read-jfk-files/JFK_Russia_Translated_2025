#!/usr/bin/env python3
# All code generate by ChatGPT
# Build a linked Table of Contents for the existing Markdown by scanning headings
# and injecting a nested bullet list with anchor links.
#
# Input:  document_pretty.md
# Output: document_pretty_with_TOC.md

import sys
import re
from pathlib import Path

def slugify(s: str, used):
    # GitHub-like slug: lowercase, strip punctuation, spaces -> dashes, collapse dashes
    slug = s.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    base = slug or "section"
    slug = base
    i = 2
    while slug in used:
        slug = f"{base}-{i}"
        i += 1
    used.add(slug)
    return slug

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python markdown_build_toc.py INPUT.md OUTPUT.md")
        sys.exit(2)
    in_md = Path(sys.argv[1])
    out_md = Path(sys.argv[2])
    md = in_md.read_text(encoding="utf-8", errors="ignore")

    # Find headings up to depth 4 (# .. ####)
    heading_re = re.compile(r"^(#{1,4})\s+(.*)$", re.MULTILINE)

    # Collect headings and build TOC entries
    used_slugs = set()
    entries = []
    for m in heading_re.finditer(md):
        hashes, text = m.group(1), m.group(2).strip()
        level = len(hashes)
        # Skip if it's the main title (level 1) but still linkable in TOC; keep it
        slug = slugify(text, used_slugs)
        entries.append((level, text, slug))

    # If no headings or only one, skip TOC
    if len(entries) <= 1:
        toc_block = ""
    else:
        # Build nested bullet list
        toc_lines = ["## Table of Contents", ""]
        prev_level = entries[0][0]
        # We'll start from the first heading; if it's H1, include it, otherwise still list from first
        for level, text, slug in entries:
            indent = "  " * (level - 1)  # H1 indent 0, H2 indent 2 spaces, etc.
            toc_lines.append(f"{indent}- [{text}](#{slug})")
        toc_lines.append("")

        toc_block = "\n".join(toc_lines)

    # Inject anchors into the document by appending explicit IDs after headings,
    # but in regular Markdown engines the (#{slug}) pattern isn't standard.
    # Instead, we'll rely on renderer auto-IDs; we won't alter headings themselves.
    # We just ensure our TOC slugs match common conventions.

    # Place TOC after the first H1 if present, otherwise at the beginning
    first_h1 = re.search(r"^#\s+.*$", md, flags=re.MULTILINE)
    if toc_block:
        if first_h1:
            # Insert after the first H1 block
            pos = first_h1.end()
            # Find the next non-empty line after H1 to insert a blank line then TOC
            md = md[:pos] + "\n\n" + toc_block + "\n" + md[pos:]
        else:
            md = toc_block + "\n" + md

    out_md.write_text(md, encoding="utf-8")
    print(f"Saved Markdown with linked TOC to: {out_md}")

