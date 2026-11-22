# 2026-11-22 爬取快照 — 832 稳态（连续第 5 天持平）

## 一、结论摘要

| 项 | 值 |
|---|---|
| crawl verdict | **IDENTICAL**（与 11-21 逐字节相同） |
| index.json | **832 entries, 2,620,789 bytes**（与 11-18 / 11-19 / 11-20 / 11-21 完全一致） |
| locale 分布 | zh=476 / en=178 / kr=178 |
| 抓取耗时 | **4:02.5**（实测 11:00:42 → 11:04:44） |
| 网络抓取次数 | **0**（日志 `✓` 行数 = 0，`raw/` 最新 mtime = 11-18 11:03） |
| 判定 | **纯本地重抽取，零网络请求 → 上游零变更** |
| 姊妹 KB inexbot | **561**（维持） |
| e2e 探针 | **12/12 全 200**（32.5–72.0s，**0 次 502/500** → 连续第 17 天 502 计数为 0） |

**832 是 11-18 打破 817 稳态后的新基线**，**连续第 5 天持平**（11-19 / 11-20 / 11-21 / 11-22 均 IDENTICAL）。

---

## 二、本轮与 11-21 的差异

- **唯一变化：无。** index.json 字节数完全相同（2,620,789 × 5 天）。
- `raw/` 最新 mtime = **2026-11-18 11:03**（早于本次爬取起点 11-22 11:00:42）
  → 本轮 832 页**全部命中缓存**，**一个页面都没重新抓**。
- md/ 今日改动 = **0** 个文件（与 IDENTICAL 判定自洽）。
- 无 `.tmp` 残留（原子写 `save_json()` 正常工作）。
- 爬取耗时 **4:02.5**（历史稳态带 3:00–4:42 内）→ 正常。
- crawler 日志：832/832 成功，索引完成 832 条。

---

## 三、轮次第 0 步：**11-21 那轮报告写「遗留：无」，但工作其实没入库 —— 本轮补齐**

`hermes cron list` 显示 11-21 的 `Last run` = `2026-11-21T11:19:01 ok`（**未带 `error:`**），
所以按 §陷阱 14 的规则，其报告结论**本应可信**。**但本轮独立核验发现它不可信**：

| 核验项 | 结果 |
|---|---|
| 本库 `git status -sb` | **有 5 处未提交**：`M SKILL.md` / `M references/crawl-state-2026-11-21.md` / `M references/shared-proxy-service-pitfalls.md` / `?? references/upstream-url-form-drift.md` / `?? scripts/check_citation_links.py` |
| `git log --oneline -1` | `6374927`（11-21 轮的 commit）—— 11-21 快照正文**已入库**，但**收尾新增的文件没入库** |
| 11-21 快照 §九「遗留」 | 写着「**本库**：无」—— **与磁盘事实矛盾** |

⇒ **11-21 那轮犯了「commit → push → 写报告」顺序的反面**：它先写了快照正文并 commit，
再**新增**了 `scripts/check_citation_links.py` 与 `references/upstream-url-form-drift.md`
（11-21 快照 §七 明确说「本轮收尾时把这条一次性探针固化成常驻脚本」），
但**这两个新文件从未被 `git add`** ⇒ 未入库 ⇒ **下次 `git pull` 会静默丢掉它们**。

🔴 **本轮补齐的内容**（已 commit + push，commit `2055270`）：

| 文件 | 状态 |
|---|---|
| `scripts/check_citation_links.py` | **`??` → 已入库**（241 行） |
| `references/upstream-url-form-drift.md` | **`??` → 已入库**（111 行） |
| `SKILL.md`（v1.35.0 → **v1.36.0** + 第 6c 步 + 429 核验判读表） | **`M` → 已入库** |
| `references/crawl-state-2026-11-21.md`（补 §七固化说明） | **`M` → 已入库** |
| `references/shared-proxy-service-pitfalls.md`（陷阱 43 姊妹互证注解） | **`M` → 已入库** |

⇒ **本轮新增一条教训（见 §九）**：**「写报告」不是「工作的最后一步」——
「最后一步」是「commit + push」。** 报告正文可以在 commit 之前写（它是产物），
但**报告里提到「本轮新增了 X」之后，X 必须先入库**。
11-21 把「固化脚本」写进了快照 §七，却没把脚本 `git add` ⇒ 快照与磁盘脱节。

---

## 四、8 步标准验证序列（全绿）

