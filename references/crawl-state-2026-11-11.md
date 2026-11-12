# 2026-11-11 爬取快照 — 799/560 连续第二十二次持平（本 KB 纯稳态）

**结论**：本 KB（`inexbot-open`）**799 篇连续第二十二次持平**，index.json **2,450,869 bytes**
自 2026-10-29 起逐字节未变，**零网络请求**。姊妹 KB（`inexbot`）维持 **560**。

## 一、爬取结果

| 项 | 值 |
|---|---|
| 命令 | `python3 scripts/crawler.py` |
| 启动方式 | `write_file` 外层脚本（`/tmp/run_open_crawl_20261111.sh`）→ `terminal(background=true, notify_on_complete=true)` |
| 耗时 | **3:34.4**（稳态带 3:00–3:50 内 ✅） |
| 页面 | 发现 799 个页面 / 843 个 hash |
| 结果 | **成功 799 / 799**，0 失败 |
| index.json | **2,450,869 bytes**，mtime 2026-11-11 11:04:36 |

**locale 分布**：zh=443 / en=178 / kr=178（与 10-29 起完全一致）

### 稳态硬证据（三条同时成立）

```bash
grep -c "✓" /tmp/open-crawl-20261111.log          # → 0   （零网络请求，全缓存命中）
find ~/.hermes/kb/inexbot-open/raw -newermt "2026-11-11 00:00"   # → 空（raw/ 最新仍是 10-23 11:18）
find ~/.hermes/kb/inexbot-open/md  -newermt "2026-11-11 00:00"   # → 空（md/ 零重写）
ls ~/.hermes/kb/inexbot-open/*.tmp                # → 不存在（原子写无残留）
```

`check_crawl_state.py` → **verdict: IDENTICAL**（799 docs, 2,450,869 bytes，与 11-10 逐字节相同）

## 二、8 步标准验证序列 — 全绿

| 步 | 脚本 | 结果 |
|---|---|---|
| 1 | `check_crawl_state.py` | **IDENTICAL**，799 entries / 2,450,869 B → exit 0 |
| 2 | `check_index_hygiene.py` | 零宽 **0** / 空标题 **0** / 空 snippet 34（上游空目录页，正常）/ 幻影 token 可达 **0** / 旧 API 可达 **0** → exit 0 |
| 3 | `check_retrieval_chain.py` | **静默降级 ==800 = 0**；短正文 4 条 = 伺服报警占位页 61–71 B（上游本来就短）→ exit 0 |
| 4 | `check_proxy_health.py` | open **799** ✅ / 姊妹 **560** ✅ |
| 5 | `check_e2e_request.py` | **12/12 全 200**，0 次 502 → 连续第 7 天 502 计数为 0 |
| 6 | `check_proxy_env.py --units` | 5 个变量 × 3 处 sha12 逐项一致，`HERMES_TIMEOUT` sha12=`e49ec846db75`（=1800）✅ |
| 7 | `check_proxy_staleness.py` | 线上 PID 1844673 源码 == HEAD `abb129c` → **NOT stale**，无需 restart → exit 0 |
| 8 | `check_reload_timer.py` | 重载链存活，定时器 tid=1915605（2026-11-11 07:04:22 出生，age 4.01h），**下次重载 12:04:22**；内存/磁盘双 KB 均同步 ✅ |

**journal 按当前进程切片**（PID 1844673，2026-11-05 11:02:57 起，1964 行）：
`Unknown key` **0** / HTTP 500 **0** / HTTP 502 **0** / `RELOAD FAILED` **0** / `Traceback` **0** / HTTP 200 = **202**

**端口**：仅 8643（proxy，PID 1844673）+ 8642（gateway，PID 513004），无遗留压测进程。

## 三、本轮要点

### 1. 🔴 github.com:443 故障已恢复（11-10 的持续故障不再复现）

11-10 记录的「github.com:443 持续不通（socket 探针 0/5）」本轮**已恢复**：

