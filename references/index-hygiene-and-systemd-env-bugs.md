# 索引卫生三修 + systemd Environment= 静默失效（2026-10-29 现场）

本轮爬取 799/799、零网络请求、上游零变化，但排查中发现并修复了 **3 个此前从未记录的缺陷**。
全部属于**本地抽取 / 部署配置**问题，与上游无关。

---

## 缺陷 1：标题含 U+200B 零宽字符（764 个条目）

### 现象

`index.json` 里 764 个条目的 `title` / `content_snippet` 含 U+200B（零宽空格）。
典型形态：`'C++ 上位机开发\u200b'` —— 标题末尾挂一个不可见字符。

### 根因

VitePress 生成的 `<h1>` 里，标题文本后面跟一个 header-anchor 链接，
其内容就是 U+200B：

```html
<h1>AI 助手 / 自动化工具：先读这里<a class="header-anchor" href="#..."></a></h1>
```

`h1.get_text(strip=True)` 把 anchor 的 U+200B 一起取了出来。

### 影响面（2026-10-29 实测）

| 指标 | `inexbot`（姊妹 KB） | `inexbot-open`（本 KB，修复前） | 修复后 |
|---|---|---|---|
| 含 U+200B 的条目 | **0** | **764** | **0** |
| 其中标题含 ZWSP | 0 | 760 | 0 |
| 空标题条目 | **0** | **39** | **0** |

检索影响：jieba 会把 U+200B **单独切成一个 token**（长度 1），
被 proxy 的 `len(w) >= 2` 过滤掉 → **对检索命中影响有限**（实测 token 重叠数 dirty vs clean 完全相同）。
但对**展示**（注入 LLM 的标题带不可见字符、引用链接显示带怪字符）和
**精确短语匹配**（`query_lower in title`）仍有干扰。属于「该修但不紧急」的卫生问题。

### 关键发现：姊妹 KB 早就有这个修复

姊妹 KB `inexbot-knowledge-base/scripts/crawler.py` 已有 `clean_text()`，
本 KB 一直漏着。**两个 KB 是姊妹关系 —— 修 bug 前先看姊妹 KB 是否已修，
直接移植已验证的实现，不要从零重写。**

```python
def clean_text(s: str) -> str:
    if not s:
        return ""
    s = re.sub(_ZERO_WIDTH, "", s)      # 零宽字符 + BOM
    s = s.replace("\xa0", " ")           # NBSP → 普通空格
    s = "\n".join(line.rstrip() for line in s.split("\n"))
    return s.strip()
```

### ⚠️ 踩坑：字面零宽字符写进源码会被静默吞掉

第一次用 `skill_manage`/编辑把 U+200B **字面量**写进 `_ZERO_WIDTH` 字符集时，
它**被无声地丢掉了** —— 写完检查发现字符集里只剩 `U+200C U+200D U+FEFF`，`U+200B` 不见了。
如果没检查就上线，`clean_text()` 会**漏掉最常见的那个零宽字符**。

**对策：字符集用显式 codepoint 构造，不要写字面量。**

```python
_ZERO_WIDTH = "[" + "".join(chr(c) for c in (0x200B, 0x200C, 0x200D, 0xFEFF)) + "]"
```

**写完必须验证**：

```python
for i, ln in enumerate(src.splitlines(), 1):
    if "_ZERO_WIDTH" in ln:
        print(i, repr(ln), [hex(ord(c)) for c in ln if ord(c) > 127])
```

---

## 缺陷 2：39 个空标题 / 34 个完全无内容条目

### 现象

`index.json` 里 39 个条目 `title` 为空，其中 34 个 `content_snippet` 也为空（完全死条目）。
涉及路径如 `/zh/06.控制器/01.文档/`、`/zh/07.示教器/04.参考/错误码表`、`/zh/08.ROS/02.ROS-2/04.参考/`。

### 根因

这些是**分类索引页**（上游的空目录页）：`raw/` 里有 263KB 的 HTML（整站壳 + sidebar），
但 `<h1>` 不存在、正文容器 `div.vp-doc` 的 textlen = 0。

DOM 结构对照（好页 vs 死页）：

```
好页: div.vp-doc._zh_04_...  textlen=472   ← 真正文
死页: div.vp-doc._zh_06_...  textlen=0     ← 空容器
```