| # | 检查 | 结果 | 关键数据 |
|---|---|---|---|
| 1 | `check_crawl_state.py` | ✅ exit 0 | **IDENTICAL** / 832 / 2,620,789 B / zh=476 en=178 kr=178 |
| 2 | `check_index_hygiene.py` | ✅ exit 0 | 零宽 0、空标题 0、幻影 token 可达 0、旧 API 可达 0、空 snippet 34（上游空目录页） |
| 3 | `check_retrieval_chain.py` | ✅ exit 0 | **静默降级(==800) = 0**；短正文 4 条（61–71 B，伺服报警占位页，属上游本来就短） |
| 4 | `check_proxy_health.py` | ✅ exit 0 | open **832** / sister **561**，均 loaded=True |
| 5 | `check_e2e_request.py` | ✅ 12/12 | 见 §六 |
| 6 | `check_proxy_env.py --units` | ✅ exit 0 | 5 个变量在「线上 environ / /etc 部署版 / repo 模板」三处 sha12 逐项一致；`HERMES_TIMEOUT` sha12=`e49ec846db75` = 1800 ✅ |
| 6b | `check_url_to_index_key.py` | ✅ exit 0 | **93/93**；静默降级 0；no-md lookup 0 |
| 6c | `check_citation_links.py` | ✅ exit 0 | 抽样 60 条（CJK 池 474）→ **60/60 = 200**，404/410 = 0，网络错误 0 |
| 6c' | `check_citation_links.py --probe-both-forms` | ✅ exit 0 | 裸路径 **30/30 = 200**；带 `.html` 后缀 25/30（目录页等非 `.html` 路由）⇒ **仍走裸路径路由** |
| 7 | `check_proxy_staleness.py` | ✅ exit 0 | 线上 PID 2016323 源码 == HEAD `b9def11` → **NOT stale，无需 restart** |
| 8 | `check_reload_timer.py` | ✅ exit 0 | 重载链存活，定时器线程 tid=2037359（08:05:26 起），**下次重载 13:05:26**；内存 832 == 磁盘 832 → 已同步 |

**附加守卫**：
- `check_md_reachability.py` → ✅ open **832/832** + sister **561/561**
- `check_token_consistency.py` → ✅ **PASS**（两个 KB 各 0 处不一致）
- `check_shared_pitfalls_structure.py` → ✅ **OK**（两库各 43 sections，仅 WARN 级重复行，不计入退出码）
- `test_shared_pitfalls_structure.py` → ✅ 回归通过（完好文件 exit 0 / 孤儿体 exit 1）
- `diff_shared_pitfalls.py` → 43 sections **完全一致**，唯一差异 = 本库在陷阱 43 加了 2 行「姊妹互证」注解
  → 属**本库独有内容**，**不 cp 覆盖**（§陷阱 23「姊妹独有行 = 0 才可覆盖」）；本轮无需同步
- journal 按进程切片（PID 2016323，since 2026-11-20 11:04:53，814 行）：
  `Unknown key` **0** / HTTP 500 **0** / HTTP 502 **0** / `RELOAD FAILED` **0** /
  `Traceback` **0** / HTTP 200 = **69** / HTTP 404 = **97**（**全是外部扫描器**，非 KB 请求）

---

## 五、本轮零 proxy restart（§陷阱 20 再次生效）

- 爬前 `check_proxy_health.py` 已是 **832**（新值）→ 爬后必然也是 → **不需要为内容 restart**。
- `check_proxy_staleness.py`：线上 PID **2016323** 源码 == HEAD `b9def11` → 行为等价 → **不需要为代码 restart**。
- `check_reload_timer.py`：内存 832 == 磁盘 832 → **已同步**；下次自动重载 13:05:26（在 124 分钟内）。

⇒ **本轮全程未对 proxy 做过任何 restart**，未打断姊妹 KB 的探针窗口。

---

## 六、e2e 探针（12/12 全 200）

| 查询 | 4 次耗时 | 状态 |
|---|---|---|
| `C1102 控制器 通讯接口 有哪些` | 34.5 / 42.7 / 65.3 / 32.5s | 4/4 = 200 |
| `冲压工艺 手册 参数设置` | 72.0 / 60.6 / 50.5 / 59.1s | 4/4 = 200 |
| `示教器 操作手册 功能说明` | 46.6 / 60.2 / 57.1 / 57.1s | 4/4 = 200 |

