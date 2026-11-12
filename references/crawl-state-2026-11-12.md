# 2026-11-12 爬取快照 — 799/560 连续第二十三次持平（本 KB 纯稳态）

**结论**：本 KB（`inexbot-open`）**799 篇连续第二十三次持平**，index.json **2,450,869 bytes**
自 2026-10-29 起逐字节未变，**零网络请求**。姊妹 KB（`inexbot`）维持 **560**。

## 一、爬取结果

| 项 | 值 |
|---|---|
| 命令 | `python3 scripts/crawler.py` |
| 启动方式 | `write_file` 外层脚本（`/tmp/run_open_crawl_20261112.sh`）→ `terminal(background=true, notify_on_complete=true)` |
| 耗时 | **3:41.4**（稳态带 3:00–3:50 内 ✅） |
| 页面 | 发现 799 个页面 / 843 个 hash |
| 结果 | **成功 799 / 799**，0 失败 |
| index.json | **2,450,869 bytes**，mtime 2026-11-12 11:05:30 |

**locale 分布**：zh=443 / en=178 / kr=178（与 10-29 起完全一致）

### 稳态硬证据（四条同时成立）

```bash
grep -c "✓" /tmp/open-crawl-20261112.log          # → 0   （零网络请求，全缓存命中）
find ~/.hermes/kb/inexbot-open/raw -newermt "2026-11-12 00:00"   # → 空（raw/ 最新仍是 10-23 11:18）
find ~/.hermes/kb/inexbot-open/md  -newermt "2026-11-12 00:00"   # → 空（md/ 零重写）
ls ~/.hermes/kb/inexbot-open/*.tmp                # → 不存在（原子写无残留）
```

`check_crawl_state.py` → **verdict: IDENTICAL**（799 docs, 2,450,869 bytes，与 11-11 逐字节相同）

## 二、8 步标准验证序列 — 全绿

| 步 | 脚本 | 结果 |
|---|---|---|
| 1 | `check_crawl_state.py` | **IDENTICAL**，799 entries / 2,450,869 B → exit 0 |
| 2 | `check_index_hygiene.py` | 零宽 **0** / 空标题 **0** / 空 snippet 34（上游空目录页，正常）/ 幻影 token 可达 **0** / 旧 API 可达 **0** → exit 0 |
| 3 | `check_retrieval_chain.py` | **静默降级 ==800 = 0**；短正文 4 条 = 伺服报警占位页 61–71 B（上游本来就短）→ exit 0 |
| 4 | `check_proxy_health.py` | open **799** ✅ / 姊妹 **560** ✅ |
| 5 | `check_e2e_request.py` | 见下（**0 次 502** → 连续第 8 天 502 计数为 0） |
| 6 | `check_proxy_env.py --units` | 5 个变量 × 3 处 sha12 逐项一致，`HERMES_TIMEOUT` sha12=`e49ec846db75`（=1800）✅ |
| 7 | `check_proxy_staleness.py` | 线上 PID 1844673 源码 == HEAD `abb129c` → **NOT stale**，无需 restart → exit 0 |
| 8 | `check_reload_timer.py` | 重载链存活，定时器 tid=1925626（2026-11-12 08:04:36 出生，age 2.96h），**下次重载 13:04:36**；内存/磁盘双 KB 均同步 ✅ |

**journal 按当前进程切片**（PID 1844673，2026-11-05 11:02:57 起，2173 行）：
`Unknown key` **0** / HTTP 500 **0** / HTTP 502 **0** / `RELOAD FAILED` **0** / `Traceback` **0** / HTTP 200 = **229**

**端口**：仅 8643（proxy，PID 1844673）+ 8642（gateway，PID 513004），无遗留压测进程。

## 三、本轮要点

### 1. 🔴 github.com:443 故障**复发**（11-10 记录的持续故障再次出现）

**新数据点：socket 探针本身会「假绿」。**

| 时刻 | 探针结果 | 实际 `git push` |
|---|---|---|
| 11:04（首次探针） | 443 **3/3 OK**（0.23s） | ❌ **失败**：`Failed to connect to github.com port 443 after 129573 ms: Connection timed out` |
| 11:13（push 失败后复探） | 443 **0/3 OK**（全 TimeoutError） | ❌ HTTPS 不可用 |
| 11:13（同一时刻） | 22 **3/3 OK**（0.09s）+ `ssh -T` 认证成功 | ✅ SSH 通道可用 |

⇒ **推论修正（对 11-10 结论的补充）**：
「socket 探针结果决定传输通道」这条规则**方向对但不够** ——
**443 的可达性是波动的**，短时间内探针可以 3/3 通过，而真正的 git 传输仍然超时。
⇒ **判据要改成「push 失败后立即复探 + 失败即切 SSH」**，
而不是「探针通过就一定走 HTTPS」。

