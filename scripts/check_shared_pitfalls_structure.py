#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""结构自检：共享 pitfalls 文件有没有「重复块 / 孤儿块 / 标题截断」。

背景（2026-11-13 实测，见 shared-proxy-service-pitfalls.md §陷阱 31）：
两个 KB 的 agent 同时 patch 同一个共享文件时，可能拼出
  - 孤儿块：有完整正文，但没有自己的 `## 陷阱 N：` 标题（标题被吞）
  - 重复块：同一段正文出现两次（一次在正常 section 里，一次在文件末尾）
  - 标题截断：`## 陷阱 N` 存在但切不出对应正文

这类损坏**两个 KB 都看得见**，且**sha1 两边一致**（同一个 commit 推过去的）
⇒ 只靠 `diff_shared_pitfalls.py`（比内容）**抓不到** —— 必须单独做结构检查。

用法：
    /usr/bin/python3 scripts/check_shared_pitfalls_structure.py
    /usr/bin/python3 scripts/check_shared_pitfalls_structure.py --file <path>

退出码：
    0 = 结构完好
    1 = 发现重复块 / 孤儿块 / 标题截断
    2 = 文件不存在

⚠️ 必须用 /usr/bin/python3（cron 禁内联脚本，见 §陷阱 29）。
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

DEFAULT_FILES = [
    Path.home() / ".hermes/skills/productivity/inexbot-open-knowledge-base/references/shared-proxy-service-pitfalls.md",
    Path.home() / ".hermes/skills/productivity/inexbot-knowledge-base/references/shared-proxy-service-pitfalls.md",
]

SECTION_RE = re.compile(r"^##\s+(陷阱\s+\d+[^\n]*)$")
SUBHEAD_RE = re.compile(r"^###\s+")
# 门槛：短于这个长度的重复行多半是表格分隔线 / 装饰线，不算重复块
MIN_LINE_LEN = 40


def analyze(text):
    lines = text.splitlines()
    headings = []
    for i, ln in enumerate(lines):
        m = SECTION_RE.match(ln)
        if m:
            headings.append((i, m.group(1).strip()))

    problems = []
    warnings = []

    # --- 1) 重复长行 ——
    # ⚠️ 只报 WARNING，不计入退出码：同一份 pitfalls 里不同 section 复用
    #    同一段 shell 片段是**正常**的（例如「trap 1 的诊断命令」与
    #    「trap 20 的决策流程」都含 `ps -o pid,lstart,etime -p $(pgrep -f ...)`）。
    #    2026-11-15 实测：把重复行当 FAIL 会让脚本对**结构完好**的文件
    #    稳定返回 exit 1 → 变成「天天误报的假警报」，比没有守卫更糟。
    seen = {}
    for i, ln in enumerate(lines):
        s = ln.strip()
        if len(s) < MIN_LINE_LEN:
            continue
        if s.startswith("|"):
            continue
        if s.startswith("#"):
            continue
        seen.setdefault(s, []).append(i + 1)
    for s, positions in seen.items():
        if len(positions) > 1:
            warnings.append(
                ("DUPLICATE_LINE", f"line {s[:60]!r} appears at lines {positions}")
            )

    # --- 2) 标题截断：最后一个标题之后没有正文 ---
    if headings:
        last_idx, last_title = headings[-1]
        tail = [ln for ln in lines[last_idx + 1:] if ln.strip()]
        if not tail:
            problems.append(("EMPTY_SECTION", f"last section {last_title!r} has no body"))
        # 最后一个 section 的正文应该直到文件尾
    else:
        problems.append(("NO_SECTIONS", "no '## 陷阱 N' headings found at all"))

    # --- 3) 子标题多于 section 数 -> 可能有孤儿块 ---
    n_sub = sum(1 for ln in lines if SUBHEAD_RE.match(ln))
    if headings and n_sub > len(headings) * 3:
        problems.append(
            ("SUSPECT_ORPHAN", f"{n_sub} sub-headings vs {len(headings)} sections -- check for a body without its own heading")
        )

    # --- 4) 重复块 / 孤儿块：某个 section 的正文在文件里出现了第二份 ---
    # ⚠️ 这才是「重复块 / 孤儿块」的真判据（2026-11-13 实测：陷阱 27 的正文
    #    在文件末尾成孤块 —— **没有自己的 `## 陷阱 27：` 标题**）。
    #
    # 做法：对每个 section 取「正文开头 SIG_LINES 个非空行」当签名，
    #    在整份文件的非空行序列里滑动找该签名的出现次数。
    #    出现 > 1 次 → 有一份复制体（正常 section + 末尾孤块，或两个同名正文）。
    #
    # ⚠️ 为什么不用「整段正文」当签名：最后一个 section 的正文延伸到 EOF，
    #    若孤块恰好是它的复制体，「整段正文」会**把孤块吸进自己** →
    #    签名随之改变 → 反而找不到重复（2026-11-15 实测踩到）。
    #    固定长度的前缀签名不受影响。
    SIG_LINES = 8

    nonempty = [ln.strip() for ln in lines if ln.strip()]
    body_of = {}
    for k, (start, title) in enumerate(headings):
        end = headings[k + 1][0] if k + 1 < len(headings) else len(lines)
        body = [ln.strip() for ln in lines[start + 1:end] if ln.strip()]
        body_of[title] = body

    sig_owner = {}
    for title, body in body_of.items():
        if len(body) < SIG_LINES:
            continue
        sig = tuple(body[:SIG_LINES])
        hits = 0
        for j in range(len(nonempty) - SIG_LINES + 1):
            if tuple(nonempty[j:j + SIG_LINES]) == sig:
                hits += 1
        if hits > 1:
            problems.append(
                ("DUPLICATE_BLOCK",
                 f"section body of {title!r} appears {hits} times (orphan/duplicate copy)")
            )
        sig_owner[sig] = sig_owner.get(sig, 0) + 1

    for sig, owners in sig_owner.items():
        if owners > 1:
            problems.append(
                ("DUPLICATE_SECTION",
                 f"{owners} sections share the same body prefix {sig[:2]}")
            )

    return problems, warnings, len(headings), n_sub, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", action="append", help="path to check (repeatable)")
    args = ap.parse_args()

    files = [Path(f) for f in args.file] if args.file else DEFAULT_FILES
    rc = 0
    for f in files:
        print(f"=== {f} ===")
        if not f.exists():
            print(f"  [FAIL] file not found")
            rc = 2
            continue
        text = f.read_text(encoding="utf-8")
        problems, warnings, n_sec, n_sub, lines = analyze(text)
        print(f"  sections={n_sec}  sub-headings={n_sub}  lines={len(lines)}")
        for kind, detail in warnings:
            print(f"  [WARN {kind}] {detail}")
        if not problems:
            print("  [OK] structure intact: no duplicate/orphan/truncated sections")
            continue
        rc = 1
        for kind, detail in problems:
            print(f"  [{kind}] {detail}")
        # 打印重复正文块的标题，供人工核对
        heads = [SECTION_RE.match(ln).group(1).strip()
                 for ln in lines if SECTION_RE.match(ln)]
        print(f"  section titles: {heads}")

    return rc


if __name__ == "__main__":
    sys.exit(main())
