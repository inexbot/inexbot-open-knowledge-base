#!/usr/bin/env python3
"""
md 可达性检查 —— 用 proxy 的**权威** slug 契约反查 index.json 的每一条。

为什么需要这个脚本（陷阱 11 / 34 家族）：
    「index 里的每个 path 能不能找到对应的 md 文件」这个问题，**不能自己 join**。
    自己写的 slug 逻辑（哪怕是 import 来的 crawler.slugify）也算不出来，
    因为 proxy 的定位逻辑是 `_md_slug_candidates()`：多候选 + unquote + 兜底。

    2026-11-17 实测（第 7 次复发）：
        自写 crawler.slugify() 直连      -> 790 / 817  ← 假阳性，看着像 KB 回归
        proxy 的 _md_slug_candidates()   -> 817 / 817  ← 真实值
    两者的差别不是「写错了」，而是「proxy 的契约不止一个函数」：
    crawler.slugify() 只覆盖**一种**命名形态，proxy 要面对**两种编码态**
    + 超长名 MD5 截断 + OSError 兜底。

用法：
    /usr/bin/python3 scripts/check_md_reachability.py
    /usr/bin/python3 scripts/check_md_reachability.py --kb both

输出：
    index entries            : 817
    resolved via _md_slug_candidates : 817
    unresolved               : 0

退出码：
    0 = 全部可达（健康）
    1 = 有不可达条目（真问题，或脚本自身环境异常）
    2 = 找不到 proxy 模块 / index.json

⚠️ 必须用 /usr/bin/python3（沙盒 python3 没有 flask，proxy 模块 import 不了）。
⚠️ 这个脚本 import 的是 proxy 本体，因此是「用被测组件自己的函数」——
   这正是陷阱 11/24/25/34 一再强调的修法：**别复刻，去复用**。
"""

import importlib.util
import json
import sys
import types
from pathlib import Path

PROXY_PY = Path("/home/ecs-user/hermes-skill-proxy/hermes-skill-proxy.py")
KB_ROOT = Path.home() / ".hermes/kb"

# 两个 KB 的索引目录名 -> 展示名
KB_DIRS = {
    "inexbot-open": "inexbot-open",
    "inexbot": "inexbot",
}


def load_proxy():
    """加载 proxy 模块。优先 /usr/bin/python3（flask 真实存在）；
    没有 flask 时用 stub 兜住 —— 但 stub 可能因 proxy 新增 API 而失效。"""
    try:
        import flask  # noqa: F401
        has_flask = True
    except ImportError:
        has_flask = False

    if not has_flask:
        flask = types.ModuleType("flask")
        flask.Flask = type(
            "Flask",
            (),
            {
                "__init__": lambda self, *a, **k: None,
                "route": lambda self, *a, **k: (lambda f: f),
            },
        )
        flask.request = types.SimpleNamespace(get_json=lambda *a, **k: {}, data=b"")
        flask.Response = object
        flask.jsonify = lambda *a, **k: {}
        flask.stream_with_context = lambda f: f
        sys.modules["flask"] = flask

    spec = importlib.util.spec_from_file_location("hsp", str(PROXY_PY))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["hsp"] = mod
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    return mod


def check_one(mod, kb_dir):
    """对单个 KB 做可达性反查。返回 (resolved, unresolved_list, total)。"""
    idx_path = KB_ROOT / kb_dir / "index.json"
    md_dir = KB_ROOT / kb_dir / "md"

    if not idx_path.exists():
        return None, [], 0

    idx = json.loads(idx_path.read_text(encoding="utf-8"))

    resolved = 0
    unresolved = []
    for path in idx:
        hit = False
        try:
            # 关键：必须用 proxy 自己的候选生成器，且自己拼 ".md"（陷阱 11）
            for slug in mod._md_slug_candidates(path):
                if (md_dir / (slug + ".md")).exists():
                    hit = True
                    break
        except OSError:
            # 超长文件名候选会抛 OSError [Errno 36] —— 必须兜住，
            # 否则检查脚本自己先崩掉（陷阱 11 末尾的警告）
            continue
        if hit:
            resolved += 1
        else:
            unresolved.append(path)

    return resolved, unresolved, len(idx)


def main():
    which = "both"
    if "--kb" in sys.argv:
        i = sys.argv.index("--kb")
        if i + 1 < len(sys.argv):
            which = sys.argv[i + 1]

    if not PROXY_PY.exists():
        print(f"[FAIL] 找不到 proxy 模块: {PROXY_PY}", file=sys.stderr)
        return 2

    mod = load_proxy()

    targets = list(KB_DIRS.values()) if which == "both" else [which]
    bad = False
    for kb_dir in targets:
        resolved, unresolved, total = check_one(mod, kb_dir)
        if resolved is None:
            print(f"[SKIP] {kb_dir}: 没有 index.json")
            continue
        print(f"=== {kb_dir} ===")
        print(f"  index entries            : {total}")
        print(f"  resolved via _md_slug_candidates : {resolved}")
        print(f"  unresolved               : {len(unresolved)}")
        for u in unresolved[:10]:
            print(f"     UNRESOLVED: {u}")
        if len(unresolved) > 10:
            print(f"     ... 还有 {len(unresolved) - 10} 条")
        if total and resolved != total:
            bad = True
            print(
                f"  [FAIL] {kb_dir}: {total - resolved} 条 index 无法定位到 md\n"
                f"         ⚠️ 先怀疑脚本/环境，别急着判 KB 回归 ——\n"
                f"         陷阱 11/34：定位失败率 100% 时几乎必然是脚本自己的问题。"
            )
        else:
            print(f"  [OK] {kb_dir}: 全部 {total} 条均可达")

    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
