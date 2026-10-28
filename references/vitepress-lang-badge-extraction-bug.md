# VitePress 语言徽章污染：crawler 抽取出的「幻影标识符」

> 发现日期：2026-10-26 cron cycle。**这是一个会伪装成「上游改名」的假警报**——
> 差点让人误以为上游把 API 重命名了，从而白做一次「精准失效缓存」的重爬。

## 症状

`check_staleness.py` 报出一个 cache-only term：

```
zh   1  cppset_tool_hand_number
```

按 SKILL.md「增量爬取的盲区」章节的判据，这看起来正是 2026-10-23 那种
「上游改名 → 其它 locale 永久停留在旧内容」的场景。**但这次不是。**

## 真因：`<span class="lang">` 徽章被粘到代码文本前面

VitePress / shiki 把语言标签渲染成紧挨 `<pre>` 之前的：

```html
<div class="language-cpp">
  <span class="lang">cpp</span>
  <pre class="shiki ..."><code><span class="line">
    <span>set_tool_hand_number</span><span>(fd, toolNum);</span>
  </span></code></pre>
</div>
```

crawler 原来的 `ul/ol` 分支写的是：

```python
lines.append(prefix + li.get_text(strip=True))
```

`get_text(strip=True)` 会把 `<span class="lang">cpp</span>` 和紧随其后的代码文本
**无分隔地粘在一起** → 产出根本不存在的标识符 `cppset_tool_hand_number`。

同理还会产出 `cpp_interface`、`cpp_demo`、`connect_robot`（`cpp` + `connect_robot`）等。

**影响面（2026-10-26 实测）**：
- **166 个 index 可达页面**含此类幻影标识符
- **219 个 md 文件**含游离的独立 `cpp` 行（`<pre>` 前的徽章被当成正文段落吐出）
- 只有「列表项内嵌代码块」这一种结构会触发（`li.get_text()` 才会跨过 `div.language-*` 拼接）

## 关键判据：先看 raw，再看 md

**`raw/<slug>.html` 是干净的**——crawler 存的原始 HTML 里 `html.count("cppset_tool_hand_number") == 0`，
`set_tool_hand_number` 出现 6 次。**污染只发生在 `raw → md` 的抽取阶段。**

所以：

| 检查 | 结论 |
|---|---|
| raw HTML 有幻影 token | 上游真的改了 → 走「精准失效缓存」流程 |
| **raw HTML 干净，只有 md 有** | **本地抽取 bug → 不要重爬，改 crawler** |

这个顺序能省掉一次「失效缓存 + 重爬 + 核对」的整个循环（10-23 那次是 5 条 / 10 个文件 / 3:19）。

### 快速判定脚本

```python
raw = (KB / "raw" / f"{slug}.html").read_text(encoding="utf-8", errors="ignore")
md   = (KB / "md"   / f"{slug}.md").read_text(encoding="utf-8", errors="ignore")
print("raw has phantom:", PHANTOM in raw)   # False => 本地抽取 bug
print("md   has phantom:", PHANTOM in md)   # True  => 确认污染
```

## 已实施的修复（`scripts/crawler.py`）

### 1. 抽正文前先摘掉语言徽章

```python
for tag in article.find_all(["nav", "script", "style", "footer", "aside", "button", "input"]):
    tag.decompose()
# VitePress renders a language badge as <span class="lang">cpp</span> right
# before <pre>.  get_text() glues it onto the following code text, which
# fabricates identifiers like "cppset_tool_hand_number" (badge "cpp" +
# "set_tool_hand_number").  Strip the badges before extracting text.
for badge in article.find_all("span", class_="lang"):
    badge.decompose()
```

### 2. 新增 `_pre_to_md()`：正确取语言标签

旧代码只从 `<code class="language-xxx">` 取语言，但 VitePress 把语言放在
**wrapper `<div class="language-xxx">`** 上 → 旧逻辑拿不到 → 吐出裸 `cpp` 行。
新逻辑依次查 `pre` / `pre.parent` / `pre.find("code")` 三处的 class。

### 3. 列表项内嵌代码块不再压平

旧：`- 切换到标定的工具手cppset_tool_hand_number(fd, toolNum);`
新：

```markdown
1. 切换到标定的工具手
  ```cpp
  set_tool_hand_number(fd, toolNum);
  ```
```

实现：`<li>` 若含 `<pre>`，散文用 `_text_without_pre(li)`（clone 后 decompose 掉 `pre`），
代码另起 fenced block（缩进 2 空格）。

## 离线重生成 md（不重爬、不给上游加压）

修复后**不需要** `--force` 重抓 799 页。`raw/` 缓存是完好的，只是抽取逻辑变了，
可以**纯离线**从 `raw/` 重生成 `md/`：

```python
# 逐个 index path：读 raw/<slug>.html -> extract_content() -> 写 md/<slug>.md
# 写盘格式必须与 crawler 主流程完全一致：
new = f"# {pd['title']}\n\n"
if pd["description"]:
    new += f">{pd['description']}\n\n"
new += pd["content_md"]
```

**幂等性验证**：跑第二遍应输出 `rewritten=0 unchanged=799`。
2026-10-26 实测首轮改写若干页、次轮 0 改写——**证明抽取是确定性的**。

> 建议先验证「raw → md 抽取是确定性」的（跑两遍比较），再批量重生成。
> 2026-10-26 的验证样本：22 页抽样 match=22 mismatch=0。

## 重建 index.json

md 改完后，`index.json` 的 `content_snippet` / `word_counts` 仍是旧抽取结果，
**必须重建**（否则摘要里还带着幻影 token，jieba 分词也把它当词）：

```python
pages = []
for p in sorted(idx):
    slug = crawler.slugify(p.lstrip("/"))
    pd = crawler.extract_content((KB/"raw"/f"{slug}.html").read_text(encoding="utf-8"),
                                "https://open.inexbot.com" + p)
    pd["path"] = p
    pages.append(pd)
new_index = crawler.build_search_index(pages)   # 复用 crawler 自己的函数
crawler.save_json(new_index, crawler.INDEX_F)
```

同样是纯离线，不打网络。

## 验证清单

```bash
# 1. 幻影 token 消失
grep -rl "cppset" ~/.hermes/kb/inexbot-open/md/*.md    # 只应命中不可达死缓存文件
# 2. 游离 cpp 行大幅减少
grep -l '^cpp$' ~/.hermes/kb/inexbot-open/md/*.md | wc -l
# 3. 目标页渲染正确
grep -n "切换到标定的工具手" \
  ~/.hermes/kb/inexbot-open/md/zh-04.上位机-01.C++-03.示例-02.基础应用-13.工具手标定.md
# 4. 状态探针 + 检索链路
python3 ~/.hermes/skills/productivity/inexbot-open-knowledge-base/scripts/check_crawl_state.py
/usr/bin/python3 ~/.hermes/skills/productivity/inexbot-open-knowledge-base/scripts/check_retrieval_chain.py
```

## 给未来的自己

- `check_staleness.py` 报的 cache-only term **不一定是上游改名**。
  **先查 raw，再下结论。** 只有 raw 里也缺这个词，才是上游真改了。
- 改 `crawler.py` 的 `slugify()` 时**逐字保留字符集**（`[<>:\|"?*]`）。
  2026-10-26 误把它写成 `[<>:"?*]`（漏了 `|`），虽行为等价但会让 diff 变脏；
  已用逐条断言脚本验证两种写法输出完全一致。
- 修 `crawler.py` 后，**proxy 的 `read_full_content()` 不需要改**——它只按 index path
  定位 md，读的是 md 文件本身；md 内容变好，proxy 立刻受益。