- 客户端 timeout = **1860s**（> proxy 上游 1800s），无 000 / exit 28。
- **HTTP 502 = 0、HTTP 500 = 0** → **连续第 17 天** 502 计数为 0（§陷阱 22 的 timeout 对齐修复持续有效）。
- 日志文件 `/tmp/e2e-open-2026-11-22.log`（带 KB 名后缀，§陷阱 42）→ 本轮与姊妹 KB **无互相覆盖**
  （姊妹本轮用 `/tmp/e2e-inexbot-2026-11-22.log`，同样带库名后缀 ✅）。
- **本轮探针在轮次最开始就后台起跑**（§编排铁律），与全部离线检查并行 → 未撞工具调用上限。

---

## 七、引用链接实网探测（第 6c 步，11-21 新脚本首次按标准序列跑）

本轮是 `scripts/check_citation_links.py`（11-21 固化）**第一次作为标准第 6c 步**运行：

| 项目 | 结果 |
|---|---|
| 抽样 | **60 条**（CJK 池 474，**池子非空** ⇒ 谓词没退化成全集，§陷阱 26） |
| HTTP 200/3xx | **60** |
| HTTP 404/410 | **0** |
| 网络错误 | **0** |
| 双形态：裸路径 | **30/30 = 200** ✅ |
| 双形态：带 `.html` 后缀 | 25/30（目录页等非 `.html` 路由 404） |
| index 里的 `url_suffix` 字段 | **0 条存在**（本库 crawler 不写这个字段） |

⇒ **本库上游仍是裸路径路由**，proxy `url_suffix_mode: inexbot-open = "none"` **依然正确** → **本轮不改 proxy 代码**。

---

## 八、其它确认

- **SKILL.md 体积**：**88,441 字符 / 140,040 字节 / 2,176 行**（写快照前）
  → **未顶破 `skill_manage patch` 的 100,000 字符上限**（§陷阱 41 的瘦身手术仍然有效；距上限还有 11.5 KB 余量）。
- **姊妹库工作树**：`M SKILL.md` + `M references/upstream-url-suffix-routing.md`
  → 属**它自己** cron 的职责，本库**不代提交**，仅记录。
- **proxy 仓库**：干净，HEAD `b9def11`（`fix(proxy): support per-KB url suffix for citation links`）→ 与线上进程源码一致。

---

## 九、本轮新增教训（已写进 SKILL.md）

### 「写报告」不是「工作的最后一步」——**「最后一步」是「commit + push」**

11-21 那轮 `Last run` 是 **ok**（无 `error:`），按 §陷阱 14 的规则其报告结论本应可信，
**但它写的「遗留：无」与磁盘事实矛盾**：快照 §七 明明写了「本轮收尾时把这条一次性探针
固化成常驻脚本」（并列出 2 个新文件），而那两个文件**从未 `git add`**。

⇒ **根因不是「忘了 commit」，而是「把『收尾时再固化的东西』写进了报告，
却把固化动作排在了 commit 之后」。**

⇒ **判据（新增）**：**报告正文里凡是出现「本轮新增了 X / 本轮固化了 Y / 新增了脚本 Z」，
就必须在本轮结束前核验 X/Y/Z 已在 `git log` 里** ——
不是核验「本轮的主体工作已入库」，而是**核验报告点名的每一个新增物**。

⇒ **具体做法**：写报告正文时，把「新增物」列成一张表；
commit 之前用 `git status --short` 对着这张表逐行核（`??` = 没入库）。
**报告的最后一步永远是 `git commit` + `git push` + `git status` 复核。**

---

## 十、遗留

- **本库**：无（`git status -sb` 干净，仅 `M references/.index-snapshot.json`，属每轮刷新的良性快照）。
- **姊妹 KB**：`SKILL.md` / `references/upstream-url-suffix-routing.md` 有未提交改动 —— 属它自己 cron 的职责，本库不代提交。
- **git push 通道**：HTTPS(443) 本轮**故障**（`GnuTLS recv error (-110)` → 重试 `Failed to connect to github.com port 443 after 130476 ms`），
  socket 探针却报 **443 3/3 OK**（§陷阱 30 的「探针假绿」再现）→ 已切 **SSH 通道**推送成功
  （`git push git@github.com:inexbot/inexbot-open-knowledge-base.git main:main`，
  `6374927..2055270`），并用 `merge-base --is-ancestor` 核验 **IN remote: yes**。
