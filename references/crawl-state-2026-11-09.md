# 2026-11-09 爬取快照 — 799/560 连续第二十次持平（本 KB 纯稳态）

**结论**：本 KB（`inexbot-open`）**799 篇连续第二十次持平**，index.json **2,450,869 bytes**
自 2026-10-29 起逐字节未变，**零网络请求**。姊妹 KB（`inexbot`）维持 **560**。

## 一、爬取结果

| 项 | 值 |
|---|---|
| 命令 | `python3 scripts/crawler.py` |
| 启动方式 | `write_file` 外层脚本（`/tmp/run_open_crawl_20261109.sh`）→ `terminal(background=true, notify_on_complete=true)` |
| 耗时 | **3:13.8**（稳态带 3:00–3:50 内 ✅） |
| 页面 | 发现 799 个页面 / 843 个 hash |
| 结果 | **成功 799 / 799** |
| index.json | **2,450,869 bytes**，mtime 2026-11-09 11:04:01 |

**locale 分布**：zh=443 / en=178 / kr=178（与 10-29 起完全一致）

### 稳态硬证据（三条同时成立）

```bash
grep -c "✓" /tmp/open-crawl-20261109.log          # → 0   （零网络请求，全缓存命中）
find ~/.hermes/kb/inexbot-open/raw -newermt "2026-11-09 00:00"   # → 空（raw/ 最新仍是 10-23 11:18）
find ~/.hermes/kb/inexbot-open/md  -newermt "2026-11-09 00:00"   # → 空（md/ 零重写）
ls ~/.hermes/kb/inexbot-open/*.tmp                # → 不存在（原子写无残留）
```

`check_crawl_state.py` → **verdict: IDENTICAL**（799 docs, 2,450,869 bytes，与 11-08 逐字节相同）

## 二、8 步标准验证序列 — 全绿

| 步 | 脚本 | 结果 |
|---|---|---|
| 1 | `check_crawl_state.py` | **IDENTICAL**，799 entries / 2,450,869 B |
| 2 | `check_index_hygiene.py` | 零宽 **0** / 空标题 **0** / 空 snippet 34（上游空目录页，正常）/ 幻影 token 可达 **0** / 旧 API 可达 **0** → exit 0 |
| 3 | `check_retrieval_chain.py` | **静默降级 ==800 = 0**；短正文 4 条 = 伺服报警占位页 61–71 B（上游本来就短）→ exit 0 |
| 4 | `check_proxy_health.py` | open **799** ✅ / 姊妹 **560** ✅ |
| 6 | `check_proxy_env.py --units` | 5 个变量 × 3 处 sha12 逐项一致，`HERMES_TIMEOUT` sha12=`e49ec846db75`（=1800）✅ |
| 7 | `check_proxy_staleness.py` | 线上 PID 1844673 源码 == HEAD `abb129c` → **NOT stale**，无需 restart → exit 0 |
| 8 | `check_reload_timer.py` | 重载链存活，定时器 tid=1894538（2026-11-09 10:03:58 出生，age 1.01h），**下次重载 15:03:58**；内存/磁盘双 KB 均同步 ✅ |
| 5 | `check_e2e_request.py` | **12/12 全 200**，**0 次 502** → 连续第 5 天 502 计数为 0 |

### e2e 明细（12 次，46.3s–176.9s）

```
C1102 控制器 通讯接口 有哪些 : 46.3 / 51.8 / 55.5 / 70.5      全 200
冲压工艺 手册 参数设置         : 84.7 / 82.4 / 124.6 / 76.6     全 200
示教器 操作手册 功能说明       : 130.9 / 107.0 / 118.0 / 176.9  全 200
```

无一次触碰 300s（旧上限）边界 → `HERMES_TIMEOUT=1800` 修复持续生效。

## 三、本轮观察到的情况

### ① 共享文件同步方向：**姊妹更新 → 直接 cp**（与 11-08 方向再次反转）

| | 行数 | 字节 | sha1 | 姊妹独有行 | 本 skill 独有行 | section 标题 |
|---|---|---|---|---|---|---|
| 姊妹 | 979 | 49,861 | `fdc364656f99` | — | — | 23 |
| 本 skill（同步前） | 961 | 48,714 | `08b8b138a901` | **2 块** | **0** | 23（标题完全一致） |

