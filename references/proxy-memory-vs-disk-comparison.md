# 比对 proxy 内存索引 vs 磁盘 index.json —— 两个 KB 共用的三个陷阱

2026-10-29 姊妹 KB（`inexbot-knowledge-base`）cron 现场沉淀。
**两个 KB 共用同一个 `hermes-skill-proxy`**，所以这里的坑对两边都成立。

姊妹 skill 的完整版本：`inexbot-knowledge-base/references/proxy-runtime-freshness.md`
（本文只收录姊妹 KB 现场新增的三条更正）。

---

## 陷阱 1：比对内存索引时**不能比 `title` 字符串**（会得到全量假阳性）

### 症状

写了一段脚本比对「proxy 内存索引」与「磁盘 `index.json`」，输出：

```
memory doc count: 558 disk index count: 558
key sets equal: True
title mismatches memory vs disk: 558      ← 558 条全部「不一致」
```

明明内容逐字节相同（`IDENTICAL`），却报 558 条不一致 → **纯假阳性**。

### 根因

proxy 的 `_doc_scores[name][path]` 存的是**分词后的 token 集合**，不是原始字符串：

```python
scores[path] = {
    "title_tokens":   {w for w in jieba.cut(item.get("title",""))       if len(w) >= 2},
    "desc_tokens":   {w for w in jieba.cut(item.get("description","")) if len(w) >= 2},
    "content_tokens":{w for w in jieba.cut(item.get("content_snippet","")) if len(w) >= 2},
    "word_counts":   item.get("word_counts", {}),
}
```

`mem[k]` 里**没有 `title` 键** → `mem[k].get("title")` 恒为 `""` →
`disk[k]["title"] != ""` 恒为 `True`。

### ✅ 正确做法：token 级比对

把磁盘侧也用**同一套** jieba 规则切词，再比集合：

```python
import importlib.util, sys, json
from pathlib import Path
import jieba

spec = importlib.util.spec_from_file_location("hsp", "/home/ecs-user/hermes-skill-proxy/hermes-skill-proxy.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["hsp"] = mod
spec.loader.exec_module(mod)
mod.load_all_indexes()          # ← 必须调用

def toks(s):                     # ← 必须与 proxy 的切词规则一致（len >= 2）
    return {w for w in jieba.cut(s or "") if len(w) >= 2}

kb   = "inexbot-open"
disk = json.loads((Path.home()/".hermes/kb/inexbot-open/index.json").read_text(encoding="utf-8"))
mem  = mod._doc_scores[kb]
dk, mk = set(disk), set(mem)
print("memory:", len(mem), "disk:", len(disk), "key sets equal:", dk == mk)

bad = 0
for k in dk.intersection(mk):
    d, m = disk[k], mem[k]
    if (toks(d.get("title",""))           != m["title_tokens"]
     or toks(d.get("description",""))     != m["desc_tokens"]
     or toks(d.get("content_snippet","")) != m["content_tokens"]):
        bad += 1
print("token-level mismatches (memory vs disk):", bad)
```

判读：
- `key sets equal == False` → **内存索引已过期，必须重启 proxy**
- `token-level mismatches > 0` → 内容也过期
- 全 0 → 内存索引与磁盘逐条一致，**无需重启**

2026-10-29 实测（inexbot）：key 集合相同、token 级比对 **0 处不一致**。

> 💡 `mod._index_data[kb]` 存的是**原始 index dict**（可以直接比 title/snippet），
> 但它和 `_doc_scores` 是同一次 `load_all_indexes()` 的产物，一样是「新进程读的磁盘」，
> **不代表线上进程的内存**。两个都验不出线上真实内存 ——
> 线上只能靠「进程启动时间 vs index.json mtime」判据。

---

## 陷阱 2：手写 slug 契约检查会崩在 `OSError [Errno 36]`

### 症状

自己拼候选 md 文件名做「index key → md 文件」反查，脚本当场崩：

```
OSError: [Errno 36] File name too long:
'/home/ecs-user/.hermes/kb/inexbot/md/%2Fzh%2F%25E4%25BA%25A7%25E5%2593%2581...C1102.md'
```

