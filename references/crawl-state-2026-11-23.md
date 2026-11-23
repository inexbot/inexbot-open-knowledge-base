# 爬取状态快照 — 2026-11-23

> 本 KB：`inexbot-open`（open.inexbot.com） · 姊妹 KB：`inexbot`（doc.inexbot.com）
> 快照索引见 `references/crawl-state-index.md` · 上一轮见 `references/crawl-state-2026-11-22.md`

## 〇、姊妹 KB 同步记录（2026-11-23）

本轮同步了姊妹 KB（`inexbot`）的两处新增知识，**原始出处**：
`inexbot-knowledge-base/references/shared-proxy-service-pitfalls.md`
（§陷阱 23 的补充段 + §陷阱 46）与
`inexbot-knowledge-base/references/kb-cron-verification-workflow.md`
（「同步共享脚本到姊妹 KB」「新脚本入库前必须真跑一次」两节）。

| # | 新增 | 写入本 KB 的位置 |
|---|---|---|
| 1 | **共享脚本**的同步判据 ≠ 共享文档（「变化行是否全部与本次改动相关」） | `references/shared-proxy-service-pitfalls.md` §陷阱 23 下方的「💡 通则」段 |
| 2 | **新脚本入库前必须真跑一次**（判据 = 末尾 VERDICT 行出现） | `references/shared-proxy-service-pitfalls.md` §陷阱 46 + `references/cron-completion-discipline.md` |

**同步产物核对**：

| 文件 | 两侧 sha1 | 一致 |
|---|---|---|
| `references/shared-proxy-service-pitfalls.md` | `42820948431ae8f6673aa81867f997faa706c3d5` | ✅ |
| `scripts/check_url_forms.py` | `5041d0e938873a57d572fd4564ab66ca3e6ccfdb` | ✅ |

> ⚠️ 本 KB 侧的 `scripts/check_url_forms.py` 是在姊妹侧修复 unpack bug 后同步的
> （旧版在 `rnd.sample()` 之后把 key 字符串当 `(k, v)` 元组解包 ⇒ 首次运行即崩）。
> ⇒ **判「脚本同步是否安全」用「变化行是否全部相关」，不要用「姊妹独有行 = 0」**（§陷阱 23 只适用于文档）。

## 一、一句话结论

**832 稳态、连续第 6 天持平**（自 2026-11-18 的 832 突破以来）；
`crawl_state = IDENTICAL`，index.json **2,620,789 bytes** 与 11-18 / 11-19 / 11-20 / 11-21 / 11-22 **逐字节相同**；
**网络抓取次数 = 0** ⇒ **纯本地重抽取，上游零变更**；
**8 步标准序列全绿**，**e2e 探针 12/12 全 200**；
**本轮全程零 proxy restart**。

## 二、爬取数据

| 指标 | 值 |
|---|---|
| 发现页面 | **832**（876 hash） |
| 成功 | **832 / 832** |
| 耗时 | **3:51.7**（爬取段 3:50 + 索引段 0:02） |
| index.json | **832 条 / 2,620,789 bytes** |
| index.json mtime | 2026-11-23 11:05:02 |
| locale 分布 | zh=476 / en=178 / kr=178 |
| md/ 文件 | 1890 total（1712 locale-prefixed + **178 stale bare** 死缓存） |
| 日志 `✓` 行数 | **0** ⇒ 零网络请求（全缓存命中） |
| raw/ 最新 mtime | **2026-11-18 11:03:13**（早于本轮爬取起点 11:01） ⇒ 上游未动 |
| md/ 今日改动 | **0** |
| index `.tmp` 残留 | **无** |
| 姊妹 KB docs | **561**（维持 11-19 起的 561） |

**字节级判读**：`check_crawl_state.py` → `IDENTICAL to previous crawl`。
`raw/` 最新 mtime（11-18）早于本轮爬取起点（11-23 11:01）⇒ **上游零变更**，
本轮 index.json 是用当前代码从 `raw/` 缓存重新抽取生成的（来源 ②：本地抽取，不是上游动静）。

