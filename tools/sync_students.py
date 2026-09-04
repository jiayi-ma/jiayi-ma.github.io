#!/usr/bin/env python3
"""Render the student section from the archived Wuhan University profile.

The archive is fetched first by ``sync_whu_profile_source.py``.  Keeping this
rendering step local means the published site never injects remote HTML.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path


def student_records(paragraphs: list[str]) -> tuple[str, list[list[str]], list[list[str]]]:
    try:
        start = next(i for i, text in enumerate(paragraphs) if "指导学生情况" in text)
        active = next(i for i in range(start, len(paragraphs)) if "在读学生" in paragraphs[i])
    except StopIteration as error:
        raise RuntimeError("Could not locate student sections in the Wuhan University source.") from error

    cutoff = ""
    for text in paragraphs[start:active]:
        match = re.search(r"截止?\s*(\d{4}年\d{1,2}月)", text)
        if match:
            cutoff = match.group(1)
            break

    def parse(lines: list[str], graduated: bool) -> list[list[str]]:
        records: list[list[str]] = []
        for text in lines:
            text = text.strip().rstrip("；。")
            if not text or text.startswith("姓名") or "学生" in text[:8]:
                continue
            parts = [part.strip() for part in text.split("，")]
            if len(parts) < 2 or not re.search(r"硕|博", parts[1]):
                continue
            name, program = parts[0], parts[1]
            if graduated and len(parts) >= 3:
                records.append([name, program, "，".join(parts[2:-1]), parts[-1]])
            else:
                records.append([name, program, "，".join(parts[2:])])
        return records

    graduated = parse(paragraphs[start:active], graduated=True)
    current = parse(paragraphs[active + 1 :], graduated=False)
    if not graduated or not current:
        raise RuntimeError("Student records were incomplete; leaving the published section unchanged.")
    return cutoff, graduated, current


def render_record(record: list[str], graduated: bool) -> str:
    tags = [f"<strong>{html.escape(record[0])}</strong>", f"<span>{html.escape(record[1])}</span>"]
    if len(record) >= 3 and record[2]:
        tags.append(f"<em>{html.escape(record[2])}</em>")
    if graduated and len(record) >= 4 and record[3]:
        tags.append(f"<b>{html.escape(record[3])}</b>")
    return "          <li>" + "".join(tags) + "</li>"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("res/whu-profile-source.json"))
    parser.add_argument("--index", type=Path, default=Path("index.html"))
    args = parser.parse_args()

    source = json.loads(args.source.read_text(encoding="utf-8"))
    cutoff, graduated, current = student_records(source.get("paragraphs", []))
    intro_date = cutoff or "最新官方记录"
    section = f'''    <section id="students" class="students-section" aria-labelledby="students-heading">
      <h2 id="students-heading"><strong>指导学生情况</strong></h2>
      <p class="section-intro">截至 {intro_date}，已毕业学生 {len(graduated)} 名、在读学生 {len(current)} 名。以下列出学生在读期间发表的一作论文及毕业去向。</p>

      <div class="mentorship-summary" aria-label="Student mentorship summary">
        <div><strong>{len(graduated)}</strong><span>已毕业学生</span></div>
        <div><strong>{len(current)}</strong><span>在读学生</span></div>
        <div><strong>2017–{intro_date[:4] if cutoff else '至今'}</strong><span>指导记录</span></div>
      </div>

      <details class="student-group" open>
        <summary><span>已毕业学生</span><span class="group-count">{len(graduated)} 名</span></summary>
        <ul class="student-list">
{chr(10).join(render_record(row, graduated=True) for row in graduated)}
        </ul>
      </details>

      <details class="student-group">
        <summary><span>在读学生</span><span class="group-count">{len(current)} 名</span></summary>
        <ul class="student-list compact">
{chr(10).join(render_record(row, graduated=False) for row in current)}
        </ul>
      </details>
    </section>'''
    index = args.index.read_text(encoding="utf-8")
    pattern = r'    <section id="students" class="students-section".*?\n    </section>(?=\n\s*<section id="honors")'
    updated, count = re.subn(pattern, section, index, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError("Could not replace exactly one student section.")
    args.index.write_text(updated, encoding="utf-8")
    print(f"Rendered {len(graduated)} graduated and {len(current)} current students.")


if __name__ == "__main__":
    main()