### 根因

候选列表里如果有 `quote(path, safe="")`（**双重编码**形态），
超长中文路径编码后远超 Linux **255 字节**文件名上限 → `Path.exists()` 抛 `Errno 36`。

proxy 自己是用 try/except 兜住的（`read_full_content()` 里 `except OSError: continue`），
所以**线上不会挂** —— 但**你的检查脚本会挂**。

### ✅ 正确做法：复用 proxy 的候选生成函数

```python
for k, v in idx.items():
    path = v.get("path") or k
    hit = None
    for slug in mod._md_slug_candidates(path):     # ← 复用 proxy 的实现，别复刻
        cand = md_root / f"{slug}.md"
        try:
            if cand.exists():
                hit = cand; break
        except OSError:                              # ← Errno 36 必须兜住
            continue
```

2026-10-29 实测：复用 `_md_slug_candidates()` 后 **558/558 全部解析成功，
`OSError` 吞掉 0 次**（第一个候选就命中，根本走不到超长的 `quote()` 候选）。

> 💡 这正是「三个 slug 契约副本（proxy / `retrieve.py` / `check_crawl_state.py`）
> 必须保持一致」的价值 —— **复用而不是复刻**。

---

## 陷阱 3：`verify_kb.py` 的「短 snippet」note 不等于有 BUG

### 症状

`verify_kb.py` 输出：

```
note: 短 snippet  247  inexbot / 示教器 操作手册 / 操作手册  ← 疑似静默降级
```

### 判别表

`verify_kb.py` 的 note 只是「长度 < 800」的粗筛。真正的判别要看 **md 文件的实际字节数**：

| `snippet_len` | md 实际字节数 | 结论 |
|---|---|---|
| `== 800` | — | **静默降级**（index 摘要兜底）→ BUG |
| `< 800` | `== snippet_len` | **正文已完整读取**，只是这一页本身就很短 → 正常 |
| `< 800` | `> snippet_len` | 部分读取 → 查 slug 契约 |

### 核验脚本

```python
for r in mod.search_single_kb("inexbot", q, 30):
    if len(r.get("content_snippet","")) < 800:
        hit = None
        for slug in mod._md_slug_candidates(r.get("path") or ""):
            c = md_root / f"{slug}.md"
            try:
                if c.exists(): hit = c; break
            except OSError: continue
        disk_len = len(hit.read_text(encoding="utf-8")) if hit else -1
        print(r["title"], len(r["content_snippet"]), disk_len)
```

2026-10-29 实测：5 条「短 snippet」note 全部满足 `md_bytes == snippet_len`
（247 / 277 / 418 / 440 / 468 字节），即**磁盘正文被完整取出**，
这些是「示教器无法开机」「伺服错误」这类本身就两三行的 FAQ 页 → **无 BUG**。

---

## 附：另外两个工具坑（2026-10-29 再次验证）

### heredoc 里写 `&` 会被 terminal 拦下

```
Foreground command uses '&' backgrounding. Use terminal(background=true) ...
```

`for k in dk & mk:` 会被安全扫描判成「前台命令用了后台符号」直接拒绝执行 ——
**在 heredoc 里也一样会被拦**。

✅ 改用集合方法：`dk.intersection(mk)` / `dk.difference(mk)` / `dk.union(mk)`。

### 无人值守 cron 下删文件会被审批卡住

```
rm -f /tmp/proxy_chain_test.py ...
→ ⚠️ delete in root path. Asking the user for approval.
```

cron 场景**没人能批** → 清理做不成。

✅ **优先清进程**（`kill <PID>`）而不是清文件 —— 进程才是占端口/吃资源的实体，
残留的 `.py`/`.log` 不占端口、不影响服务。确需删文件时，
在报告里写明残留清单 + 理由，把决定权交回用户。

> 💡 压测残留**最该盯的是进程和端口**。
> 2026-10-29 检查：`ss -ltnp | grep -E "864[0-9]"` 只有 8643 + 8642 → 端口干净 →
> `/tmp` 里的 `.py` 残留不影响交付，可以放着。