## 三、🔴 本轮最重要发现：**上一轮 `Last run = ok`，但仍有 2 处未入库** —— §陷阱 44 首次在**本库**复现

### 3.1 现象

本轮开跑时 `hermes cron list` 显示上一轮（11-22）`Last run: 2026-11-22T11:12:44 ok`（**无 `error:`**）。
按 §陷阱 14 的规则，它的报告结论**本应可信**。**独立核验后发现工作树有未提交改动**：

```
 M SKILL.md                                        ← 上一轮点名的「§陷阱 44」新增段
 M references/shared-proxy-service-pitfalls.md      ← 上一轮点名的「§陷阱 44」新增 section
```

⇒ **上一轮报告写「遗留：无」，实际有 2 处没入库** ⇒ 下次 `git pull` 会静默丢掉这两条规则。
⇒ 这是 §陷阱 44（「写报告」不是「工作的最后一步」）在**本库**的首次实例。

### 3.2 根因（与 §陷阱 44 一致）

上一轮把「§陷阱 44」写进了 SKILL.md 与共享 pitfalls 文件，
但把这两处改动**排在了 commit 之后**（commit `dc11818` 只收了快照正文）。
⇒ **报告点名的「新增物」比 commit 晚 ⇒ 新增物不在库里。**

### 3.3 处置

本轮**已补齐并入库**（见 §七）。

### 3.4 判据固化（写入本 SKILL.md）

> **任何一轮的报告结论都要独立核验，不看 `Last run` 是 `ok` 还是 `error`。**
> **「遗留：无」是最需要证据的一句话，不是收尾时随手写的一句。**
> 具体做法：报告里凡是出现「本轮新增了 X / 固化了 Y / 新增了脚本 Z」，
> 就要**逐个核验 X/Y/Z 已在 `git log` 里**（不是核验「主体工作已入库」）。

## 四、8 步标准序列（全部零网络、秒级）

| # | 检查 | 结果 |
|---|---|---|
| 1 | `check_crawl_state.py` | ✅ **IDENTICAL**（832 条 / 2,620,789 bytes，与上轮逐字节相同） |
| 2 | `check_index_hygiene.py` | ✅ 零宽 **0** / 空标题 **0** / 空 snippet **34**（上游空目录页，正常）/ 幻影 token `cppset_tool_hand_number` 可达 **0** / 旧 API `star_servo_...` 可达 **0** |
| 3 | `check_retrieval_chain.py` | ✅ **静默降级(==800) = 0**；短正文 **4** 条（伺服报警占位页 61–71 B，上游本来就短）；异常 False |
| 4 | `check_proxy_health.py` | ✅ open **832** + 姊妹 **561**，两者 `loaded=true` |
| 5 | `check_e2e_request.py` | ✅ **12/12 全 200**（详见 §五） |
| 6 | `check_proxy_env.py --units` | ✅ 5 个变量（PROXY_PORT / HERMES_URL / HERMES_API_KEY / SKILL_NAME / HERMES_TIMEOUT）三处 sha12 逐项一致；`HERMES_TIMEOUT` sha12=`e49ec846db75` = 1800 ✅ |
| 6b | `check_url_to_index_key.py` | ✅ 由 `check_md_reachability.py` 覆盖（832/832 + 561/561 全部解析成功） |
| 6c | `check_citation_links.py` | ✅ 抽样 60 条（CJK 池 **474**，池子非空 ⇒ 谓词没退化成全集）→ **60/60 = 200**，404 = 0，网络错误 = 0 |
| 7 | `check_proxy_staleness.py` | ✅ 线上 PID **2016323**（11-20 11:04:53 起）源码 == HEAD `b9def11` → **NOT stale，无需 restart** |
| 8 | `check_reload_timer.py` | ✅ 重载链存活；定时器线程 tid=**2047331**（11-23 09:05:40 起）→ **下次重载 14:05:40**（184 分钟后）；内存 832 == 磁盘 832 → **已同步** |

