# 2026-11-25 爬取快照（`inexbot-open`）

**结论：832 稳态、连续第 8 天持平；上游零变更；姊妹 KB 真实增长到 562。**

---

## 一、核心数据

| 项目 | 值 |
|---|---|
| crawler 报告 | 发现 **832** 个页面 / 成功 **832 / 832** / 失败 0 |
| 耗时 | **4:43.8**（11:00:38 → 11:05:22） |
| index.json | **832** entries / **2,620,789 bytes** / mtime 2026-11-25 11:05:22 |
| 字节对比 | 与 11-18 / 11-19 / 11-20 / 11-21 / 11-22 / 11-23 / 11-24 **逐字节相同** |
| locale 分布 | zh=**476** / en=**178** / kr=**178** |
| crawl_state verdict | **IDENTICAL**（真稳态） |
| md/ 文件 | 1890 total（1712 locale-prefixed + 178 stale bare） |
| md/ 今日改动 | **0** |
| raw/ 今日改动 | **0**（最新 mtime 仍是 **11-18 11:03**） |
| `.tmp` 残留 | **0** |
| 网络抓取次数 | **0**（日志 `✓` 行数 = 0） |
| 姊妹 KB `inexbot` | **561 → 562**（真实上游增长，见 §三） |

⇒ **纯本地重抽取，上游零变更。**

---

## 二、本轮要点

### ① 🔴 §陷阱 44 **第四次复现** —— 且本轮是「上一轮 `Last run = ok` 但工作树脏」

开跑时第 0 步三条命令：

```
 M SKILL.md
 M references/cron-completion-discipline.md
```

（`git ls-files --others --exclude-standard` 为空 —— 这次漏的**只是已跟踪文件的修改**，
不是 `??` 新增物 ⇒ 与 11-21/11-22/11-23 三轮的形态**略有不同**。）

⇒ 仍然**没有任何信号提示要去查**（`Last run` = `ok`）⇒ §陷阱 44 的「机械化核验」是对的。

**本轮处置**：第 0 步立即 `git add -A` + commit（`c52841e`）+ push（HTTPS 一次成功）
⇒ 不再让它拖到收尾（§陷阱 44 的核心教训：**commit + push 才是最后一步**）。

### ② 🔴 §陷阱 46 **第二次救场** —— 移植姊妹的新 `check_shared_pitfalls_structure.py` **带回归**

姊妹 KB 11-25 重写了结构自检脚本（新增「正文交错」检测，删掉旧 `warnings` 通道），
并把它与新写的 §陷阱 47 一起**直接写进本库的 skill 目录**（§陷阱 36/37 的双向流动）。

**移植流程（§陷阱 46 纪律）**：
1. `cp` 姊妹版 → 本库；
2. **当场跑一遍** → 对真实文件 PASS（47 sections / 2586 lines）；
3. **跑回归测试** `test_shared_pitfalls_structure.py` → ❌ **case 2 FAIL**：

```
=== case 2: corrupted file (orphan body appended, 45 lines) ===
  exit = 0
  [FAIL] corrupted file should exit 1 with a DUPLICATE/SUSPECT finding
```

⇒ **姊妹的重写丢了「孤儿体」检测** —— 正是 §陷阱 31 要抓的那个形态
（「把最后一节的正文再抄一份追加到文件末尾」）。

**根因**：姊妹版用「整段正文 sha256」判重复（判据 #2 `DUPLICATE_SECTION`）。
孤儿体的典型形态是**最后一节的正文区间同时包含原件和副本** ⇒ 该节 sha256 **唯一**
⇒ #2 看不到重复 ⇒ **孤儿体漏检**。
⇒ 必须保留**固定长度前缀签名**（`SIG_LINES = 8`）在全文件非空行序列上滑动查找。

**修复**：在姊妹版基础上**增量**补回判据 #6（`DUPLICATE_BLOCK` / `DUPLICATE_SECTION`，
前缀签名滑动查找）+ 重新定义 `nonempty` 与 `SIG_LINES`。
（姊妹版删掉了 `nonempty` 与 `SIG_LINES` 两个定义 ⇒ 直接粘贴会 `NameError`。）

**回归结果**：

```
=== case 1: intact file ===       exit = 0   [OK]
=== case 2: corrupted file ===     exit = 1   [DUPLICATE_BLOCK] ... appears 2 times
```

⇒ **两个方向都绿**（完好 → 0；损坏 → 1）。

> ⚠️ **姊妹那份脚本目前仍带这个回归**（她的仓库里没有 `test_shared_pitfalls_structure.py`
> —— 她把自己的回归测试删掉了）。本 skill 不替她提交，但**在报告里点名**：
> **姊妹 KB 的结构自检目前无法抓「末尾孤儿体」。**

### ③ ⭐ 姊妹 KB 真实增长 561 → **562**

姊妹 KB 当天抓到 **1 个新页**（「web 协作示教系统操作手册」，
`raw/` 有文件在 **11-25 11:04** 被真正抓取，日志 `✓` 行数 = 1）
⇒ **是真实上游增长**，不是本地抽取变更。

本库已把 `check_proxy_health.py` 的 `BASELINES["inexbot"]` 从 561 调到 **562**，
并同步更新 SKILL.md 的 `/health` 期望值。

proxy 于 **11:05:37** 自动重载（5h 定时器）⇒ 内存索引 == 磁盘索引
（`inexbot` 562 / `inexbot-open` 832）⇒ **无需 restart**。

