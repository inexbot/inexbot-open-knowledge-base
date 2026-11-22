#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
引用链接实网可达性检查（inexbot-open KB / open.inexbot.com）
=============================================================

为什么需要独立脚本（2026-11-21 新增）
------------------------------------
**引用链接 404 是一类「表层全绿」的静默故障**：
`/health` 绿灯、检索链路 PASS、索引完整性 PASS、crawler 报「832/832 成功」
—— 但**用户点回答末尾的每个链接都是 404**。
⇒ 只有实网打一次链接才能抓到。

姊妹 KB `inexbot-knowledge-base` 有同名脚本（2026-11-10 起），
本脚本是**按本库 URL 语义移植**的版本（见下方「与姊妹版的差异」）。

用法
----
    /usr/bin/python3 scripts/check_citation_links.py
    /usr/bin/python3 scripts/check_citation_links.py --sample 60 --timeout 20
    /usr/bin/python3 scripts/check_citation_links.py --probe-both-forms   # 双形态探测

判定
----
- HTTP 200 / 3xx  -> PASS
- 404 / 410        -> FAIL（引用链接打不开）
- 连接类错误      -> WARN（网络抖动，非内容问题，不计入 FAIL）
- **cjk 池为空**  -> FAIL（检测谓词写错；见下方「陷阱 26」）

⚠️ 陷阱 26（shared-proxy-service-pitfalls.md）
------------------------------------------------
检测中文路径必须 `unquote(k)` **先解码再匹配**；
在**已编码**的 key 上跑 CJK 正则 → **恒为空集** → 脚本静默退化成
「全库随机抽」，**看起来跑通了（60/60 200），但根本没测它声称要测的中文路径**。
⇒ **池子为空就应当报错退出**，绝不能静默退化成全集（兜底分支是在「藏错」，不是「稳健」）。

⚠️ 陷阱 43（shared-proxy-service-pitfalls.md）
------------------------------------------------
**上游的「URL 形态」是会反复漂移的变量**（11-19 收紧 → 11-21 放宽，两天切两次、方向相反）。
⇒ 每轮 cron 都应跑一次 `--probe-both-forms` 看当前是哪一档；
⇒ **绝不**因为「裸形态现在能用」就删掉兼容层。

⚠️ 探测必须用 index.json 的真实条目，别手拼 URL
------------------------------------------------
手拼的路径**可能根本不是 index 里的一条**（例：手拼 `/zh/操作手册` 当普通页 + `.html`
→ **404**），于是错误地得出「上游还没放宽」的结论。
⇒ **URL 必须从 index.json 取**，再按 `url_suffix` 拼出「带后缀」形态，两种都打一次。

与姊妹版的差异（移植时必看）
----------------------------
| 维度 | `inexbot`（姊妹，doc.inexbot.com） | `inexbot-open`（本库，open.inexbot.com） |
|---|---|---|
| index key 形态 | **percent-encoded**（`%E6%8A%80…`） | **明文中文**（`上位机`） |
| `url_suffix` 字段 | **有**（`.html` / `/index.html`，逐条） | **无**（本库 crawler 不写） |
| 路由形态 | `.html` 后缀路由（11-19 起，曾收紧） | **裸路径路由**（11-21 实测裸路径 200） |
| proxy 分派 | `url_suffix_mode: "html"` | `url_suffix_mode: "none"` |
| URL 构造 | `quote(path, safe="/%")`（保留既有 %XX） | `quote(path, safe="/")`（整体编码明文中文） |