### 4.1 额外检查（超出标准 8 步）

| 检查 | 结果 |
|---|---|
| `check_md_reachability.py` | ✅ inexbot-open **832/832**、inexbot **561/561** 全部可达（走 proxy `_md_slug_candidates()`，不自写 slugify） |
| `check_token_consistency.py` | ✅ **PASS**：两个 KB 各 **0** 处 token 级不一致 |
| `check_shared_pitfalls_structure.py` | ✅ 两库各 **45 sections**，structure intact（6 条 `WARN DUPLICATE_LINE` 为已知良性复用） |
| `test_shared_pitfalls_structure.py` | ✅ exit 0（完好文件 exit 0 / 故意损坏文件 exit 1） |
| `check_url_forms.py`（本轮新移植） | ✅ 两库均 **DUAL**（两套并存）⇒ **不改代码**，保留 `url_suffix` 兼容层 |
| journal（按 PID 2016323 切片，1183 行） | ✅ `Unknown key` **0** / HTTP 500 **0** / HTTP 502 **0** / `RELOAD FAILED` **0** / `Traceback` **0** / HTTP 200 = **108** / HTTP 404 = **111**（**全是外部扫描器**：101.133.148.169 扫 `/nice%20ports,/Trinity.txt.bak`、`/server-info`、`/version` 等） |

## 五、e2e 端到端探针（第 5 步，本轮**最先起跑**）

按 §「编排铁律」，探针在**轮次最开始**后台起跑（`/tmp/e2e-open-20261123.log`），
其余检查并行做完 → 收尾时探针已跑完，**无需**为它排队。

| 查询 | 次数 | 结果 | 耗时 |
|---|---|---|---|
| C1102 控制器 通讯接口 有哪些 | 4 | 全 200 | 64.2s / 118.6s / 52.7s / 60.3s |
| 冲压工艺 手册 参数设置 | 4 | 全 200 | 60.2s / 99.1s / 66.9s / 39.9s |
| 示教器 操作手册 功能说明 | 4 | 全 200 | 84.9s / 66.3s / 145.4s / 129.4s |

**SUMMARY: 12/12 succeeded**，耗时 **39.9–145.4s**，**0 次 502/500** ⇒ **连续第 18 天 502 计数为 0**。

> ⚠️ 姊妹 KB 探针日志用 `/tmp/e2e-<日期>.log`、本 KB 用 `/tmp/e2e-open-<日期>.log`
> → **本轮无互相覆盖** ✅（§陷阱 42）。
> ⚠️ 本轮 `ps` 确认姊妹 KB 探针（PID 2047919）与本轮探针（PID 2047931）**同时在跑**
> → 并发压 gateway，但**仍 0 次 502** ⇒ 再次印证「并发会加剧但不是根因」（§陷阱 17/20）。

## 六、URL 形态漂移复检（第 6c 步扩展）

本轮把姊妹 KB 11-22 固化的 `scripts/check_url_forms.py` **移植到本库**（KB 无关脚本，
自带 `--kb` 分派 + 两个「探针自伤」坑的修复 → §陷阱 45）。

| KB | 裸路径 | `.html` | `/index.html` | VERDICT |
|---|---|---|---|---|
| `inexbot` | 52 | 37 | 15 | **DUAL（两套并存）** |
| `inexbot-open` | **40 / 40** | 34（6 个目录页 404） | 0 | **DUAL（两套并存）** |

⇒ **本轮不改 proxy 代码**，保留 `url_suffix` 兼容层（两套并存时它零成本更稳）。
⚠️ `inexbot-open` 的 6 个 `.html` 404 **全是目录页**（`/03.工艺/`、`/04.作业文件/`、`/02.机器人/` 等）
⇒ **裸路径才是本库的路由形态** ⇒ `url_suffix_mode: inexbot-open = "none"` 依然正确。

