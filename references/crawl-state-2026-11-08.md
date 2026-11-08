# 2026-11-08 爬取快照 — 799/560 连续第十九次持平（本 KB 纯稳态）

**结论**：本 KB（`inexbot-open`）**799 篇连续第十九次持平**，index.json **2,450,869 bytes**
自 2026-10-29 起逐字节未变，**零网络请求**。姊妹 KB（`inexbot`）**+2 → 560**。

## 一、爬取结果

| 项 | 值 |
|---|---|
| 命令 | `python3 scripts/crawler.py` |
| 启动方式 | `write_file` 外层脚本 → `terminal(background=true, notify_on_complete=true)`（policy 禁 `-lic` wrapper） |
| 耗时 | **3:11.5**（稳态带 3:00–3:50 内 ✅） |
| 页面 | 发现 799 个页面 / 843 个 hash |
| 结果 | **成功 799 / 799** |
| index.json | **2,450,869 bytes**，mtime 2026-11-08 11:03:46 |

**locale 分布**：zh=443 / en=178 / kr=178（与 10-29 起完全一致）

### 稳态硬证据（三条同时成立）

```bash
grep -c "✓" /tmp/open-crawl-20261108.log          # → 0   （零网络请求，全缓存命中）
find ~/.hermes/kb/inexbot-open/raw -newermt "2026-11-08 00:00"   # → 空（raw/ 仍是 10-23）
find ~/.hermes/kb/inexbot-open/md  -newermt "2026-11-08 00:00"   # → 空（md/ 零重写）
ls ~/.hermes/kb/inexbot-open/*.tmp                # → 不存在（原子写无残留）
```

`check_crawl_state.py` → **verdict: IDENTICAL**（799 docs, 2,450,869 bytes，与 11-07 逐字节相同）

## 二、8 步标准验证序列 — 全绿

| 步 | 脚本 | 结果 |
|---|---|---|
| 1 | `check_crawl_state.py` | **IDENTICAL**，799 entries / 2,450,869 B |
| 2 | `check_index_hygiene.py` | 零宽 **0** / 空标题 **0** / 空 snippet 34（上游空目录页，正常）/ 幻影 token 可达 **0** / 旧 API 可达 **0** → exit 0 |
| 3 | `check_retrieval_chain.py` | **静默降级 ==800 = 0**；短正文 4 条 = 伺服报警占位页 61–71 B（上游本来就短）→ exit 0 |
| 4 | `check_proxy_health.py` | open **799** ✅ / 姊妹 **560** ✅ |
| 6 | `check_proxy_env.py --units` | 5 个变量 × 3 处 sha12 逐项一致，`HERMES_TIMEOUT` sha12=`e49ec846db75`（=1800）✅ |
| 7 | `check_proxy_staleness.py` | 线上 PID 1844673 源码 == HEAD `abb129c` → **NOT stale**，无需 restart → exit 0 |
| 8 | `check_reload_timer.py` | 重载链存活，定时器 tid=1883325（2026-11-08 09:03:46 出生，age 2.01h），**下次重载 14:03:46**；内存/磁盘双 KB 均同步 ✅ |
| 5 | `check_e2e_request.py` | **12/12 全 200**，**0 次 502** → 连续第 4 天 502 计数为 0 |

### e2e 明细（12 次，37.6s–167.3s）

```
C1102 控制器 通讯接口 有哪些 : 46.0 / 80.8 / 64.2 / 37.6      全 200
冲压工艺 手册 参数设置         : 81.7 / 143.8 / 106.5 / 57.5     全 200
示教器 操作手册 功能说明       : 167.3 / ...                      全 200
```

无一次触碰 300s（旧上限）边界 → `HERMES_TIMEOUT=1800` 修复持续生效。

## 三、本轮抓到的问题与处置

### ① 共享文件是**陈旧超集**（不是「各有独有 section」）→ 直接 cp

上一轮（11-07）走的是「双方各有独有 section → 跑 merge 脚本」。本轮实测**方向反了**：

| | 行数 | 字节 | sha1 |
|---|---|---|---|
| 姊妹 | 919 | 46,125 | `9123cfa68c20` |
| 本 skill | 926 | 46,718 | `675dc4fe8e6a` |

`diff_shared_pitfalls.py` 的 diff 统计：**姊妹独有行 = 0**，**本 skill 独有行 = 7**。
且 22 个 section 标题**完全一致**（无任何「ONLY IN SISTER」）。

**那 7 行是过时内容，不是独有知识**：