⇒ **本库默认输出裸路径**（与 proxy 实际行为一致）；
⇒ 但 index 里若**将来**出现 `url_suffix` 字段，本脚本会自动跟随。
"""

import argparse
import json
import random
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote, unquote

KB_ROOT = Path.home() / ".hermes/kb/inexbot-open"
BASE_URL = "https://open.inexbot.com"

# 本库 index 里目前 0 条带 url_suffix（crawler 不写这个字段）。
# 保留它是为了「将来上游改路由形态时本脚本不用改」。
DEFAULT_SUFFIX = ""


def kb_url(path, suffix="", base=BASE_URL):
    """
    Mirror the proxy's `_kb_url()` for **this KB**.

    本库 index key 是**明文中文**（不是 percent-encoded）⇒ URL 要整体编码。
    姊妹库的 `safe="/%"`（保留既有 %XX）规则**不适用于本库** ——
    照抄会把明文中文原样塞进 URL。

    ⚠️ 陷阱 24/25：归一化规则**必须按 KB 分开**，用同一条规则套两个 KB
    ⇒ 必然大面积假 miss。
    """
    if "%" in path:
        # 兼容将来 index 变成 percent-encoded 的情况
        url = base + quote(path, safe="/%")
    else:
        url = base + quote(path, safe="/")
    if suffix:
        if suffix.startswith("/"):
            return url.rstrip("/") + suffix
        return url + suffix
    return url


def fetch_status(url, timeout):
    req = urllib.request.Request(url, method="GET", headers={
        "User-Agent": "Mozilla/5.0 (compatible; kb-citation-check)",
        "Accept": "text/html,*/*",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read(512)
            return r.status, ""
    except urllib.error.HTTPError as e:
        return e.code, "HTTPError"
    except Exception as e:
        return 0, type(e).__name__ + ": " + str(e)[:80]


def probe_both_forms(index, keys, timeout):
    """
    双形态探测（陷阱 43）：对每条真实 index 条目同时打「裸路径」与
    「带 .html 后缀」，用来判定上游当前是「收紧」还是「放宽」路由。

    ⚠️ **URL 必须从 index.json 取**，别手拼（手拼会误判，见模块 docstring）。
    """
    bare_ok = sfx_ok = 0
    rows = []
    sfx_present = 0
    for k in keys:
        sfx = index[k].get("url_suffix", "")
        if sfx:
            sfx_present += 1
        else:
            sfx = ".html"
        b = fetch_status(kb_url(k, ""), timeout)[0]
        s = fetch_status(kb_url(k, sfx), timeout)[0]
        bare_ok += (b == 200)
        sfx_ok += (s == 200)
        rows.append((k, sfx, b, s))

    print("=== 双形态探测（陷阱 43）===")
    print("index 条目里带 url_suffix 字段的条数 : %d" % sfx_present)
    print("裸路径   200 : %d/%d" % (bare_ok, len(keys)))
    print("带后缀   200 : %d/%d" % (sfx_ok, len(keys)))
    if bare_ok == len(keys) and sfx_ok == len(keys):
        verdict = "上游『放宽』：两套并存 —— **什么都不改**（绝不删兼容层）"
    elif bare_ok == 0 and sfx_ok > 0:
        verdict = "上游『收紧』：只认后缀 —— 本库需要实施 url_suffix 支持"
    else:
        verdict = "混合状态 —— 逐条看下面的明细"
    print("VERDICT: %s" % verdict)
    print("--- 明细（前 15 条：key | suffix | bare | sfx）---")
    for r in rows[:15]:
        print("  %-58s %-12s %s %s" % (r[0][:58], r[1], r[2], r[3]))
    return bare_ok, sfx_ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=60)
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20261121)
    ap.add_argument("--probe-both-forms", action="store_true",
                    help="额外做双形态探测，判定上游当前路由档位（陷阱 43）")
    args = ap.parse_args()

    index = json.loads((KB_ROOT / "index.json").read_text(encoding="utf-8"))
    keys = list(index.keys())
    print("index entries: %d" % len(keys))

    # ⚠️ TRAP 26: 检测谓词必须作用在**已解码**的 key 上。
    # 本库 key 本来就是明文中文，但**仍然要 unquote** —— 万一将来
    # index 变成 percent-encoded，不解码就会得到空池子。
    cjk = [k for k in keys if re.search(r"[\u4e00-\u9fff]", unquote(k))]

    if not cjk:
        print("[FAIL] cjk pool is EMPTY -- the detection predicate is wrong.")
        print("       index keys may be percent-encoded; decode before matching.")
        print("       Refusing to fall back to random sampling over the whole")
        print("       index (that would silently test the wrong subset).")
        return 1

    pool = cjk if len(cjk) >= args.sample else keys
    random.seed(args.seed)
    if len(pool) > args.sample:
        sample = random.sample(pool, args.sample)
    else:
        sample = pool

    # ⚠️ 目录页强制并入样本：它们只有十几条，随机抽样几乎抽不到，
    # 而它们恰是「后缀规则最容易写错」的那一类。
    # 本库目前 0 条带 url_suffix=/index.html，但保留这段以防上游改路由。
    dir_keys = [k for k in keys if index[k].get("url_suffix") == "/index.html"]
    if dir_keys:
        forced = [k for k in dir_keys if k not in sample]
        sample = sample + forced
        print("forced-in directory pages (url_suffix=/index.html): %d" % len(forced))

    ok = bad = warn = 0
    failures = []
    warnings = []
    for k in sample:
        # 本库默认裸路径（proxy 的 url_suffix_mode = "none"）；
        # 若 index 里出现 url_suffix 字段则自动跟随。
        url = kb_url(k, index[k].get("url_suffix", DEFAULT_SUFFIX))
        code, err = fetch_status(url, args.timeout)
        if code == 200:
            ok += 1
        elif code in (301, 302, 303, 307, 308):
            ok += 1
        elif code in (404, 410):
            bad += 1
            failures.append((code, k, url))
        else:
            warn += 1
            warnings.append((code or err, k, url))

    print("sampled: %d   (cjk pool: %d)" % (len(sample), len(cjk)))
    print("HTTP 200/3xx : %d" % ok)
    print("HTTP 404/410 : %d" % bad)
    print("network err  : %d" % warn)

    if failures:
        print("\n--- FAIL (引用链接打不开) ---")
        for code, k, url in failures[:20]:
            print("  %s  %s" % (code, url))
    if warnings:
        print("\n--- WARN (网络类, 非内容问题) ---")
        for code, k, url in warnings[:10]:
            print("  %s  %s" % (code, url[:120]))

    if args.probe_both_forms:
        print()
        probe_both_forms(index, random.sample(keys, min(30, len(keys))), args.timeout)

    print("\n=> %s" % ("PASS: 全部引用链接可达" if bad == 0 else "FAIL: %d 条 404" % bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