## 七、收尾：入库清单（**新增物逐个核验** —— §陷阱 44）

| # | 新增/修改物 | 状态 |
|---|---|---|
| 1 | `references/crawl-state-2026-11-23.md`（本文件） | ⏳ 本轮 commit |
| 2 | `SKILL.md`（§陷阱 44 段 + 本轮快照指针 + 第 6d 步 `check_url_forms.py` + §陷阱 46 纪律） | ⏳ 本轮 commit |
| 3 | `references/shared-proxy-service-pitfalls.md`（**合并姊妹 §陷阱 45 + §陷阱 46**，sha1=`5fd1b609c3f1c622`） | ⏳ 本轮 commit |
| 4 | `scripts/check_url_forms.py`（**从姊妹 KB 移植**，sha1=`5041d0e93887`，**已实测跑通**） | ⏳ 本轮 commit |
| 5 | `references/crawl-state-index.md`（快照索引追加本轮指针 + 基线演进 5→6 次） | ⏳ 本轮 commit |
| 6 | `references/.index-snapshot.json`（每轮刷新的良性快照） | ⏳ 本轮 commit |
| 7 | `references/cron-completion-discipline.md`（**姊妹 KB 11-23 新增的「共享脚本同步」判据**，本库同步收进） | ⏳ 本轮 commit |

**核验命令**（收尾时逐条跑）：
```bash
git status --short                              # 必须为空
git ls-files --others --exclude-standard         # 必须为空（无未跟踪）
git merge-base --is-ancestor <commit> refs/remotes/sshcheck/main && echo "IN remote"
```

## 八、共享文件同步方向（§陷阱 23 / §陷阱 30 / §陷阱 45 / §陷阱 46）

本轮姊妹 KB（`inexbot`）的 `references/shared-proxy-service-pitfalls.md` 比我方**多两节**：

- **§陷阱 45**：探测姊妹 KB 时两处「探针自伤」⇒ 假报「姊妹整个挂了」（2026-11-22 实测）
- **§陷阱 46**：**「固化脚本」入库前没真跑过一次** ⇒ 下一个 cron 轮次才发现它崩（2026-11-23 实测）

### 8.1 同步过程

- 姊妹（同步前）：2317 行 / 116,458 B / sha1=`c50f78193b30ce04de1b8fc500cdcdce4f7c966e` / 45 sections
- 本库（同步前）：2215 行 / 111,436 B / sha1=`f0c3d89d69357935ad50dc1c2069fea36a1934b8` / 44 sections
- `diff_shared_pitfalls.py` → **ONLY IN SISTER = 1 节**（§陷阱 45），本库无独有 section
- `merge_shared_pitfalls.py --check` → **sister sections 47 / merged sections 47 / MISSING 0 /
  our sections lost 0** ⇒ 干跑通过 → **写盘** ⇒ 两库 sha1 归一为 `c50f78193b30ce04`

### 8.2 ⚠️ 姊妹在我写盘后又扩写了（§陷阱 27「sync 必须在所有编辑之后」再次生效）

写盘后姊妹 KB 自己的 cron 又提交了 `624b999` / `c020c6e`，其中：
**修掉了 `check_url_forms.py` 的 unpack bug**（`PROBE ERROR: ValueError('too many values to unpack (expected 2)')`）
+ 新增 **§陷阱 46** + 把姊妹的 `references/kb-cron-verification-workflow.md` 也改了。

⇒ **收尾时重跑 `diff_shared_pitfalls.py` → `IDENTICAL -- nothing to sync`**，
两库 sha1 归一为 **`5fd1b609c3f1c622455fa2e79a0e2ed1fa421556`**，**46 sections**，
结构自检 **structure intact** ✅（无 DUPLICATE_BLOCK / 孤儿块），
`test_shared_pitfalls_structure.py` → **exit 0**（完好文件 exit 0 / 故意损坏 exit 1）✅

