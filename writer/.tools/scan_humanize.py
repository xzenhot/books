#!/usr/bin/env python3
"""Scan haveli chapter.md files for non-Bengali characters."""
import re, json
from pathlib import Path

root = Path(r'D:\lab\github\books\writer\.space/pipeline/haveli/chapters')
CHINESE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\U00020000-\U0002a6df]')
URDU = re.compile(r'[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]')
LATIN = re.compile(r'[a-zA-Z]')

results = []
for d in sorted(root.glob('*')):
    if not d.is_dir() or not d.name.isdigit():
        continue
    md = d / 'chapter.md'
    if not md.exists():
        continue
    text = md.read_text(encoding='utf-8-sig')
    issues = {'chinese': set(), 'urdu': set(), 'latin': set()}
    for i, line in enumerate(text.split('\n'), 1):
        c = CHINESE.findall(line)
        u = URDU.findall(line)
        l = LATIN.findall(line)
        if c: issues['chinese'].update(c)
        if u: issues['urdu'].update(u)
        if l: issues['latin'].update(l)
    if any(issues.values()):
        results.append((d.name, issues))

print(f"Chapters with foreign characters: {len(results)}")
for ch, issues in results:
    details = []
    if issues['chinese']: details.append(f"chinese={list(issues['chinese'])[:5]}")
    if issues['urdu']: details.append(f"urdu={list(issues['urdu'])[:5]}")
    if issues['latin']: details.append(f"latin_count={len(issues['latin'])}")
    print(f"  Chapter {ch}: {', '.join(details)}")
