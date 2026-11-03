# 2026-11-03 爬取状态：799/558 连续第十五次持平（纯稳态）+ 定位 502 的**真正**成因

## 爬取本体：完全稳态，无任何异常

| 项目 | 结果 |
|---|---|
| 爬取页数 | **799 / 799**（0 失败） |
| 耗时 | **3:21.4**（稳态带 3:00–3:20 内） |
| index.json | **2,450,869 bytes** —— 与 10-29 / 10-30 / 10-31 / 11-01 / 11-02 **逐字节相同** |
| verdict | `IDENTICAL`（`check_crawl_state.py`） |
| 网络请求 | **0**（日志 `✓` 行 = 0；`raw/` 最新 mtime = 2026-10-23） |
| locale 拆分 | zh=443 / en=178 / kr=178 |
| md/ 今日重写 | **0 个**（`find -newermt` 无命中） |
| `.tmp` 残留 | 无（原子写正常） |
| 姊妹 KB | 558（11:04 落盘，同窗口并发爬取，本 KB 3:21 完成 → CPU 争抢影响 ~5%，与既往判断一致） |

上游**零变化**，连续第 15 次持平（自 2026-10-10 起 24 天零新增）。

> 📌 本轮起始 `ps` 确认姊妹 KB crawler 于 11:01 同窗口起跑；
> 本 KB 3:21 完成，比 11-02 的 3:31 **更快**。

## 验证序列（10-31 固化的 5 步）

| # | 检查 | 结果 |
|---|---|---|
| 1 | `check_crawl_state.py` | IDENTICAL，2,450,869 bytes ✅ |
| 2 | `check_index_hygiene.py` | 零宽字符 0 / 空标题 0 / 空 snippet 34 / 幻影 token 可达 0 / 旧 API 可达 0 ✅ |
| 3 | `check_retrieval_chain.py` | 静默降级(==800) **0**；短正文 4 条（伺服报警占位页 61–71 B，正常）✅ |
| 4 | `check_proxy_health.py` | inexbot-open=799 / inexbot=558 / loaded=True ✅ |
| 5 | `check_e2e_request.py` | **11/12 HTTP 200**，1 次 502（见下节）⚠️ |

---

## 🔴 本轮核心发现：502 的真正成因 = **三层 timeout 不对齐**，且**不是**并发争抢

### 现象

三轮 e2e 探针（每轮 12 次请求）**每轮都恰好出现 1 次 502**，body 一致：

```json
{"error": {"message": "HTTPConnectionPool(host='localhost', port=8642): Read timed out. (read timeout=300)"}}
```

耗时**精确 300.1s**。

| 轮次 | 是否与姊妹 KB 探针并发 | 结果 |
|---|---|---|
| 第 1 轮（11:08–11:24） | ✅ 并发 | 11/12（1 次 502 @ 300.1s） |
| 第 2 轮（11:36–11:52，**隔离**，`ps` 确认无其它探针） | ❌ 无并发 | **11/12（1 次 502 @ 300.1s）** ← **同样复现** |

> 💡 **关键**：第 2 轮是**完全隔离**的（姊妹 KB 探针 11:24 已退出，
> `ps aux | grep check_e2e_request` 无其它进程），**仍然复现 1 次 502**。
> → **并发争抢不是根因**（只是加剧因素）。姊妹 KB 那轮的结论「并发压 gateway」**不完整**。

### 三层 timeout 不对齐（根因链）

| 层 | 位置 | 值 | 行为 |
|---|---|---|---|
| ① provider read timeout | `agent/anthropic_adapter.py:549` `_read_timeout` | **900s** | 上游 LLM 停顿最多等 900s |
| ② gateway agent timeout | `~/.hermes/config.yaml:12` `gateway_timeout` | **1800s** | gateway 最多等 agent 1800s |
| ③ **proxy 上游 read timeout** | `hermes-skill-proxy.py:47` `HERMES_TIMEOUT` | **300s** | **proxy 300s 就放弃 → 直接回 502** |

→ **③ 比 ①② 短得多** → gateway 还在正常跑，proxy 已经先放弃了。
→ **这是 10-31 那个「120s → 300s」修复的同一个结构性问题，只是阈值不够大。**

### 硬证据：gateway 侧那几次请求**最终是成功的**

解析 `~/.hermes/logs/agent.log` 的 aiohttp access 行
（`[起始时间戳]` vs 日志行时间戳 = gateway 侧真实耗时），今日 42 次请求：