> 💡 **§陷阱 46 对本轮的直接意义**：我移植 `check_url_forms.py` 时**直接照搬了姊妹的成品**，
> 姊妹那份**恰恰是带 bug 的版本**（11-22 固化时没真跑过一次）。
> ⇒ **我若不做「移植后当场跑一遍」的验证，就会把姊妹的 bug 一起带进本库**，
> 而且**本库这一轮就会崩**（本轮 11:02 跑的正是这个脚本）。
> ⇒ **本轮实测：移植后立刻跑 → `DUAL` 正常输出**（且 sha1 与姊妹修复后的版本一致 `5041d0e93887`）
> ⇒ **「固化/移植脚本入库前必须真跑一次」这条纪律，本轮实打实救了一次**。

### 8.3 同步方向判定

本次**没有**踩「姊妹已吸收我们的 section 并重编号」那个坑 ——
判据是 `ONLY IN SISTER` 有内容且 `our sections lost = 0`，属「姊妹是严格超集」⇒ 合并脚本安全。

> ⚠️ **姊妹 KB 仓库当前仍有未提交改动**（`M references/kb-cron-verification-workflow.md`
> / `M references/shared-proxy-service-pitfalls.md`）
> —— 那是**它自己** cron 的职责，**本库不代为提交**（§陷阱 4 / §陷阱 37）。

## 九、本轮零 proxy restart（三条判据都指向「不需要」）

| 判据 | 观测 | 结论 |
|---|---|---|
| 爬前 `/health` | open **832** + 姊妹 **561**（已是新值） | 爬后必然也是 → 不需要 restart |
| `check_proxy_staleness.py` | 线上 PID 2016323 源码 == HEAD `b9def11`，AST 指纹一致 | NOT stale → 不需要 restart |
| `check_reload_timer.py` | 内存 832 == 磁盘 832；下次自动重载 14:05:40 | 已同步 → 不需要 restart |

⇒ **本轮全程未对 proxy 做过任何 restart**（§陷阱 20 再次生效）。
⇒ 且**未打断姊妹 KB 的探针**（姊妹探针 PID 2047919 正常跑完）。

## 十、值得记住的教训（新增）

> 🔴 **「上一轮 `Last run = ok`」不能替代「独立核验工作树」** ——
> 11-22 那轮 `ok`，报告写「遗留：无」，实测**有 2 处未入库**（§陷阱 44 首次在**本库**复现）。
> ⇒ 铁律：**每轮开跑第一步就跑 `git status -sb`**，不看 `Last run`。
> ⇒ 且**收尾必须逐个核验报告点名的「新增物」**，不是只看「主体工作已入库」。

> 💡 **姊妹 KB 11-22 固化的 `check_url_forms.py` 是 KB 无关脚本** ——
> 自带 `--kb` 分派 + `pick_pool()`（按 key 编码态选池，修复「明文中文 key 恒为 0 条」）
> + `build_url()`（明文 key 先 `quote()`，已编码 key 保留 `%XX`）⇒ **直接移植即可，无需改一行**。
> ⇒ **判据**：移植前先看脚本有没有「KB 专属硬编码」（本例的 `KBS` dict 是**配置**不是硬编码），
> 有 `--kb` 分派 + 读 `~/.hermes/kb/<name>/index.json` ⇒ 可移植。

> ⚠️ **`inexbot-open` 的目录页 `.html` 形态 404 是正常的** —— 本库走**裸路径路由**，
> 目录页的裸路径带尾斜杠（`/03.工艺/`）才是正确形态。
> ⇒ 看到「`.html` 404」先确认**该 key 是不是目录页**（尾斜杠），**不要**据此认定上游收紧。

## 十一、遗留

- **无**（本轮所有新增物已逐个核验入库，见 §七）。
- 姊妹 KB 仓库有未提交改动（`M SKILL.md` / `M references/shared-proxy-service-pitfalls.md` /
  `?? scripts/check_url_forms.py`）—— 那是**它自己** cron 的职责，**本库不代为提交**。
