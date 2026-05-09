from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, List, Optional, Tuple


ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
LATEST_EXAM_JSON = ARTIFACTS_DIR / "latest_exam.json"


SEASON_RE = re.compile(r"\b(Spring|Autumn|Summer|Winter)\b", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(20\d{2})\b")

PROBLEM_HEADING_RES = [
    # Keep permissive: papers vary between "Practice Problem", "Problem", "Question".
    re.compile(r"^\s*(?:Practice\s+Problem|Problem|Question)\s+(\d{1,2})\b.*$", re.IGNORECASE | re.MULTILINE),
]

SCENARIO_HEADING_RE = re.compile(r"^\s*Scenario\b[^\n]*$", re.IGNORECASE | re.MULTILINE)

EVIDENCE_LINE_RE = re.compile(
    r"^\s*(Email|Letter|Memo|Minutes|Instruction|Request|Report|Note)\b.*$",
    re.IGNORECASE | re.MULTILINE,
)
DATED_RE = re.compile(r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b")  # e.g. 14 Oct 2023


@dataclass
class PracticeProblem:
    number: int
    title_guess: str
    raw_text: str
    evidence_items: List[str]


@dataclass
class ExamArtifact:
    exam_title: str
    source: str
    parsed_at_utc: str
    scenario_text: str
    practice_problems: List[PracticeProblem]
    scenario_projects: List[dict]
    warnings: List[str]


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_text_from_pdf(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "PDF extraction requires `pypdf`. Install dependencies (see requirements.txt) "
            "or pass pre-extracted text using --text/--text-file."
        ) from e

    reader = PdfReader(str(pdf_path))
    chunks: List[str] = []
    for i, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        chunks.append(f"\n\n--- PAGE {i+1} ---\n{page_text}")
    return "\n".join(chunks)


def _normalize_text(raw: str) -> str:
    # If the caller passed literal "\n" sequences (common in shells),
    # convert them into real newlines.
    if "\\n" in raw and "\n" not in raw:
        raw = raw.replace("\\n", "\n")
    # Normalise line endings and collapse excessive blank lines.
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def _guess_exam_title(text: str) -> str:
    # Conservative: find first plausible season/year pair in first ~2000 chars.
    head = text[:2000]
    season = None
    year = None
    m1 = SEASON_RE.search(head)
    if m1:
        season = m1.group(1).title()
    m2 = YEAR_RE.search(head)
    if m2:
        year = m2.group(1)

    if season and year:
        return f"{season} {year}"
    if year:
        return f"Exam {year}"
    return "Unknown exam"


def _find_problem_headings(text: str) -> List[Tuple[int, int, str]]:
    """
    Returns list of (problem_number, start_index, heading_line).
    """
    headings: List[Tuple[int, int, str]] = []
    for rex in PROBLEM_HEADING_RES:
        for m in rex.finditer(text):
            try:
                n = int(m.group(1))
            except Exception:
                continue
            headings.append((n, m.start(), m.group(0).strip()))
    headings.sort(key=lambda x: x[1])
    # De-dup by (n, start)
    out: List[Tuple[int, int, str]] = []
    seen = set()
    for n, idx, h in headings:
        key = (n, idx)
        if key in seen:
            continue
        seen.add(key)
        out.append((n, idx, h))
    return out


def _slice_sections(text: str, starts: List[Tuple[int, int, str]]) -> List[PracticeProblem]:
    problems: List[PracticeProblem] = []
    if not starts:
        return problems

    for i, (n, start_idx, heading) in enumerate(starts):
        end_idx = starts[i + 1][1] if i + 1 < len(starts) else len(text)
        block = text[start_idx:end_idx].strip()
        title_guess = heading
        evidence = _extract_evidence_items(block)
        problems.append(
            PracticeProblem(
                number=n,
                title_guess=title_guess,
                raw_text=block,
                evidence_items=evidence,
            )
        )
    return problems


def _extract_scenario_text(text: str, first_problem_start: Optional[int]) -> str:
    # Prefer explicit "Scenario" heading if present.
    m = SCENARIO_HEADING_RE.search(text)
    if m:
        scenario_start = m.start()
    else:
        scenario_start = 0

    scenario_end = first_problem_start if first_problem_start is not None else len(text)
    scenario = text[scenario_start:scenario_end].strip()
    return scenario


def _extract_evidence_items(problem_text: str) -> List[str]:
    candidates = [m.group(0).strip() for m in EVIDENCE_LINE_RE.finditer(problem_text)]

    # If none found, attempt a weaker heuristic: lines with a date + "from/to".
    if not candidates:
        lines = [ln.strip() for ln in problem_text.splitlines() if ln.strip()]
        for ln in lines:
            if DATED_RE.search(ln) and re.search(r"\b(from|to|re:|subject)\b", ln, re.IGNORECASE):
                candidates.append(ln)

    # De-dup and cap.
    out: List[str] = []
    seen = set()
    for c in candidates:
        c2 = re.sub(r"\s+", " ", c).strip()
        if c2.lower() in seen:
            continue
        seen.add(c2.lower())
        out.append(c2)
    return out[:12]


def _extract_scenario_projects_stub(scenario_text: str) -> List[dict]:
    """
    Lightweight stub: returns [] unless obvious "Project" bullet patterns exist.
    The orchestrator (Layer 1) should still build the portfolio table from scenario_text.
    """
    projects: List[dict] = []
    # Heuristic: lines starting with a project-like bullet.
    for ln in scenario_text.splitlines():
        s = ln.strip()
        if not s:
            continue
        if re.match(r"^[-*]\s+\w+", s):
            projects.append({"hint": s.lstrip("-* ").strip()})
        if len(projects) >= 20:
            break
    return projects


def parse_exam_text(source: str, raw_text: str) -> ExamArtifact:
    warnings: List[str] = []
    text = _normalize_text(raw_text)
    exam_title = _guess_exam_title(text)

    headings = _find_problem_headings(text)
    first_problem_start = headings[0][1] if headings else None
    scenario_text = _extract_scenario_text(text, first_problem_start)
    problems = _slice_sections(text, headings)

    if not problems:
        warnings.append("No practice problem headings detected; output contains scenario_text only.")
    else:
        # Warn if not 10 problems (Part 3 typical).
        unique_nums = sorted({p.number for p in problems})
        if len(unique_nums) != 10:
            warnings.append(f"Detected {len(unique_nums)} unique problems (expected 10): {unique_nums}")

    artifact = ExamArtifact(
        exam_title=exam_title,
        source=source,
        parsed_at_utc=datetime.now(timezone.utc).isoformat(),
        scenario_text=scenario_text,
        practice_problems=problems,
        scenario_projects=_extract_scenario_projects_stub(scenario_text),
        warnings=warnings,
    )
    return artifact


def write_latest_exam_json(artifact: ExamArtifact) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = asdict(artifact)
    LATEST_EXAM_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Parse RIBA Part 3 exam PDF/text into artifacts/latest_exam.json")
    p.add_argument("--pdf", type=str, default=None, help="Path to a text-based PDF exam paper.")
    p.add_argument("--text-file", type=str, default=None, help="Path to a UTF-8 text file containing extracted exam text.")
    p.add_argument("--text", type=str, default=None, help="Raw exam text (use quotes).")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    provided = [x for x in [args.pdf, args.text_file, args.text] if x]
    if len(provided) != 1:
        raise SystemExit("Provide exactly one of: --pdf, --text-file, --text")

    if args.pdf:
        pdf_path = Path(args.pdf).expanduser().resolve()
        raw = _extract_text_from_pdf(pdf_path)
        source = str(pdf_path)
    elif args.text_file:
        txt_path = Path(args.text_file).expanduser().resolve()
        raw = _read_text_file(txt_path)
        source = str(txt_path)
    else:
        raw = str(args.text)
        source = "raw_text"

    artifact = parse_exam_text(source=source, raw_text=raw)
    write_latest_exam_json(artifact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