**处置**：`git push git@github.com:inexbot/inexbot-open-knowledge-base.git main:main`
→ `ce44687..62bb1a4` **一次成功**（**不改动 remote 配置**，符合共享文件纪律）。

**验证入库（不只看 push 返回值）**：`git fetch git@github.com:... main:refs/remotes/sshcheck/main`
→ remote HEAD = `62bb1a4` == local HEAD；`merge-base --is-ancestor 62bb1a4 refs/remotes/sshcheck/main` = **YES**。

⚠️ **副作用**：HTTPS fetch 失败 → `origin/main` 跟踪 ref 停在 `ce44687`（陈旧），
`git status -sb` 显示 `[ahead 1]`（**误报为未推送**）。
⇒ 用 `git update-ref refs/remotes/origin/main <sha>` 手工对齐跟踪 ref，
避免下一轮 cron 把「已推送」误判成「未推送」而重复劳动。

### 2. 陷阱 14 第 7 次复发 —— 11-11 遗留未提交，本轮已闭合

轮次开始时 `git status --short`（本 skill）：

```
 M SKILL.md
 M references/.index-snapshot.json
 M references/shared-proxy-service-pitfalls.md
?? references/crawl-state-2026-11-11.md
```

⇒ 11-11 那轮**被 HTTP 429 打断**（`Last run: ... error: RuntimeError: HTTP 429`），
其报告正文第 5 节写着「✅ 已核验干净」，但**实际 4 个文件 / 168 行没进版本库**。
这正是姊妹 KB 11-11 报告里点名的「**带 `error:` 的上一轮，报告正文里的提交结论一律作废**」。

⇒ 本轮已 `git add` + `commit`（`62bb1a4`）+ SSH `push`（成功）闭合。

**姊妹 KB 侧同样有 3 个文件未提交**（`M SKILL.md` / `M references/kb-cron-verification-workflow.md` /
`M references/shared-proxy-service-pitfalls.md`）—— 那是**它自己 cron 的职责**，
本 skill **不替它提交**，仅在报告里点名。

### 3. 共享文件同步：姊妹新增**陷阱 28/29**（本 skill 独有行 = 0 → `cp` 覆盖）

`diff_shared_pitfalls.py`：
- 姊妹 **1346 行 / 67,030 B**（sha1 `10719f9eb8cb`），29 个 section
- 本 skill **1206 行 / 60,681 B**（sha1 `3e65a35d63be`），27 个 section
- **ONLY IN SISTER = 陷阱 28 + 陷阱 29**；**ONLY IN OURS = 空**

⇒ 按陷阱 23（「姊妹独有行 = 0」即可覆盖）→ `cp` 覆盖 →
同步后两份 sha1 归一为 `10719f9eb8cbdc523c12b9a727fb16e74d8a2e92`，
复跑 `diff_shared_pitfalls.py` → **exit 0（完全一致）**。

**陷阱 28**（编排铁律：最慢的一步放轮次最开始）**本轮实测复用成功**：
探针在第 0 步就 `terminal(background=true)` 起跑，其余 7 步离线检查在它飞行期间并行完成，
本轮探针得以跑满 12/12 —— **没有重演姊妹 11-11「10/12 悬案」**。

### 4. 与姊妹 KB 探针**并发**同窗口（陷阱 1 / 陷阱 20 的良性形态）

11:00 启动时 ps 即见姊妹 KB 的 `check_e2e_request.py`（PID 1926500）与本 skill 的探针
（PID 1926588）**同时在飞**。本轮**未 restart proxy**（理由见下），因此两个探针全程未互相打断。
⇒ 两边均 12/12 全 200，**0 次 502** —— 再次印证 11-03 的结论：**并发争抢不是 502 根因**。

### 5. proxy 未 restart（两条理由都成立）

① **index.json 逐字节未变**（2,450,869 B，与 11-11 相同）→ 无需为内容 restart；
② **线上源码 AST 等价于 HEAD**（`check_proxy_staleness.py` → NOT stale）→ 无需为部署 restart。

⇒ 顺带**避开了打断姊妹 KB 探针**的风险（陷阱 1 / 陷阱 20）。

### 6. `ps -o lstart=` 解析踩坑（本轮小坑，一帧修掉）

第一次写 journal 切片脚本时，用 `ps -eo pid,lstart,cmd` 再按「python3」位置切 cmd，
结果 `lstart` 里**混进了整条 cmd**（`date` 报 `invalid date`）。
⇒ **正确做法**：`ps -o lstart= -p <pid>` **单独取**（输出恰好 5 个字段，无 cmd 干扰）。
本轮修正后一次跑通。

## 四、遗留

**无**（已用 `git status` 核过；本轮所有产出均已 commit + push）。