**上游确实是空的**，不是抽取失败 —— 所以「补正文」是不可能的，
能做的是**补标题**（让这些页至少能被标题检索命中）。

### 为什么标题为空有实际影响

proxy 的 `search_single_kb()`：

```python
title = idx[path].get("title", "").lower()
if query_lower and query_lower in title:   # ← 短语命中 +20
    score += 20
for w in query_words:
    if w in item_ds["title_tokens"]:  score += 3   # ← 标题 token +3
    if w in item_ds["desc_tokens"]:   score += 2
    if w in item_ds["content_tokens"]:score += 1
```

标题为空 → 短语命中 +20 和标题 token +3 **全部拿不到**，
只能靠 description 里的通用文案「纳博特科技官方SDK文档」勉强参与匹配。

### 修复：移植姊妹 KB 的标题兜底链

```python
if not title:
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        title = clean_text(og["content"])

if not title:
    seg = unquote(url.rstrip("/").split("/")[-1]) if url.rstrip("/") else ""
    seg = unescape(seg)
    seg = clean_text(seg)
    seg = re.sub(r"\.html?$", "", seg).strip()
    if seg and not seg.lower().startswith(("readme", "index")):
        title = seg[:120]

if not title:
    cand = clean_text(description)[:120]
    if cand and cand != "纳博特科技官方SDK文档" and cand.lower() != "not found":
        title = cand
```

> ⚠️ **实测这 39 页里 `og:title` 存在的是 0 个** → 实际全靠 **URL 末段** 生效
> （`错误码表`、`变更日志`、`数据结构`、`01.文档` 等）。
> 写兜底链时别只测 og:title 那条分支。

修复效果：空标题 39 → **0**，完全死条目 34 → **0**（仍有 34 个 snippet 为空，
但它们现在有标题了，属于「有标题的上游空页」，正常）。

---

## 缺陷 3：systemd `Environment=` 块语法错误 → 4 个环境变量被静默忽略

### 现象

`journalctl -u hermes-skill-proxy` 反复出现：

```
hermes-skill-proxy.service:11: Unknown key name 'PROXY_PORT' in section 'Service', ignoring.
hermes-skill-proxy.service:12: Unknown key name 'HERMES_URL' in section 'Service', ignoring.
hermes-skill-proxy.service:13: Unknown key name 'HERMES_API_KEY' in section 'Service', ignoring.
hermes-skill-proxy.service:14: Unknown key name 'SKILL_NAME' in section 'Service', ignoring.
```

`systemctl show hermes-skill-proxy -p Environment` → `Environment=`（空）。

### 根因

unit 文件里写成了：

```ini
Environment=
  PROXY_PORT=8643
  HERMES_URL=http://localhost:8642
  HERMES_API_KEY=hermes-website-search
  SKILL_NAME=inexbot-knowledge-base
```

**systemd 不支持 `Environment=` 后跟缩进续行** —— 它把 `PROXY_PORT=8643` 当成
一个（未知）的 directive key，于是 4 个变量**全部被丢弃**。
`Environment=` 后面接续行的写法在 shell 的 `.env` 里常见，但 systemd 不认。

### 修复

```ini
Environment="PROXY_PORT=8643"
Environment="HERMES_URL=http://localhost:8642"
Environment="HERMES_API_KEY=hermes-website-search"
Environment="SKILL_NAME=inexbot-knowledge-base"
```

### 复现 / 验证方法（无需改线上文件）

`systemd-analyze verify` 会直接把问题打出来：

```bash
systemd-analyze verify /tmp/probe-fixed.service 2>&1 | grep probe-fixed
```

- 旧写法 → 每行一条 `Unknown key name 'XXX' in section 'Service', ignoring.`
- 新写法 → 无任何针对该 unit 的告警

> ⚠️ **`systemd-analyze verify` 要求文件名以 `.service` 结尾**，
> 用 `.fixed` / `.txt` 会报 `Failed to prepare filename ...: Invalid argument`，
> 看起来像「修复无效」，其实是文件名问题。先 `cp` 成 `xxx.service` 再验。

### 行为影响评估（重要）

修复前 4 个变量就被忽略了 → proxy 一直用**代码默认值**：

