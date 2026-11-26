# 爬取快照：2026-11-26

## 一、爬取结果

| 项 | 值 |
|---|---|
| 爬取 | **832 / 832 成功**，失败 0，耗时 **3m59.8s** |
| 页面总数 | **832**（与 11-18 → 11-25 **连续第 9 次持平**） |
| 网络抓取次数 | **0**（日志 `✓` 行数 = 0）⇒ **上游零变更**，纯本地重抽取 |
| index.json | **2,620,789 bytes**，与 11-18 → 11-25 **逐字节相同** |
| locale 分布 | zh=**476** / en=**178** / kr=**178**（与上轮完全一致） |
| md / raw 今日改动 | **0 / 0**（全缓存命中）；`.tmp` 残留 **0** |
| crawl_state verdict | **IDENTICAL**（内容逐字节未变） |
| 姊妹 KB `inexbot` | **562**（与 11-25 持平；姊妹 `raw/` 今日改动 0） |

> ⚠️ **判读**：`raw/` 最新 mtime 仍是 **11-18 11:03**（早于本次爬取起点 11:01:15），
> 且日志 `✓` 行数 = 0 ⇒ **上游本轮没有任何新页面/正文变化**，
> 832 是真稳态（docs 数持平 + 字节数完全相同 = 逐字节一致）。

## 二、验证闭环（全部通过）

| 检查 | 结果 |
|---|---|
| `check_crawl_state.py` | **IDENTICAL**（832 docs / 2,620,789 bytes / 与 11-25 逐字节相同） |
| `check_index_hygiene.py` | 零宽 **0**、空标题 **0**、空 snippet **34**（上游空目录页，正常）；幻影 token `cppset_tool_hand_number` 可达 **0**；旧 API `star_servo_...` 可达 **0** |
| `check_retrieval_chain.py` | **静默降级(==800) = 0**、异常 False；短正文 4 条 = 伺服报警占位页（61–71 B，属上游本来就短）；全文命中 4000 字上限多条 |
| `check_proxy_health.py` | `inexbot-open` **832**（基线 832）+ `inexbot` **562**（基线 562），均 `loaded=True` |
| `check_proxy_env.py --units` | 5 个变量三处 sha12 **逐项一致**；`HERMES_TIMEOUT` sha12=`e49ec846db75`（=1800）✅ |
| `check_proxy_staleness.py` | 线上 PID **2016323**（11-20 11:04:53 起）源码 == HEAD `b9def11` → **NOT stale，无需 restart** |
| `check_reload_timer.py` | 重载链**存活**（tid=2079554，07:06:20 触发）；内存 832 == 磁盘 832 → **已同步**；下次自动重载 12:06:20 |
| `check_md_reachability.py` | **832/832**（本库）+ **562/562**（姊妹）全部可达，unresolved = 0 |
| `check_url_to_index_key.py` | **93/93** 命中；静默降级 0；no-md lookup 0 |
| `check_token_consistency.py` | 两库各 **0 处不一致** → PASS |
| `check_citation_links.py` | 抽样 **60/60 全 200**，404 = 0，网络错 0（cjk 池 474） |
| `check_url_forms.py` | **DUAL**（裸路径 + `.html` 并存）⇒ **不改代码**，保留 `url_suffix` 兼容层（§陷阱 43） |
| `check_shared_pitfalls_structure.py` | **PASS**（48 sections / 2647 行，无重复/孤儿/截断/交错） |
| `test_shared_pitfalls_structure.py` | **回归两个方向全绿**（完好文件 exit 0、损坏文件 exit 1） |
| 端到端探针 | **12/12 全 200**，耗时 **46.3–172.3s**，**0 次 500/502** → 连续第 **21** 天 502 = 0 |
| journal（按 PID 2016323 切片） | `Unknown key` **0** / HTTP 500 **0** / HTTP 502 **0** / `RELOAD FAILED` **0** / `Traceback` **0**；HTTP 200 = 208 / HTTP 404 = 131（**全是外部扫描器**） |
| 遗留进程/端口 | 无残留探针；8643(proxy) + 8642(gateway) 之外无监听 ✅ |

## 三、本轮的三件事

### ① 🔴 §陷阱 44 **第五次**在本库复现 —— 11-25 那轮被 429 打断，6 处未入库

11-25 的 `Last run` = **`error: RuntimeError: HTTP 429: 已达到 Token Plan 用量上限`**。
按 §陷阱 14 的规则，**它的报告正文里的「已提交」结论一律作废** ⇒ 本轮开局独立核验：

