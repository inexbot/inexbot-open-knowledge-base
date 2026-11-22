# 2026-11-21 爬取快照 — 832 稳态（连续第 4 天持平）

## 一、结论摘要

| 项 | 值 |
|---|---|
| crawl verdict | **IDENTICAL**（与 11-20 逐字节相同） |
| index.json | **832 entries, 2,620,789 bytes**（与 11-18 / 11-19 / 11-20 完全一致） |
| locale 分布 | zh=476 / en=178 / kr=178 |
| 抓取耗时 | **3:56**（实测 11:01:10 → 11:05:07） |
| 网络抓取次数 | **0**（日志 `✓` 行数 = 0，`raw/` 最新 mtime = 11-18 11:03） |
| 判定 | **纯本地重抽取，零网络请求 → 上游零变更** |
| 姊妹 KB inexbot | **561**（维持） |
| e2e 探针 | **12/12 全 200**（43.1–118.7s，**0 次 502/500** → 连续第 16 天 502 计数为 0） |

**832 是 11-18 打破 817 稳态后的新基线**，**连续第 4 天持平**（11-19 / 11-20 / 11-21 均 IDENTICAL）。

---

## 二、本轮与 11-20 的差异

- **唯一变化：无。** index.json 字节数完全相同（2,620,789 × 4 天）。
- `raw/` 最新 mtime = **2026-11-18 11:03**（早于本次爬取起点 11-21 11:01:10）
  → 本轮 832 页**全部命中缓存**，**一个页面都没重新抓**。
- md/ 今日改动 = **0** 个文件（与 IDENTICAL 判定自洽）。
- 无 `.tmp` 残留（原子写 `save_json()` 正常工作）。
- 爬取耗时 **3:56**（历史稳态带 3:00–4:42 内）→ 正常。

---

## 三、轮次第 0 步：11-20 那轮被 429 打断，本轮独立核验

`hermes cron list` 显示 11-20 的 `Last run` 字段为
`2026-11-20T11:25:38 error: RuntimeError: HTTP 429: 已达到 Token Plan 用量上限…`

⇒ **该轮是被中断的**，其报告正文里的「已提交」等结论**一律作废**（§陷阱 14 同族规则）。

**本轮独立核验（不信任上一轮报告）**：

| 核验项 | 结果 |
|---|---|
| 本库 `git status -sb` | `## main...origin/main` —— **工作树干净** |
| `git log --oneline -3` | `919c25f docs: add 2026-11-20 crawl snapshot (832, 3rd day identical), sync shared pitfalls` |
| 11-20 快照文件 | `references/crawl-state-2026-11-20.md` **已在版本库** |
| 姊妹库 `git status` | 干净（仅 1 个姊妹自己的 `?? scripts/_tmp_url_suffix_stats.py` 临时文件，**非本库职责，不代提交**） |
| proxy 仓库 `git status` | 干净 |

⇒ 11-20 那轮虽被 429 打断，但**实质工作已入库**（提交发生在写报告之前，符合「改 → commit → push → 写报告」的正确顺序）。

---

## 四、8 步标准验证序列（全绿）

| # | 检查 | 结果 | 关键数据 |
|---|---|---|---|
| 1 | `check_crawl_state.py` | ✅ exit 0 | **IDENTICAL** / 832 / 2,620,789 B / zh=476 en=178 kr=178 |
| 2 | `check_index_hygiene.py` | ✅ exit 0 | 零宽 0、空标题 0、幻影 token 可达 0、旧 API 可达 0、空 snippet 34（上游空目录页） |
| 3 | `check_retrieval_chain.py` | ✅ exit 0 | **静默降级(==800) = 0**；短正文 4 条（61–71 B，伺服报警占位页，属上游本来就短） |
| 4 | `check_proxy_health.py` | ✅ exit 0 | open **832** / sister **561**，均 loaded=True（爬前已核，爬后必然同值） |
| 5 | `check_e2e_request.py` | ✅ 12/12 | 见 §六 |
| 6 | `check_proxy_env.py --units` | ✅ exit 0 | 5 个变量在「线上 environ / /etc 部署版 / repo 模板」三处 sha12 逐项一致；`HERMES_TIMEOUT` sha12=`e49ec846db75` = 1800 ✅ |
| 6b | `check_url_to_index_key.py` | ✅ exit 0 | **93/93**；静默降级 0；no-md lookup 0 |
| 7 | `check_proxy_staleness.py` | ✅ exit 0 | 线上 PID 2016323 源码 == HEAD `b9def11` → **NOT stale，无需 restart** |
| 8 | `check_reload_timer.py` | ✅ exit 0 | 重载链存活，定时器线程 tid=2027591（07:05:12 起），**下次重载 12:05:12**；内存 832 == 磁盘 832 → 已同步 |

**附加守卫**：
- `check_md_reachability.py` → ✅ open **832/832** + sister **561/561**
- `check_token_consistency.py` → ✅ **PASS**（两个 KB 各 0 处不一致）
- `check_shared_pitfalls_structure.py` → ✅ **OK**（两库各 42 sections，仅 WARN 级重复行，不计入退出码）
- `test_shared_pitfalls_structure.py` → ✅ 回归通过（完好文件 exit 0 / 孤儿体 exit 1）
- `diff_shared_pitfalls.py` → ✅ **IDENTICAL**（与姊妹 sha1 `74ee0c7fd0aafc4f56efb02575ed3d38f1fd3b61` 完全一致，**本轮无需同步**）
- journal 按进程切片（PID 2016323，since 2026-11-20 11:04:53，466 行）：
  `Unknown key` **0** / HTTP 500 **0** / HTTP 502 **0** / `RELOAD FAILED` **0** /
  `Traceback` **0** / HTTP 200 = **45**

