"""
Document Parser
================
Converts an uploaded CV (PDF, DOCX, or TXT) into clean plain text, and
splits both CVs and job descriptions into semantically meaningful chunks
that the embedding model can work with.

This is the first stage of the pipeline shown in the architecture diagram:

    Job Posting ─┐
                 ↓
    CV ───→ Document Parser ───→ Embedding Model ───→ Vector Database
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass

from pypdf import PdfReader
from docx import Document as DocxDocument


class UnsupportedFileType(ValueError):
    pass


@dataclass
class ParsedDocument:
    raw_text: str
    chunks: list[str]


def _extract_pdf_text(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _extract_docx_text(file_bytes: bytes) -> str:
    doc = DocxDocument(io.BytesIO(file_bytes))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    parts.append(cell.text)
    return "\n".join(parts)


def extract_text(filename: str, file_bytes: bytes) -> str:
    """Dispatch on file extension and return raw extracted text."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        text = _extract_pdf_text(file_bytes)
    elif lower.endswith(".docx"):
        text = _extract_docx_text(file_bytes)
    elif lower.endswith(".txt") or lower.endswith(".md"):
        text = file_bytes.decode("utf-8", errors="ignore")
    else:
        raise UnsupportedFileType(
            f"Unsupported file type for '{filename}'. Use PDF, DOCX, or TXT."
        )
    return _normalize_whitespace(text)


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# --- Chunking -----------------------------------------------------------
#
# CVs are chunked by "sections" (headed by things like EXPERIENCE, SKILLS,
# EDUCATION, PROJECTS) and then by bullet/sentence within long sections.
# Job descriptions are chunked by bullet points / sentences, since that is
# roughly the granularity of a single "requirement".

SECTION_HEADER_RE = re.compile(
    r"^\s*(SUMMARY|OBJECTIVE|EXPERIENCE|WORK EXPERIENCE|EMPLOYMENT|SKILLS|"
    r"TECHNICAL SKILLS|EDUCATION|PROJECTS|CERTIFICATIONS|ACHIEVEMENTS|"
    r"PUBLICATIONS|LANGUAGES)\s*:?\s*$",
    re.IGNORECASE,
)

BULLET_RE = re.compile(r"^\s*[-•*▪●○◦‣·]\s+")


def chunk_cv(text: str, max_chunk_chars: int = 500) -> list[str]:
    """Split a CV into section-aware chunks suitable for embedding."""
    lines = text.split("\n")
    sections: list[list[str]] = [[]]
    for line in lines:
        if SECTION_HEADER_RE.match(line.strip()):
            sections.append([line.strip()])
        else:
            sections[-1].append(line)

    chunks: list[str] = []
    for section_lines in sections:
        section_text = "\n".join(l for l in section_lines if l.strip())
        if not section_text.strip():
            continue
        chunks.extend(_split_long_text(section_text, max_chunk_chars))

    return [c for c in chunks if len(c.strip()) > 15]


def chunk_job_description(text: str, max_chunk_chars: int = 400) -> list[str]:
    """Split a job description into requirement-sized chunks (roughly one
    bullet point or sentence per chunk)."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    chunks: list[str] = []
    buffer = ""

    for line in lines:
        if BULLET_RE.match(line) or len(line) > 40:
            if buffer:
                chunks.append(buffer.strip())
                buffer = ""
            # Further split long sentences on ". "
            sentences = re.split(r"(?<=[.;])\s+", BULLET_RE.sub("", line))
            chunks.extend(s for s in sentences if len(s.strip()) > 8)
        else:
            buffer += " " + line

    if buffer.strip():
        chunks.append(buffer.strip())

    # Merge accidental tiny fragments back together up to max_chunk_chars
    merged: list[str] = []
    for c in chunks:
        if merged and len(merged[-1]) + len(c) < max_chunk_chars // 2:
            merged[-1] = merged[-1] + " " + c
        else:
            merged.append(c)

    return [c for c in merged if len(c.strip()) > 8]


def _split_long_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    # Split on paragraph or bullet boundaries first
    parts = re.split(r"\n(?=[-•*▪●○◦‣·]|\s*\n)", text)
    out: list[str] = []
    buf = ""
    for part in parts:
        if len(buf) + len(part) > max_chars and buf:
            out.append(buf.strip())
            buf = part
        else:
            buf += "\n" + part
    if buf.strip():
        out.append(buf.strip())
    return out


def parse_cv(filename: str, file_bytes: bytes) -> ParsedDocument:
    raw_text = extract_text(filename, file_bytes)
    return ParsedDocument(raw_text=raw_text, chunks=chunk_cv(raw_text))


def parse_job_description(text: str) -> ParsedDocument:
    text = _normalize_whitespace(text)
    return ParsedDocument(raw_text=text, chunks=chunk_job_description(text))
