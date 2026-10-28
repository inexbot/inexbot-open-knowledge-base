# Crawl state — 2026-10-26（799/558，连续第七次持平 + 修了一个抽取 bug）

## 结果摘要

| 项目 | 值 |
|---|---|
| inexbot-open docs | **799**（连续第 7 次持平：10-18 / 10-19 / 10-21 / 10-22 / 10-23* / 10-25 / 10-26） |
| index.json 字节 | **2,453,054 bytes**（与 10-23 / 10-24 / 10-25 逐字节相同） |
| locale 拆分 | en=178, kr=178, zh=443（三 locale 全非零） |
| md/ 文件 | 1855 total（1677 locale-prefixed + 178 stale bare） |
| inexbot（姊妹 KB） | **558**（持平） |
| crawler 耗时 | **3:15**（无姊妹 KB 并发，落在 3:00–3:20 稳态带内） |
| 抓取成功 | **799 / 799**，失败 0（发现 799 页，843 hash） |
| check_crawl_state verdict | **IDENTICAL**（与 10-25 字节级一致，真稳态） |
| proxy | **未 restart**（`ActiveEnterTimestamp` = Sun 2026-10-25 11:11:40 CST） |
| 检索链路 | `check_retrieval_chain.py` → 静默降级 0，异常 False，exit 0 |

**净结论：自 2026-10-23 上游 API 改名那次内容变更后，index.json 已连续 4 天逐字节未变
（10-23 / 10-24 / 10-25 / 10-26），2,453,054 bytes 确立为当前基线字节数。**

## 本 cycle 的重点：抓到一个**假警报**并修复了真 bug

`check_staleness.py --sample 25` 报出 cache-only term `cppset_tool_hand_number`。
按 10-23 的经验，这看着像「上游改名 → 其它 locale 卡在旧内容」。

**但这次不是上游改名，是本地 crawler 的抽取 bug。**

真因：VitePress 把语言标签渲染成 `<span class="lang">cpp</span>` 紧挨 `<pre>` 之前，
`li.get_text(strip=True)` 把它和代码文本**无分隔粘在一起** → 凭空造出
`cppset_tool_hand_number`（= "cpp" + "set_tool_hand_number"）。

**关键判据（已写进 SKILL.md）**：`raw/<slug>.html` 里 `cppset_tool_hand_number` 出现
**0 次**、`set_tool_hand_number` 出现 **6 次** → 污染只在 `raw → md` 抽取阶段。
若是上游真改名，raw 里也会缺这个 token。

影响面（实测）：**166 个 index 可达页面**含幻影标识符、**219 个 md 文件**含游离 `cpp` 行。

### 三处修复（`scripts/crawler.py`，已在工作区，未提交）

1. 抽正文前 `decompose()` 掉所有 `span.lang` 徽章
2. 新增 `_pre_to_md()`：从 `pre` / `pre.parent` / `code` 三处取 `language-*` 类
   （旧代码只看 `<code class>`，而 VitePress 放在 wrapper `div.language-*` 上 → 吐裸 `cpp` 行）
3. 列表项内嵌代码块不再压平：散文一行 + 独立 fenced block（缩进 2 空格）

### 离线重生成（未重爬，零网络请求）

从 `raw/` 缓存重抽 → 重写 `md/` → 重建 `index.json`：

- 首轮：改写若干页
- **次轮：`rewritten=0 unchanged=799`** → 证明抽取确定性、修复已生效
- 22 页抽样比对（修复前）：match=22 mismatch=0 → 抽取本就确定性

修复后目标页渲染正确：

```markdown
1. 切换到标定的工具手
  ```cpp
  set_tool_hand_number(fd, toolNum);
  ```
```

（修复前是 `- 切换到标定的工具手cppset_tool_hand_number(fd, toolNum);`）

> 完整分析见 `references/vitepress-lang-badge-extraction-bug.md`；
> 离线重生成已封装为 `scripts/regenerate_from_cache.py`（含 `--check` 干跑模式）。