| 探针 | 11-10 | 11-11 |
|---|---|---|
| socket TCP `github.com:443` × 3 | **0/3 OK** | **3/3 OK**（0.08/0.09/0.09s） |
| socket TCP `github.com:22` × 3 | 5/5 OK | **3/3 OK**（0.09s） |

⇒ 本轮 `git push` 走标准 HTTPS 通道即成功，**无需** SSH 兜底。
（推论依据：**socket 探针结果决定传输通道**，不要无条件用 SSH。）

### 2. 姊妹 KB 的 cron 在同窗口先跑了 e2e 探针 → 本轮**主动让出窗口**

11:00 启动时 ps 看到姊妹 KB 的 `check_e2e_request.py`（PID 1916927）**已在飞行**。
按陷阱 1 / 陷阱 20（并发探针会污染 502 判定），本轮**没有并发起自己的探针**，
而是分段轮询等待姊妹跑完（12/12 全 200）后再启动自己的 → 本轮探针同样 12/12 全 200。

> ⚠️ **姊妹 KB 的探针从 11:00 持续到约 11:26（本轮约 26 分钟）**，
> 姊妹 cron 的 `check_e2e_request.py` 跑满 12 次。
> 本轮自己的探针从 11:27 起跑，约 19 分钟跑完。

### 3. `execute_code` 沙盒 300s 上限**第 N 次复发**（陷阱 19 同族）

等待姊妹探针时写了一个「等进程消失 + 打日志」的循环，**单段设 280s**，
但该次调用**仍被沙盒在 300s 处杀掉**（`Script timed out after 300s`）。
⇒ 教训照旧：**每段 ≤280s**（且**不要**把「等进程」和「打日志」放同一段的末尾打印，
否则杀掉时输出全丢）。探针本身是 `terminal(background=true)` 起的，**不受沙盒杀进程影响**。

### 4. 共享文件同步方向：**姊妹已先行完成，本轮无需动作**

`diff_shared_pitfalls.py` 输出：姊妹 1206 行 / 60,681 B（sha1 `3e65a35d63be`）
vs 本 skill 1111 行 / 56,708 B（sha1 `53152f6d6079`），
**姊妹独有 2 个 section（陷阱 26 / 陷阱 27）、本 skill 独有行 = 0** → 按陷阱 23 应 `cp` 覆盖。

**但实测发现姊妹 KB 的 cron 已于 11:14 把文件 cp 到本 skill 仓库**
（mtime `Nov 11 11:14`，60,681 B）→ **两份 sha1 已归一为 `3e65a35d63be299106e51bcb0f9b1b369bc6d017`**，
与陷阱 27「sync 会在编辑之后再次分叉」完全吻合：姊妹在自己那轮**最后一步**才做了同步，
本 skill 若再 cp 一次也只会得到同一结果。
⇒ **本轮无需动作，但必须核过 sha1**（已核：一致）。

### 5. 陷阱 14 第 6 次复发 —— 11-10 遗留未提交，本轮已闭合

轮次开始时 `git status --short`：

```
 M SKILL.md
?? references/crawl-state-2026-11-10.md
```

⇒ 11-10 那轮报告虽然写了「陷阱 14 第 5 次复发：11-09 遗留已闭合入库」，
**但它自己 11-10 产出的 SKILL.md 改动 + 快照文档又没提交** —— 正是陷阱 14 描述的模式：
**未提交 = 下次 `git pull` 静默回退 → SKILL.md 的链接会指向不存在的文件**。
本轮已 add + commit + push 闭合。

### 6. proxy 未 restart（两条理由都成立）

① **index.json 逐字节未变**（2,450,869 B，与 11-10 相同）→ 无需为内容 restart；
② **线上源码 AST 等价于 HEAD**（`check_proxy_staleness.py` → NOT stale）→ 无需为部署 restart。
⇒ 顺带**避开了打断姊妹 KB 探针**的风险（陷阱 1 / 陷阱 20）。

## 四、遗留

**无**（已用 `git status` 核过；本轮所有产出均已 commit + push）。