```
 M SKILL.md                                        ← 上一轮点名的「§陷阱 44」新增段
 M references/.index-snapshot.json
 M references/cron-completion-discipline.md
 M references/shared-proxy-service-pitfalls.md    ← 上一轮点名的「陷阱 48」新增 section
 M scripts/check_proxy_health.py                  ← BASELINES inexbot 561 → 562
 M scripts/check_shared_pitfalls_structure.py     ← 审计脚本重写
?? references/crawl-state-2026-11-25.md           ← 报告点名的「新增物」，从未 git add
```

⇒ **7 项全部补做**：`git add -A` → commit `a79b940` → push 一次成功 →
`merge-base --is-ancestor` = YES、`HEAD == REMOTE == a79b940967b1d2321d16c9d047b87cb461b99ca5`、
`git status --short` 与未跟踪清单**均空**。

> ⭐ **本次泄漏的机制与 §陷阱 44 的「新增物排在 commit 之后」完全吻合**：
> 11-25 那轮在**报告里点名**了 `crawl-state-2026-11-25.md`，
> 但**从未 `git add`** ⇒ 429 打断时它还躺在未跟踪区。
> ⇒ **本库已连续五轮（11-21 的 5 处 / 11-22 的 2 处 / 11-23 的 4 处 / 11-24 的 2 处 /
> 11-25 的 7 处）踩同一个坑** ⇒ 收尾一律 `git add -A` + `git ls-files --others` 必须为空。

### ② ⭐ 姊妹 KB 在本轮窗口内**吸收了我们的陷阱 48 + 审计脚本修复**（§陷阱 36/37 双向流动）

轮次中途实测：姊妹那份 `shared-proxy-service-pitfalls.md` 从 2586 行 / 49 sections
变成 **2647 行 / 50 sections**，与我们的 **sha1 完全一致**（`aab928a25714`）⇒
**她吸收的正是我们 11-25 轮末才写进去的「陷阱 48」**。
`check_shared_pitfalls_structure.py` 两库 **diff = 0 行**（她的 `8449319` commit
"adopt sister KB structure script with SIG_LINES orphan detection" 已同步我们的修复）。

⇒ **本轮 `diff_shared_pitfalls.py` 判定 IDENTICAL —— 无需任何同步动作**。
✅ **姊妹的回归测试也补上了**（`test_shared_pitfalls_structure.py` 在她仓库里存在，
且**两个方向全绿**）⇒ 姊妹 11-25 记录里「她删了测试文件」的状态已被她自己修复。

> 💡 **再次印证 §陷阱 44 第 5 点的结论**：共享文件是**双向流动**的 ——
> 「姊妹比我新」或「我比姊妹新」都只是**谁先落盘**的时序差异，
> 唯一判据仍是**独有行集合**（本轮实测：姊妹独有 **0** / 本 skill 独有 **0**）。

### ③ 本轮全程**零 proxy restart**

三条判据全部指向「不需要 restart」：
- **内容维度**：爬前 `/health` 已是 832 == 磁盘 832 ⇒ 爬后必然也是（proxy 5h 自动重载）；
- **代码维度**：`check_proxy_staleness.py` → 线上源码 == HEAD `b9def11`，**AST 指纹一致**；
- **重载维度**：`check_reload_timer.py` → 内存 == 磁盘，**已同步**。

⇒ 且**未打断姊妹 KB 的探针**（本轮姊妹 repo 领先 4 个 commit，她的 cron 同期在跑）。

## 四、提交与推送

| 仓库 | commit | push | 复核 |
|---|---|---|---|
| `inexbot-open-knowledge-base` | `a79b940`（补齐 11-25 的 7 处未入库） | HTTPS **一次成功**（`c52841e..a79b940`） | `merge-base --is-ancestor` = **YES**；`HEAD == REMOTE == a79b940967b1d2321d16c9d047b87cb461b99ca5`；`git status --short` 与未跟踪清单**均空** |
| `inexbot-knowledge-base`（姊妹） | 她自己的 `8449319` 等 4 个 commit | — | **她的职责，本 skill 不代提交**；她有 1 个未跟踪快照 `crawl-state-2026-11-26.md`（她自己的 cron 收尾） |
| `hermes-skill-proxy` | **未改动** | — | staleness 检查确认线上已是 HEAD，无需部署 |

## 五、遗留

**无。** 本库工作树干净、未跟踪清单为空、远端 == HEAD。
姊妹 KB 的未跟踪快照属于**她自己的** cron 收尾范围（按 §陷阱 13 / 姊妹仓库不代提交）。

## 六、基线更新

- `inexbot-open`：**832**（11-18 → 11-26 连续第 9 次持平；docs 数自 11-18 起 8 天零新增）
- `inexbot`（姊妹）：**562**（11-25 → 11-26 持平）
- `check_proxy_health.py` 的 `BASELINES`：`inexbot-open=832`、`inexbot=562` —— **与实际一致，无需调整**