1. 陷阱 21 里残留的旧判据「所以健康的 proxy **必然**存在一个 age 落在 **4~5 小时**的线程」——
   这正是 **SKILL.md 和姊妹 11-07 修正版都明确否定**的错误判据（定时器 age 在 `[0,5h)` 均匀分布）；
2. 旧版 exit 1 判据注释「没找到 age 落在 5h 附近的线程 -> 重载链可能已断裂」；
3. 附录里重复的旧标题行 + **过时基线** `inexbot 559 / 1,728,927 bytes` 与 `558 / 1,722,769 bytes` 两行并存。

⇒ **判定规则再次被验证**：**「姊妹 = 权威 → 直接 cp」只在姊妹确实更新时成立**。
判据不是「谁行数多」，而是 **「姊妹独有行数 vs 本 skill 独有行数 + 独有内容是不是过时/重复」**。
本轮本 skill 行数**更多**（926 > 919）却更差 → **行数多 ≠ 权威**。
姊妹独有 = 0 → 直接 `cp` 覆盖（无需跑 merge 脚本）。

> ⚠️ **`diff_shared_pitfalls.py` 的 DECISION GUIDE 措辞有误导性**：
> 它把「we have sections sister lacks」判为反向补齐，但**不区分「独有 section」与「过时的重复行」**。
> 本轮的 7 行**不属于任何独有 section**（22 个标题全同），只是同 section 内的残留。
> → 建议下轮把「section 标题集合相同 + 姊妹独有行 = 0」也显式列为「可 cp」的判据。

### ② `check_proxy_health.py` 的姊妹基线过时 → 558 → 560

姊妹 KB 今日 **+2 → 560**（`1,735,196 bytes`）。本 skill 的 `BASELINES["inexbot"]` 还是 558。
已 patch 为 560（姊妹 11-08 自身记录「560 pages」）。姊妹的 559 → 560 是 2026-11-07 之后的**真实增长**，
不是本 skill 的抽取变更（姊妹的 index 在**它自己的** KB 目录里，与本 skill 无关）。

### ③ 陷阱 14 **第 4 次复发**：11-07 遗留的 2 处工作未提交

11-07 那轮改了 `SKILL.md`（version 1.21.0 → 1.22.1，新增「重载链守卫」小节）并新建了
`references/reload-chain-guard.md`（125 行），但**两者都没入库**：

```
M  SKILL.md
?? references/reload-chain-guard.md
```

其中 `references/reload-chain-guard.md` 是 **SKILL.md 里被引用的目标文件**
（SKILL.md 第 697 行：「见 `references/reload-chain-guard.md`」）——
**未跟踪 = 下次 `git pull` 静默回退 → SKILL.md 的链接指向不存在的文件**。
这与 11-02 / 11-03 / 11-06 / 11-07 是**同一个失效模式**（静默失效：文件消失，链接还在）。

本轮已 add + commit + push（见下）。

## 四、proxy 未 restart 的两条理由

① **index.json 逐字节未变**（2,450,869 B，与 11-07 相同）→ 无需为内容 restart；
② **线上源码 AST 等价于 HEAD `abb129c`**（`check_proxy_staleness.py` exit 0）→ 无需为部署 restart。

→ 顺带**避免打断姊妹 KB 的探针**（陷阱 1 / 陷阱 20）。
本轮探针启动前 `ps` 确认：姊妹 KB 只有自己的 crawler 在跑，**没有任何 probe 在飞** → 安全窗口。

## 五、journal 按进程切片（PID 1844673，2026-11-05 11:02:57 起）

- `Unknown key name` = **0**
- HTTP **500** = **0**
- HTTP **502** = **0**
- `RELOAD FAILED` = **0**
- HTTP 200 = 正常计数

端口仅 8643（proxy）+ 8642（gateway），无遗留压测进程。

## 六、本轮提交

```
git add SKILL.md references/reload-chain-guard.md references/shared-proxy-service-pitfalls.md
git add scripts/check_proxy_health.py references/crawl-state-2026-11-08.md
git add references/.index-snapshot.json
git commit -m "docs: add 2026-11-08 crawl state (799/560 19th flat), commit 11-07 leftovers"
git push
```

commit message 用**纯 ASCII**（陷阱 5：含中文会被 tirith `confusable_text` 拦下）。

## 七、遗留

**无**（已 `git status` 核过：本 skill 仓库工作树干净，仅剩被跟踪的
`references/.index-snapshot.json` 这一个良性改动 —— 它每轮刷新，属预期）。

> 姊妹 KB 仓库（`inexbot-knowledge-base`）工作树干净，无待提交项；
> 本 skill **不替它提交**（陷阱 4 的良性竞态原则）。
