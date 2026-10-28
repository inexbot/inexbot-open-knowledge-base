#!/usr/bin/env python3
"""
检索链路全链路验证（两个 KB 一起查）
=====================================

为什么需要这个脚本
------------------
`/health` 返回 `{"inexbot":{"docs":558,"loaded":true},"inexbot-open":{"docs":799,"loaded":true}}`
**只证明「index.json 读进来了」，不证明「正文读到了」**。

hermes-skill-proxy 的 `read_full_content()` 曾经与 crawler 的 `slugify()` 不一致，
导致正文永远拿不到：抛 `OSError` 的直接 500，不抛错的**静默降级**成 index.json 里
800 字的 `content_snippet` —— 看起来完全正常，没有任何报错线索。

**关键点：两个 KB 共用同一个 `read_full_content()`。**
姊妹 KB `inexbot-knowledge-base` 2026-10-24 实测已修复（`snippet_len=4000`），
但 open KB 是否同样中招**必须实测**，不能假设 —— open.inexbot.com 的 URL 更短
（带 `en-`/`kr-`/`zh-` 前缀），slug 碰撞形态不同。

判定标准
--------
`snippet_len` 是正文长度（上限 4000）：
- `> 800`  → 正文命中 ✅
- `== 800` → **静默降级成摘要 = BUG**（退回 index.json 的 content_snippet）
- `< 200`  → 该页正文本来就短（如伺服报错系列只有一行），**不是 bug**，
              要对照 `md/` 文件实际大小确认

用法
----
```bash
/usr/bin/python3 ~/.hermes/skills/productivity/inexbot-open-knowledge-base/scripts/check_retrieval_chain.py
```

⚠️ 必须用 **system python**（`/usr/bin/python3`）——沙盒 `python3` 没装 flask。
⚠️ 本地 security policy 禁止 `python3 -c`，所以脚本必须走文件路径。

退出码：0 = 检索链路正常；1 = 有条目静默降级成 800 字摘要（需要修 proxy）
"""
import importlib.util as _iu
import sys
from pathlib import Path

PROXY = "/home/ecs-user/hermes-skill-proxy/hermes-skill-proxy.py"
SNIPPET_FALLBACK = 800   # index.json 的 content_snippet 上限 = 摘要兜底的特征值

# 每个 KB 各挑几条能命中正文的查询
QUERIES = [
    # inexbot-open（open.inexbot.com：开放平台 / 二次开发）
    "JSON RPC 上位机 通信 协议",
    "NRC_GetRobotTypeConfig 机器人结构类型",
    "servo_point_position_motion_control 运动控制",
    "ROS 主站 库 二次开发",
    "HAL 上位机 接口",
    # inexbot（doc.inexbot.com：产品技术文档）
    "伺服报警 0x0051 IPM故障",
    "示教器 换图",
    "通讯协议 地址码 Modbus 寄存器",
    "冲压工艺 手册 参数设置",
    "工业机器人控制器 C1102",
    "NexAutoCail 标定",
]


def load_proxy():
    spec = _iu.spec_from_file_location("px", PROXY)
    mod = _iu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.load_all_indexes()
    return mod


def main():
    if not Path(PROXY).exists():
        print(f"✗ proxy 不存在: {PROXY}")
        return 1

    try:
        P = load_proxy()
    except Exception as e:
        print(f"✗ proxy 加载失败: {type(e).__name__}: {e}")
        print("  → 确认用 /usr/bin/python3 跑（沙盒 python3 没装 flask）")
        return 1

    print("=" * 70)
    print("检索链路验证 —— 判定: >800 正文命中 | ==800 静默降级(BUG) | <200 本来就短")
    print("=" * 70)

    degraded = []   # 静默降级成 800 字摘要
    short = []      # 正文本来就短（需人工确认，非必然是 bug）
    oserror = False

    for q in QUERIES:
        print(f"\n=== {q} ===")
        try:
            res = P.search_all_kb(q)
        except Exception as e:
            oserror = True
            print(f"  ✗ search_all_kb 抛异常: {type(e).__name__}: {e}")
            print("     → 这是最严重的一档：整个 /v1/chat/completions 会 500")
            continue

        for kb, items in res.items():
            for it in items:
                n = len(it["content_snippet"])
                title = it["title"][:34]
                if n == SNIPPET_FALLBACK:
                    print(f"  [{it['score']:5.1f}] {title:36s} len={n:<6} <-- 摘要兜底(BUG)")
                    degraded.append((kb, q, title, n))
                elif n < 200:
                    print(f"  [{it['score']:5.1f}] {title:36s} len={n:<6} <-- 可能本来就短")
                    short.append((kb, q, title, n))
                else:
                    print(f"  [{it['score']:5.1f}] {title:36s} len={n:<6} OK")

    print("\n" + "=" * 70)
    print(f"静默降级(==800): {len(degraded)}   短正文(<200): {len(short)}   异常: {oserror}")
    for d in degraded:
        print("   BUG:", d)
    for s in short:
        print("   短 :", s)

    if oserror or degraded:
        print("\n✗ 检索链路有问题 —— 详见姊妹 skill "
              "inexbot-knowledge-base/references/proxy-slug-contract-break.md")
        return 1

    print("\n✓ 检索链路正常：所有条目都读到了正文，无 800 字摘要兜底。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