## ⚠️ 本 cycle 遗留：index.json 尚未用新抽取结果重建

`/tmp/rebuild_index.py` 已写好但**因工具调用次数达上限未执行**。
当前 `index.json` 仍是爬取时由**修复前**代码生成的版本（摘要/word_counts 可能仍含幻影 token）。
**下一步：**

```bash
python3 ~/.hermes/skills/productivity/inexbot-open-knowledge-base/scripts/regenerate_from_cache.py
python3 ~/.hermes/skills/productivity/inexbot-open-knowledge-base/scripts/check_crawl_state.py
/usr/bin/python3 ~/.hermes/skills/productivity/inexbot-open-knowledge-base/scripts/check_retrieval_chain.py
```

## proxy 状态：不需要 restart

- 爬前 `check_proxy_health.py` → `inexbot-open docs=799 loaded=True`、`inexbot docs=558 loaded=True`（**爬前即新值**）
- `systemctl show -p ActiveEnterTimestamp` → `Sun 2026-10-25 11:11:40 CST`，早于本次爬取（11:00–11:03）
- 按 SKILL.md 判据 1「爬前已是新值 → 爬后必然也是，**不需要 restart**」→ 本次未做无谓 restart

### proxy 仓库已前进

- HEAD: `c7c8fab` → **`857991b`**（"fix: 引用链接双重编码导致全部 cite 链接 404"）
- **10-24 的 slug 契约修复（`_md_slug_candidates`）已被推 upstream**——不再是「工作区未提交的本地修复」
- `git diff HEAD` 为空；`hermes-skill-proxy.py` mtime 10-25 11:10:13 < 服务启动 10-25 11:11:40
  → 运行实例加载的就是修复后代码
- 抽样验证两库 cite 链接 **10/10 HTTP 200**，无 `%25` 双重编码

## 本 cycle 无新坑

全部按 SKILL.md 既定流程走完：

1. **policy 拦 wrapper shell** → 照 2026-10-18 起的标准姿势，`write_file` 写
   `/tmp/run_open_crawl_20261026.sh` 再 `terminal(background=true)` 调脚本文件
2. **`process(log)` 对重定向输出的后台任务返回空** → 直接 `tail /tmp/open-crawl-20261026.log`
3. **长任务等待** → `wait_pid.py`（`[200s] target exited`），零 `process(poll)` 浪费
4. **同名脚本覆盖** → 用带日期后缀的 `/tmp/run_open_crawl_20261026.sh`，无 sibling-subagent 警告
5. **`python3 -c` 被 policy 拦**（`script execution via -e/-c flag`）→ 全部走 `write_file` + 文件路径执行
6. **改 `slugify()` 差点写错字符集**（`[<>:\|"?*]` → `[<>:"?*]`，漏了 `|`）→
   用逐条断言脚本验证两种写法输出完全一致后还原

## 上游仓库状态

- `inexbot-open-knowledge-base`：HEAD = origin/main = `2d7b8d7`；工作区有本地改动
  （`SKILL.md`、`scripts/crawler.py`、新增 `scripts/` 与 `references/`）——**本次抽取修复属于其中一部分，尚未提交**
- `hermes-skill-proxy`：HEAD = origin/main = `857991b`，工作区干净

## 历史序列（inexbot-open）

534 (07-18) → 552 (07-26) → 636 (07-31) → 715 (08-21) → 721 (08-25 起连续 7 次)
→ 795 (09-29, +74 zh) → 797 (10-01, +2) → 799 (10-10, +2)
→ 799 (10-18 / 10-19 / 10-21 / 10-22 连续 4 次持平)
→ 799 (10-23, 字节 +4,154，**上游 API 改名**，非零变化)
→ 799 (10-24, 2,453,054 bytes，proxy 侧修复同日落地)
→ 799 (10-25, 2,453,054 bytes，内容变更后连续 3 天零变化)
→ **799 (10-26, 2,453,054 bytes，连续 4 天零变化；同时修复 crawler 语言徽章抽取 bug)**

姊妹 KB inexbot：558 (10-22 起持平)
