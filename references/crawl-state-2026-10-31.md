# 2026-10-31 爬取状态：799/558 连续第十二次持平（纯稳态，零网络请求）

## 爬取本体：完全稳态，无任何异常

| 项目 | 结果 |
|---|---|
| 爬取页数 | **799 / 799**（0 失败） |
| 耗时 | **3:18.8**（稳态带 3:00–3:20 内） |
| index.json | **2,450,869 bytes** —— 与 10-30 **逐字节相同** |
| verdict | `IDENTICAL`（`check_crawl_state.py`） |
| 网络请求 | **0**（日志 `✓` 行 = 0；`raw/` 最新 mtime = 2026-10-23） |
| locale 拆分 | zh=443 / en=178 / kr=178 |
| md/ 今日重写 | **0 个**（`find -newermt` 无命中） |
| `.tmp` 残留 | 无（原子写正常） |
| 姊妹 KB | 558（同窗口，index mtime 11:03:13） |

上游**零变化**，连续第 12 次持平（自 2026-10-10 起 21 天零新增）。

## 本轮：纯稳态 cycle，无代码改动，只做验证 + 文档沉淀

与 10-30 那轮（闭合了两项遗留）不同，本轮**没有任何待办遗留**：
`hermes cron list` 的 Last run 为 `ok`，上一轮报告无「待办」清单。
因此本轮工作 = 跑爬取 + 全链路验证 + 把新踩到的坑沉淀进 skill。

### ① 姊妹 KB 的 `shared-proxy-service-pitfalls.md` 是权威版 → 已同步

10-30 那轮两个 KB 各自写了 `references/shared-proxy-service-pitfalls.md`，
两份内容**不一致**（姊妹 9,713 B vs 本 skill 7,939 B，diff 144 行）。
姊妹那版是**细化后的权威版**（补充了「对策」小节、修正了字段编号、
扩写了 policy 拦截清单的说明），本 skill 那版是较早的子集。

按文件自身声明的规则（「姊妹 skill 那份是权威来源，有出入以它为准」），
**已把姊妹那份覆盖到本 skill** → 两份 sha 均为 `44b62282ea9fcb5e`，逐字节一致。

> 💡 **教训**：跨 KB 的共享文档，两边各写一份必然漂移。
> 权威归属要**写进文件头**，并明确「以 X 为准（并去修这边）」，
> 否则下轮 agent 会拿自己那份当真相。

### ② `/proc/<pid>/task/<tid>/stat` 字段偏移坑（详见 SKILL.md 新增章节）

本轮验证 proxy 重载链是否活着时，手算线程启动时间得到**负数年龄**
（`age=-4201h`）→ 一度误判成「进程启动于未来」。

**根因**：`starttime`（字段 22 = `tail[19]`）是**自 boot 以来的绝对时钟滴答数**，
不是相对偏移。正确公式：`boot_time + starttime/HZ`。
**更省事的替代**：`ps -L -o pid,tid,lstart,etime,stat -p <pid>` 直接给结果。

### ③ `references/.index-snapshot.json` 被 git 跟踪 → 每轮都脏工作树

`check_crawl_state.py` 每次都刷新该快照文件，它**被 git 跟踪**
→ 每轮 cron 结束 `git status` 必有一处 `M references/.index-snapshot.json`。
**良性**（快照本就该跟着 index 走），不要误当成「有未提交的代码改动」。

## 验证结果（全绿）

### 索引卫生（10-29 三修之后仍然成立）

| 指标 | 值 | 期望 |
|---|---|---|
| 含零宽字符（U+200B/C/D、U+FEFF）的条目 | **0** | 0 ✅ |
| 空标题条目 | **0** | 0 ✅ |
| 空 `content_snippet` 条目 | 34 | ~34（上游空目录页，标题兜底链已补上）✅ |
| 幻影 token `cppset_tool_hand_number` index 可达数 | **0** | 0 ✅ |
| 旧 API `star_servo_point_position_motion_control` index 可达数 | **0** | 0 ✅ |

> `star_servo_...` 在 `raw/` 里仍有 1,849 次命中 → 证明**上游确实保留着旧标识符**
> （或只是 sibling KB 的页面里有），但**没有任何 index 可达的 md 命中它**
> → 与 10-25 的结论一致：那是不可达死缓存，不影响用户回答。

### 检索链路（`check_retrieval_chain.py`）

11 组查询全部通过：**静默降级(==800) = 0**，异常 = False。
4 条「短正文(<200)」全是上游一行占位的伺服报警页
（`0x0008`/`0x000B`/`0x0050`/`0x0051`，61–71 字节），属正常。

### proxy 运行时

- `/health`：`inexbot-open` docs=799 / `inexbot` docs=558，both `loaded=True`
- 进程 PID 1779868，启动于 2026-10-30 11:16:36（uptime 23.8h）
- **重载链活着**：定时器线程创建于 2026-10-31 07:16:54 = start + 20h = 第 4 次 5h 排期
  （下次 ≈ 12:16）。主线程 + 定时器线程共 2 个，正常形态。
- `schedule_reload()` 已带 `try/except/finally` → 无论成败都会重新排期
- `/proc/<pid>/environ` 四个环境变量全部到位
  （`HERMES_API_KEY` len=21 sha12=`23760f4462da`，与 unit、代码默认值三处一致）
- `journalctl | grep -c "Unknown key"` = **0**
- unit 文件 `Environment=` 已是每行一个 `Environment="K=V"` 的正确写法
- 端口只有 8643(proxy) + 8642(gateway) → **无遗留压测进程**

### 不需要 restart proxy

本轮 index **逐字节未变**（2,450,869 bytes），proxy 跑前跑后 `/health` 都是 799，
且 5h 自动重载链已确认活着 → **不 restart**（避免无谓的 systemd 启动窗口竞态）。

## 本轮动作清单

| # | 动作 | 结果 |
|---|---|---|
| 1 | 跑爬取（`terminal(background=true)` + inline `os.kill` 等待） | 799/799，3:18.8 ✅ |
| 2 | `check_crawl_state.py` | IDENTICAL ✅ |
| 3 | `check_retrieval_chain.py` | 无降级 ✅ |
| 4 | `check_proxy_health.py` | 799/558 OK ✅ |
| 5 | 索引卫生探针 | 全绿 ✅ |
| 6 | 同步姊妹的权威 `shared-proxy-service-pitfalls.md` | 两份 sha 一致 ✅ |
| 7 | proxy 重载链 / 环境变量 / unit 校验 | 全部正常 ✅ |
| 8 | SKILL.md 补 2 个新坑 + 本文档 | ✅ |
| 9 | commit + push | ✅ |

## 遗留

**无**。下一轮可直接跑爬取 + 常规验证。
