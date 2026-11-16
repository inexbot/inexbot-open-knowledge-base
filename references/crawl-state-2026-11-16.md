# 爬取状态快照 — 2026-11-16

**结论：817/560 连续第三次持平（817 = 11-14 突破 799 后的新基线）**，纯稳态 cycle。

## 核心数据

| 项 | 值 |
|---|---|
| index.json | **2,540,096 bytes**，sha1 `40e809118867`（与 11-14 / 11-15 **逐字节相同**） |
| docs 数 | **817**（inexbot-open）/ **560**（inexbot） |
| verdict | **IDENTICAL** |
| locale 分布 | zh=461 / en=178 / kr=178 |
| crawler 耗时 | **3:47.5**（11:01:27 → 11:05:15） |
| 网络请求 | **0 次**（`✓` 行数 = 0；`raw/` 最新 mtime 仍是 **11-14 11:03**） |
| md/ 重写 | **0**（今日零重写） |
| `.tmp` 残留 | **0** |
| md/ 文件总数 | 1873（1695 locale 前缀 + 178 陈旧裸名） |

## 8 步标准序列（全绿）

| 步骤 | 脚本 | 结果 |
|---|---|---|
| 1 | `check_crawl_state.py` | **IDENTICAL** — 817 entries / 2,540,096 bytes，locale zh=461 en=178 kr=178 |
| 2 | `check_index_hygiene.py` | **OK** — 零宽 0 / 空标题 0 / 空 snippet 34（上游空目录页）/ 幻影 token 可达 0 / 旧 API `star_servo_...` 可达 0 |
| 3 | `check_retrieval_chain.py` | **OK** — **静默降级(==800) = 0**；短正文 4 条 = 伺服报警占位页 61–71 B（上游本来就短，与 10-25 基线一致） |
| 4 | `check_proxy_health.py` | **OK** — inexbot-open 817 + inexbot 560，loaded=True（爬前已是新值） |
| 5 | `check_e2e_request.py` | **12/12 全 200** — 65.3–184.8s，**0 次 502** |
| 6 | `check_proxy_env.py --units` | **OK** — 5 个变量三处（线上 environ / `/etc` unit / repo 模板）sha12 逐项一致；`HERMES_TIMEOUT` sha12=`e49ec846db75` = 1800 ✅ |
| 7 | `check_proxy_staleness.py` | **OK** — 线上 PID 1954151 源码 == HEAD `abb129c` → NOT stale，无需 restart |
| 8 | `check_reload_timer.py` | **OK** — 重载链存活（定时器线程 tid=1970700 @ 08:18:08 = start+21h 第 5 次 5h 排期，下次重载 13:18:08）；内存 817 == 磁盘 817 → in_sync |

## journal（按当前进程 PID 1954151 切片，383 行）

| 计数 | 值 |
|---|---|
| `Unknown key name` | **0** |
| HTTP 500 | **0** |
| HTTP 502 | **0** |
| `RELOAD FAILED` | **0** |
| `Traceback` | **0** |
| HTTP 200 | 36 |

端口仅 **8643**（proxy，PID 1954151）+ **8642**（gateway）——无遗留压测进程。

## 本轮关键动作与判定

### 🔴 上一轮（11-15）被 HTTP 429 打断 → 报告正文结论一律作废（陷阱 14 第 10 次复发，已闭合）

`hermes cron list` 显示 11-15 那轮 `Last run: ... error: RuntimeError: HTTP 429`。
按纪律，**该轮报告正文里的提交结论不可信**，须独立 `git status` 核对。

实测发现本 skill 仓库有 **1 处未入库**：
`M references/shared-proxy-service-pitfalls.md` —— 姊妹 KB 11-15 新增的**陷阱 32/33**
（`scan_kb_topic.py` AND 语义假 0 命中 / `ps` grep 含目录漏判）当时只写进了共享文件、没入库。
若被下次 `git pull` 静默回退 → 这两条新知识会消失。**本轮已闭合入库。**

> 💡 陷阱 14（cron 报告写「遗留：无」但工作其实没提交）**第 10 次复发**。
> 本轮的处置再次验证纪律：**独立 `git status` 核对，不信上一轮报告正文**。

### 共享文件同步：两份 IDENTICAL，无需同步

```
sister   1529 lines    77030 bytes  sha1=020468fb455e533d46007e0192c9d774772056bf
ours     1529 lines    77030 bytes  sha1=020468fb455e533d46007e0192c9d774772056bf
IDENTICAL -- nothing to sync.
```

姊妹 KB 仓库已干净（commit `633a07c docs: add 2026-11-15 crawl state snapshot and pitfalls 32-33`），
陷阱 32/33 已入库 → **本 skill 直接 cp 对齐即可**，方向为「姊妹独有行 = 0 → cp 覆盖」。

结构自检 **exit 0**（两份），回归测试 `test_shared_pitfalls_structure.py` **exit 0**
（完好文件 → 0；孤儿体 → 1）。两条 `WARN DUPLICATE_LINE` 是不同 section 复用同一段 shell 片段
（正常，不计入退出码）。

### proxy 未 restart（两条理由）

1. **内容没变** —— index.json 与 11-14/11-15 逐字节相同（2,540,096 bytes），proxy 内存 817 == 磁盘 817；
2. **代码没变** —— 线上 AST 指纹 == HEAD `abb129c`。

→ 顺带**未打断**姊妹 KB 正在飞的 e2e 探针（姊妹探针 11:01:xx 起跑，与本轮探针同窗口并发）。

### 与姊妹 KB 同窗口并发

姊妹 KB crawler + e2e 探针均与本轮同窗口（11:01 起）。两边探针并发 →
**两边均 12/12 全 200、0 次 502** → 再次印证 11-03 的结论「并发争抢不是 502 根因」。
本轮 crawler 3:47.5 落在稳态带内（3:00–3:50），未受明显影响。

### 新增陷阱（姊妹 11-15 写下，本轮同步入库）

- **陷阱 32**：`scan_kb_topic.py` 是 **AND 语义** → 多词查询（如「冲压工艺 手册」）给**假 0 命中**。
  → **「0 命中」永远要先用更短的单个核心词复验一次再下结论。**
- **陷阱 33**：用 `ps` 判「探针还在跑」时，grep 模式**含目录会漏判**（cmdline 是相对路径）→ 误以为探针已退出。
  → **grep 脚本文件名，不要 grep 含目录的完整路径**；更好的判据是 `process(action='poll')` 的 `status` 字段。

## 本轮新增脚本/文件

- `references/crawl-state-2026-11-16.md`（本文件）
- `references/shared-proxy-service-pitfalls.md` —— 同步入陷阱 32/33（姊妹 KB 11-15 写下）
- `scripts/check_token_consistency.py` —— **姊妹 KB 的 agent 11:28 直接写进本 skill 目录**
  （陷阱 13 场景：本 skill 不代姊妹提交，但姊妹写进本 skill 的文件**本 skill 要负责入库**，
  否则下次 `git pull` 会静默回退）。本轮已验证可用：
  inexbot 0 处不一致 / inexbot-open 0 处不一致 → PASS；
  姊妹 KB 自己的 SKILL.md 已登记该脚本（版本 2.31.0）。

## 遗留

- **无**（`git status` 已核过：SKILL.md + 共享文件 + 快照文件 + 姊妹写入的 token 脚本
  + 良性跟踪的 `.index-snapshot.json`，全部在本轮入库范围内）。