---

## 五、本轮零 proxy restart（§陷阱 20 再次生效）

- 爬前 `check_proxy_health.py` 已是 **832**（新值）→ 爬后必然也是 → **不需要为内容 restart**。
- `check_proxy_staleness.py`：线上 PID **2016323** 源码 == HEAD `b9def11` → 行为等价 → **不需要为代码 restart**。
- `check_reload_timer.py`：内存 832 == 磁盘 832 → **已同步**；下次自动重载 12:05:12（在 64 分钟内）。

⇒ **本轮全程未对 proxy 做过任何 restart**，未打断姊妹 KB 的探针窗口。

---

## 六、e2e 探针（12/12 全 200）

| 查询 | 4 次耗时 | 状态 |
|---|---|---|
| `C1102 控制器 通讯接口 有哪些` | 74.0 / 51.1 / 69.9 / 43.1s | 4/4 = 200 |
| `冲压工艺 手册 参数设置` | 62.7 / 48.1 / 78.7 / 76.6s | 4/4 = 200 |
| `示教器 操作手册 功能说明` | 52.5 / 95.5 / 118.7 / 103.2s | 4/4 = 200 |

- 客户端 timeout = **1860s**（> proxy 上游 1800s），无 000 / exit 28。
- **HTTP 502 = 0、HTTP 500 = 0** → **连续第 16 天** 502 计数为 0（§陷阱 22 的 timeout 对齐修复持续有效）。
- 日志文件 `/tmp/e2e-open-2026-11-21.log`（带 KB 名后缀，§陷阱 42）→ 本轮与姊妹 KB **无互相覆盖**。

---

## 七、引用链接实网探测（陷阱 39 / 43 同族，本轮独立验证本库）

姊妹 KB 11-21 发现**上游把「URL 形态」又放宽了**（裸路径与 `.html` 后缀**同时 200**），
并写入共享文件**陷阱 43**（两库 sha1 一致 = `8eb2251cc9945ba0752f1ef9f2e5ad12ecf332a0`，
43 sections，结构自检 OK）。

**本轮对本库（`inexbot-open` / open.inexbot.com）独立做实网探测**（30 条**真实 index 条目**随机抽样，
非手拼 URL —— 手拼会误判，见陷阱 43）：

| 形态 | 结果 |
|---|---|
| **裸路径**（本库 proxy 实际输出的形态） | **30/30 = 200** ✅ |
| 强制加 `.html` 后缀 | 26/30（4 条 404 —— 目录页等非 `.html` 路由） |
| 本库 index 里的 `url_suffix` 字段 | **0 条存在**（本库 crawler 不写这个字段） |

⇒ **本轮的 `url_suffix_mode = "none"`（proxy 按 KB 分派）依然正确**：
本库上游用**裸路径路由**，proxy 输出的裸路径 **30/30 全 200**，用户点得到链接。
⇒ 姊妹 KB 的 `url_suffix = "html"` 是**针对 doc.inexbot.com 的**分派，**不适用于本库**。
⇒ **本轮不改 proxy 代码**（陷阱 43 的处置原则：兼容层是零成本保险，不因「当前形态能用」就删）。

**本轮收尾时把这条一次性探针固化成常驻脚本**（本库此前**没有**这个脚本，
姊妹 KB 有 ⇒ 照 SKILL.md 的「修 bug 前先看姊妹 KB 是否已修」规则移植）：

| 新增 | 作用 |
|---|---|
| `scripts/check_citation_links.py` | 引用链接实网可达性 + `--probe-both-forms` 双形态探测（按**本库** URL 语义移植） |
| `references/upstream-url-form-drift.md` | 本库视角的 URL 形态漂移专题（姊妹的同名文件写的是 doc 侧「收紧」状态，**对本库不适用**） |

⇒ **下轮 cron 起，引用链接实网检查是标准的第 6c 步**（不再需要手写一次性探针）。

---

## 八、其它确认

- **SKILL.md 体积**：**84,121 字符 / 132,792 字节 / 2080 行**（写快照前）→ **未顶破 `skill_manage patch` 的 100,000 字符上限**（§陷阱 41 的瘦身手术仍然有效，无需再次瘦身）。
- **姊妹库工作树**：仅 `?? scripts/_tmp_url_suffix_stats.py`（姊妹自己的临时文件）→ **不代提交**，仅记录。
- **共享文件同步**：本轮姊妹与本库最终 sha1 一致（`8eb2251cc9945ba0752f1ef9f2e5ad12ecf332a0`，43 sections）→ **无需 `cp`、无需跑合并脚本**（§陷阱 23 / §陷阱 37）。

---

## 九、遗留

- **本库**：无。
- **姊妹 KB**：`scripts/_tmp_url_suffix_stats.py` 未跟踪临时文件 —— 属它自己 cron 的职责，本库不代提交。