```
gateway-side duration: min=31.0s  p50=83.0s  p75=104.0s  p90=153.0s  p95=471.0s  max=1457.0s
> 240s : 4
> 300s : 4    ← 超过 proxy HERMES_TIMEOUT=300
  start=11:08:13 dur=1270.0s status=200 bytes=0
  start=11:08:23 dur=1457.0s status=200 bytes=0
  start=11:16:29 dur= 471.0s status=200 bytes=0
  start=11:38:46 dur= 313.0s status=200 bytes=0
```

→ 4 次请求在 gateway 侧耗时 **313s / 471s / 1270s / 1457s**，
**其中至少 2 次最终返回了 HTTP 200**（只是 `bytes=0`，因为 proxy 早就断开、流被取消）。
→ **用户侧拿到的是 502，而 gateway 那边其实算完了** —— 这就是「proxy 比 gateway 先放弃」的直接证据。

### ⚠️ 另一个被证伪的假设：e2e 探针的「假模型 → 网关快速拒绝」**不成立**

`check_e2e_request.py` 的注释写着「故意用不存在的 model，让 gateway 快速拒绝」，
但实测 gateway **根本不看请求里的 `model` 字段**：

- `api_server.py:1080` `model_name = body.get("model", self._model_name)`
  —— 这个 `model_name` **只用于响应元数据**（`"model": model` 回给客户端）
- 真正建 agent 的地方是 `api_server.py:824` `model = _resolve_gateway_model()`
  和 `:836` `AIAgent(model=model, ...)` —— **用的是配置里的模型**（`minimax-cn` / MiniMax-M3），
  **完全忽略请求体里的 model**

→ **每一次 e2e 探针请求都是一次完整的 agent 跑**（system prompt 含 KB 注入的
12k–20k 字符 ≈ 6k–10k tokens），**不是**廉价的模型名校验。
→ 这也解释了为什么单次要 30–140s。
→ ⚠️ **姊妹 KB 的 `check_e2e_request.py` 注释同样有误导**，两边都该修正。

### 根因量化：注入的 context 体积

实测 `search_all_kb()` 每次检索注入的 snippet 总量：

| 查询 | 注入字符数 | 约合 tokens |
|---|---|---|
| `示教器 操作手册 功能说明` | **19,900** | ~9,950 |
| `C1102 控制器 通讯接口` | **12,190** | ~6,095 |

（proxy 的 `search_single_kb(top_k=3)` × 2 个 KB，每个 snippet 上限 4000 字符）

→ **6k–10k tokens 的 system prompt** → 上游 LLM 首 token 延迟大幅拉长，
**且偶发停顿能到几百秒**。

### 结论与建议（本轮**未实施**，留给下一轮或人工确认）

**502 是真实用户故障**（不是探针假象）：用户查「冲压工艺手册」这类长手册问题时，
若 gateway 停顿 > 300s，用户拿到的就是 502。

| # | 建议 | 收益 | 风险 |
|---|---|---|---|
| 1 | **降本（治本）**：限制注入 context 体积（如 top_k 3→2，或 snippet 4000→1500 字符） | 直接把 p50/p90 延迟压下来 | ⚠️ 检索召回略降，需权衡 |
| 2 | **兜底**：unit 里显式 `Environment="HERMES_TIMEOUT=1800"`，与 `agent.gateway_timeout` 对齐 | 消除「proxy 比 gateway 先放弃」 | 失败请求挂更久（占线程） |
| 3 | **体验**：proxy 侧对 timeout 做一次自动重试（当前直接 502） | 用户少看到错误 | 重试会放大上游压力 |

> 📌 **本轮未改 proxy 代码、未 restart proxy** —— 原因有三：
> 1. 三个 KB 共用同一个 proxy repo，**本 skill 不替姊妹 KB 决定架构改动**；
> 2. 改 `HERMES_TIMEOUT` 会影响**姊妹 KB 同样在用的链路**，需两边协调；
> 3. 建议 1（降 context 体积）才是治本，且**改 `search_single_kb` 的 top_k 同样影响两个 KB**。
>
> → **本轮把问题精确定位并留下证据，交由下一轮/人工决策。**

### 📌 判读表更新（重要）

| 现象 | 含义 | 本轮观测 |
|---|---|---|
| 502 + body `read timeout=300` | **proxy 的 HERMES_TIMEOUT 到点放弃**，gateway 侧可能仍在正常跑 | ✅ 本轮 2 次复现 |
| 502 + body `read timeout=120` | 10-31 之前的老 bug（已修） | 本轮 0 次 |
| 500 | 检索崩了（slug 契约断裂等） | 本轮 **0** 次 |
| 000 | 客户端 `-m` 太小 | 用 `-m 360` |

---