```python
HERMES_URL     = os.getenv("HERMES_URL", "http://localhost:8642")
HERMES_API_KEY = os.getenv("HERMES_API_KEY", "hermes-website-search")
PROXY_PORT     = int(os.getenv("PROXY_PORT", "8643"))
```

而且 `/etc` 部署版里的 `HERMES_API_KEY` 是**被截断的占位符** `hermes...arch`（len=13），
与代码默认值 `hermes-website-search`（len=21）**不同**。
若直接把这个占位符写进修好的 unit，proxy 会改用一个**错误的 key** 去转发 gateway。

**结论：修 unit 时 `HERMES_API_KEY` 要显式写成代码默认值 `hermes-website-search`**，
这样修复前后行为完全一致。改之前先比对：

```bash
python3 - <<'PY'   # 用 sha 比对，不要把 key 明文打到日志里
import hashlib
for v in ("hermes...arch", "hermes-website-search"):
    print(v[:6], len(v), hashlib.sha256(v.encode()).hexdigest()[:12])
PY
```

---

## 离线重建 + 内容完整性验证（零网络）

改完 `crawler.py` 的抽取逻辑后，用现成脚本离线重生成（**不要 `--force` 重爬 799 页**）：

```bash
python3 scripts/regenerate_from_cache.py --check   # 先看会改哪些
python3 scripts/regenerate_from_cache.py             # 再写盘
python3 scripts/regenerate_from_cache.py --check   # 必须报 rewritten=0 unchanged=799
```

2026-10-29 实测：第一次 `rewritten=799 unchanged=0`（全部页面都带 ZWSP），
写盘后第二次 `rewritten=0 unchanged=799` ✅ 抽取确定性成立。
index.json：2,453,407 → **2,450,869 bytes**（-2,538）。

### ⚠️ 内容完整性必须核对，别只看「rewritten=0」

`rewritten=0` 只证明**确定性**，不证明**没改坏内容**。
`clean_text()` 会改 `content_md`（行尾 rstrip），必须验证没有内容丢失。

**分词级核对（最有效）**——用新旧两个 extractor 分别抽全文，比对 token 集合：

```python
ot = {w for w in jieba.cut(old_content) if len(w) >= 2 and w.strip("\u200b\ufeff")}
nt = {w for w in jieba.cut(new_content) if len(w) >= 2 and w.strip("\u200b\ufeff")}
lost = ot - nt     # 必须为空
```

2026-10-29 实测（抽样 200 页）：**丢失 token 数 = 0** ✅

全量 `content_md` 比对：774 条一致，25 条不同 —— 逐条看差异**全部是空白差异**
（`\n \n` → `\n\n`，`clean_text()` 的行尾 rstrip 所致），无一处内容变化。

> ⚠️ **snippet 长度变化 ≠ 内容变化。** index 的 `content_snippet` 是 `content_md[:800]`，
> 去掉一个 ZWSP 字符后，800 字窗口的**边界会移动** → snippet 长度会变（-443 字符总量）。
> 这是窗口效应，不是内容丢失。判断内容完整性要比对**未截断的 `content_md`**。

---

## `diagnose_byte_change.py` 的 "MIXED" 假象

本轮该脚本报：

```
VERDICT
MIXED -- on-disk index matches the NEW extractor, but the OLD extractor also differs
from the snapshot: upstream may have moved too.
```

**这是探针的顺序问题，不是上游真的动了。** 原因：

- 脚本拿 `references/.index-snapshot.json` 当「上次快照」
- 但 `regenerate_from_cache.py` **写盘时已经刷新了快照**（新的 2,450,869）
- 于是「上次快照」= 修复后的尺寸，而 `OLD 重建` = 2,453,407（修复前）→ 两者不等 → 报 MIXED

**硬证据仍然指向「纯本地变更」**：
- `crawl log: 0 page fetches`（零网络请求）
- `newest raw/ file: 2026-10-23`（早于本次爬取 10-29）
- `OLD 重建 = 2,453,407` = **恰好等于修复前的 index.json 尺寸**

**判读优先级：抓取次数 + `raw/` mtime > 脚本的 VERDICT 措辞。**
只要「0 次抓取」且「`raw/` 早于爬取开始」，上游就不可能动过。