**姊妹独有行 = 0 块 → 0、本 skill 独有行 = 0 → 判定为「姊妹更新且本 skill 无独有内容」**
→ 直接 `cp` 覆盖（未跑 merge 脚本）。同步后两份 sha1 归一为
`fdc364656f990254be31bfaae5c4bed71d1eccf1`。

姊妹新增的两块内容：
- 陷阱 14 的「变体」补充：未跟踪的 `references/*.md` 若被 SKILL.md 引用，
  **必须与 SKILL.md 同一个 commit 入库**，否则下次 `git pull` 后链接失效；
- 附录里姊妹 KB 的 index 基线更新（`inexbot` 560 / 1,735,196 bytes）+ 明确提醒
  **别把姊妹 KB 的增长误记成「本 skill 的抽取变了」**。

⇒ **同步方向连续三轮反转（11-07 merge → 11-08 cp → 11-09 cp）**，
再次印证陷阱 23：**判据是「姊妹独有行 vs 本 skill 独有行 + 内容是不是过时残留」，
不是行数**。本 skill 行的字节数少于姊妹 → 姊妹确实更新 → cp。

### ② 本轮**无新缺陷**（陷阱 14 未复发）

上一轮（11-08）已把所有改动入库。本轮开跑前 `git status --short` 只有一项：
` M references/shared-proxy-service-pitfalls.md`（姊妹在同窗口先改了它，本轮按规则 cp 同步）。
**没有 `??` 未跟踪文件，也没有 `M` 的代码/文档文件** → 无「报告写『遗留：无』但实际没提交」的复发。

### ③ 姊妹 KB 的探针与本轮探针**并发**（但结果仍全绿）

本轮 e2e 探针运行期间，`ps` 看到姊妹 KB 的 `check_e2e_request.py --runs 4` 已在跑
（PID 1895536/1895545，启动于本轮探针后约 4 分钟）。
按 11-03 的结论「并发争抢不是 502 的根因，只是加剧因素」，本轮仍然 **12/12 全 200**，
且本轮最长一次 176.9s 远未触到 300s（旧上限）边界 → 再次印证 `HERMES_TIMEOUT=1800` 生效。

## 四、proxy 未 restart 的两条理由

① **index.json 逐字节未变**（2,450,869 B，与 11-08 相同）→ 无需为内容 restart；
② **线上源码 AST 等价于 HEAD `abb129c`**（`check_proxy_staleness.py` exit 0）→ 无需为部署 restart。

→ 顺带**避免打断姊妹 KB 的探针**（陷阱 1 / 陷阱 20）。
重载链守卫确认**内存索引 == 磁盘索引**（双 KB 均 560/799），下次自动重载 **15:03:58**。

## 五、journal 按进程切片（PID 1844673，2026-11-05 11:02:57 起）

- `Unknown key name` = **0**
- HTTP **500** = **0**
- HTTP **502** = **0**
- `RELOAD FAILED` = **0**
- HTTP 200 = **156**（探针前 130 → 探针后 156，+26 = 本轮 12 次 e2e + 姊妹探针 + health 检查）

端口仅 8643（proxy）+ 8642（gateway），无遗留压测进程。

## 六、本轮提交

```
git add SKILL.md references/crawl-state-2026-11-09.md
git add references/shared-proxy-service-pitfalls.md references/.index-snapshot.json
git commit -m "docs: add 2026-11-09 crawl state (799/560 20th flat), sync shared pitfalls from sister"
git push
```

commit message 用**纯 ASCII**（陷阱 5：含中文会被 tirith `confusable_text` 拦下）。

## 七、遗留

**无**（已 `git status` 核过：本 skill 仓库工作树干净，仅剩被跟踪的
`references/.index-snapshot.json` 这一个良性改动 —— 它每轮刷新，属预期）。

> 姊妹 KB 仓库（`inexbot-knowledge-base`）本轮由它自己的 cron 处置；
> 本 skill **不替它提交**（陷阱 4 的良性竞态原则）。