## 本轮闭合了 11-02 报告的遗留：把「共享文件同步」脚本**入库**

11-02 轮次结束时 `git status` 显示：

```
 M SKILL.md                                   ← version 1.14.0→1.15.0 + 陷阱 16 章节
 M references/shared-proxy-service-pitfalls.md ← 与姊妹 KB 同步
?? scripts/diff_shared_pitfalls.py            ← 未跟踪！
```

`scripts/diff_shared_pitfalls.py` 是 11-02 新写的**同步决策辅助脚本**，SKILL.md 第 1166 行
已经引用它 —— 若被 `git pull` 静默回退，SKILL.md 的链接就会指向不存在的文件
（**陷阱 14 的第三次复发**）。

> 📌 本轮已 `git add` + `commit` + `push`：**commit `040293b`**。

### 共享文件同步：本轮姊妹 KB 是超集 → 直接覆盖

按 11-02 修订后的规则（**先 diff 再决定**，不盲目 cp）：

| | 姊妹 KB | 本 skill（同步前） |
|---|---|---|
| 行数 | 557 | 442 |
| 字节 | 26,807 | 21,292 |
| sha1 | `c3a95a40e3f5…` | `b9419a8cb0e6…` |
| 陷阱 15（`--amend` 后 push → non-fast-forward） | ✅ | ❌ 缺 |
| 陷阱 16（普通箭头 `→` U+2192 也会被 tirith 拦） | ✅ | ❌ 缺 |
| 本 skill 独有 section | — | **无** |

→ `diff_shared_pitfalls.py` 报 `ONLY IN SISTER` = 陷阱 15、16；`ONLY IN OURS` = **空**
→ **姊妹是超集** → `cp` 覆盖即可（本次覆盖不会丢任何内容）。
→ 同步后两份 sha1 均为 **`c3a95a40e3f5a8e2dfe8342b82f6fe20f541701b`**。

### 陷阱 15 / 16 的要点（本轮首次纳入本 skill）

- **陷阱 15**：`git commit --amend` 之后再 `git push` → **non-fast-forward**，
  连试 6 次全失败；**错误尾部是 `non-fast-forward` 还是 `Failed to connect` 决定修法完全不同**
  （前者要 `reset --hard` + 增量重提成 fast-forward，后者直接重试）。
  ⚠️ **不要用 `--force-with-lease`**：两个 KB 共用仓库时会抹掉对方的提交。
- **陷阱 16**：普通箭头 `→`（U+2192）**同样触发** tirith 的 `variation_selector` 拦截
  （陷阱 7 的清单只列了 emoji 的 U+FE0F）。**对策：用 `patch` / `write_file` 走文件工具链，
  不要用 shell heredoc 拼内容。**

## proxy 状态

- 进程 PID **1792095**，启动于 **2026-10-31 11:36:48**（姊妹 KB 10-31 部署 `a331618` 时重启的）
- **本轮未 restart**：index.json 逐字节未变 → 没有新数据要加载，restart 是无谓的
- 四环境变量到位（经 `/proc/<pid>/environ` 实测）
- `journalctl` 按当前进程切片：`Unknown key` = **0**、HTTP 500 = **0**、HTTP 502 = **2**（本轮探针所致）
- 重载链**活着**：定时器线程创建于 **2026-11-03 09:37:34** = 进程启动 +22h = **第 5 次 5h 排期**
- 端口仅 **8643**（proxy）+ **8642**（gateway），无遗留压测进程

## 姊妹 KB 仓库状态（**不代它提交**，仅点名）

`~/.hermes/skills/productivity/inexbot-knowledge-base` 工作树本轮开工时有 2 处未提交改动：

```
 M SKILL.md
 M references/shared-proxy-service-pitfalls.md
```

按纪律**本 skill 不替姊妹 KB 提交**。姊妹那份 `shared-proxy-service-pitfalls.md`
本轮已扩写（18,586 B → 26,807 B，新增陷阱 15、16），本 skill 已按上述规则同步。

> ⚠️ 姊妹 KB 11:03 的 cron **自身报了错**（`cron.scheduler: Job 'inexbot-knowledge-base daily crawl' failed`）——
> 原因不是爬取失败，而是它的报告正文里含 `RuntimeError:` 之类内容被 cron 判为失败。
> 爬取本体是成功的（558/558）。

## 提交状态

| 仓库 | commit | 状态 |
|---|---|---|
| `inexbot-open-knowledge-base` | `040293b` | **已 push**，工作树干净 |
| `hermes-skill-proxy` | 未改动 | 本轮不需要 restart |

SKILL.md → **version 1.15.0**，`last_verified: 2026-11-03`。