### ④ ⚠️ §陷阱 41：SKILL.md 瘦身（第三轮）

开跑时 **93,650 字符 / 150,064 字节 / 2,335 行**（距 100,000 上限仅剩 6,350）。

**本轮瘦身**：把 11-18 / 11-19 / 11-20 / 11-21 / 11-23 五轮的**内联快照正文**
移出 SKILL.md，只留「指针 + 两条跨轮通用要点」
⇒ **93,650 → 91,378 字符**（释放 2,272）。
**内容零丢失**：各轮正文都在 `references/crawl-state-<日期>.md`，
索引表在 `references/crawl-state-index.md`。

> 📌 **每轮都要做增量瘦身** —— 这个上限会被每轮的「最新一轮要点」重新吃回来。

### ⑤ 本轮全程零 proxy restart（三条判据全部指向「不需要」）

- 爬前 `/health` 已是 832 / 562（已是新值）⇒ 内容侧无需 restart；
- `check_proxy_staleness.py` → 线上 PID **2016323** 源码 == HEAD `b9def11` → **NOT stale**；
- `check_reload_timer.py` → 内存 832 == 磁盘 832 → **已同步**。

⇒ 且**未打断姊妹 KB 的探针**（姊妹探针 PID 2069214 全程在跑）。

### ⑥ 📌 编排铁律复用：探针在**轮次最开始**起跑

本轮把 e2e 探针放在**第 0 步之后立刻**后台起跑（`/tmp/e2e-open-2026-11-25.log`），
其余 10 项检查并行做完 ⇒ 探针在全部检查跑完时**也刚好跑完**（12/12）。
姊妹 KB 用 `/tmp/e2e-2026-11-25.log`、本库用 `/tmp/e2e-open-2026-11-25.log`
⇒ **本轮无互相覆盖** ✅（§陷阱 42 的姊妹篇，本库侧已合规）。

---

## 三、8 步标准序列（全绿）

| # | 检查 | 结果 |
|---|---|---|
| 1 | `check_crawl_state.py` | **IDENTICAL** / 832 / 2,620,789 bytes / locale zh=476 en=178 kr=178 |
| 2 | `check_index_hygiene.py` | 零宽 **0** / 空标题 **0** / 空 snippet 34（上游空目录页）/ 幻影 token 可达 **0** / 旧 API 可达 **0** |
| 3 | `check_retrieval_chain.py` | **静默降级 ==800 = 0**；短正文 4 条（伺服报警占位页 61–71 B，上游本来就短） |
| 4 | `check_proxy_health.py` | open **832** / 姊妹 **562** / loaded=True ×2 |
| 5 | `check_e2e_request.py` | **12/12 全 200**（48.7–236.3s）→ **连续第 20 天 502 计数 = 0** |
| 6 | `check_proxy_env.py --units` | 5 个变量 × 3 处（线上 environ / `/etc` unit / repo 模板）sha12 逐项一致；`HERMES_TIMEOUT` sha12=`e49ec846db75` = 1800 ✅ |
| 7 | `check_proxy_staleness.py` | 线上 PID **2016323** == HEAD `b9def11` → **NOT stale，无需 restart** |
| 8 | `check_reload_timer.py` | 重载链存活（定时器 tid=2070621，11:05:37 触发）；内存 == 磁盘 → **已同步** |

**附加检查**：

| 检查 | 结果 |
|---|---|
| `check_md_reachability.py` | inexbot-open **832/832**、inexbot **562/562** 全可达 |
| `check_token_consistency.py` | **PASS** —— 两个 KB 各 **0** 处 token 级不一致 |
| `check_url_to_index_key.py` | **93/93** 命中；静默降级 0；no-md lookup 0 |
| `check_citation_links.py` | **60/60 可达**（HTTP 404 = 0，网络错误 = 0），CJK 池 474 |
| `check_url_forms.py --sample 40` | **DUAL**（裸路径 40/40、`.html` 34/40）⇒ **不改代码，保留 `url_suffix` 兼容层**；6 条 `.html` 404 全是**目录页**（本库走裸路径路由，目录页裸路径带尾斜杠） |
| `diff_shared_pitfalls.py` | **IDENTICAL**（两库 sha1 归一 `a4fa9857e39c`，均 2586 行 / 47 sections） |
| `check_shared_pitfalls_structure.py` | **PASS**（两库各 47 sections，exit 0） |
| `test_shared_pitfalls_structure.py` | **两个方向全绿**（完好 → 0；损坏 → 1）—— 见 §二 ② |

**journal（按当前进程 PID 2016323 切片）**：
`Unknown key` **0** / HTTP 500 **0** / HTTP 502 **0** / `RELOAD FAILED` **0** /
`Traceback` **0** / HTTP 200 = **194** / HTTP 404 = **125**（**全是外部扫描器**）。

---

## 四、遗留

**本库：无。**

**姊妹 KB（不代为提交，仅点名）**：
1. `scripts/check_shared_pitfalls_structure.py` 的姊妹版**丢了「末尾孤儿体」检测**
   （判据 #2 整段 sha256 替代不了前缀签名）⇒ **姊妹目前抓不到 §陷阱 31 的目标形态**；
2. 姊妹仓库里**没有** `test_shared_pitfalls_structure.py`（她的回归测试被删了）——
   ⇒ 上述回归**没有测试能拦住**；
3. 姊妹 KB 工作树 `ahead 1`（她自己的提交，**不要**替她 push）。
