# 2026-11-15 爬取快照（inexbot-open）

## 结论

**817/560 连续第二次持平（817 为 11-14 首次突破 799 后的新基线）**：index.json
**2,540,096 bytes 与 11-14 逐字节相同**（sha1 `40e809118867`）、
verdict=IDENTICAL、**零网络请求**（0 次 `✓`、raw/ 最新仍是 11-14 11:03）、
**3:46.5** 落在稳态带内、md/ 今日零重写、无 `.tmp` 残留；姊妹 KB 维持 **560**。

## 本轮关键发现

### ① 11-14 那轮被 HTTP 429 打断，但**爬取本身已完成**

`hermes cron list` 显示 11-14 最后一轮 `error: RuntimeError: HTTP 429`。
按「上一轮带 `error:` → 报告正文结论一律作废」的纪律，本轮独立核对：

- 磁盘上 index.json 已是 **817 条 / 2,540,096 bytes**（11-14 11:05:08 落盘）；
- `scripts/check_proxy_health.py` 的 `BASELINES` 已被改成 `inexbot-open: 817`；
- `raw/` 有 **18 个文件在 11-14 11:03:33 被真正抓取**（zh Python SDK 接口 13 个、
  C++ 示例 2 个、控制器文档 2 个、EtherCAT 排障 1 个）→ **11-14 的 +18 是真实上游增长**。

⇒ 429 打断的是**收尾阶段**（commit/push），不是爬取阶段。
⇒ 但 trap 14 依然生效：11-14 的**报告正文里「已提交」的说法一律作废** ——
本轮 `git status` 实测确有 **5 个修改 + 1 个未跟踪文件**没入库
（`M SKILL.md` / `M references/.index-snapshot.json` /
`M references/cron-completion-discipline.md` / `M references/shared-proxy-service-pitfalls.md` /
`M scripts/check_proxy_health.py` / `?? scripts/check_shared_pitfalls_structure.py`）
→ **陷阱 14 第 9 次复发**，本轮已闭合。

### ② 🔴 `check_shared_pitfalls_structure.py` 修好了：原本是**假警报守卫**

11-14 留下的这个未跟踪脚本有个严重缺陷：
它把**任何重复的长行**都判成 FAIL。而共享 pitfalls 里**不同 section 复用同一段 shell 片段是正常的**
（trap 1 的诊断命令 vs trap 20 的决策流程都含 `ps -o pid,lstart,etime -p $(pgrep -f ...)`）
⇒ 脚本对**结构完好**的真实文件稳定返回 **exit 1** → 变成「天天误报的假警报」，
比没有守卫更糟（会诱使下一轮 cron 去「修」一个不存在的问题）。

本轮修了三处：

1. **重复长行降级为 `WARN`**（不计入退出码）—— 合法复用不再误报；
2. **`block_hashes` 算了却从没用过** → 真正实现「重复块 / 孤儿块」检测；
3. 孤儿块检测用**固定长度前缀签名**（`SIG_LINES = 8`）而非「整段正文」——
   ⚠️ **踩到的坑**：最后一个 section 的正文延伸到 EOF，若孤块恰好是它的复制体，
   「整段正文」签名会**把孤块吸进自己** → 签名改变 → 反而找不到重复（实测 exit 0 漏报）；
   固定长度前缀签名不受 EOF 吸收影响。

**回归测试**（`/tmp/test_structure_guard.py`）双用例通过：
真实完好文件 → exit 0；人为追加 54 行无标题孤儿体 → exit 1 并报出
`DUPLICATE_BLOCK section body of '陷阱 29：...' appears 2 times`。

### ③ 「31 行孤立删除」不是半截行事故，是陷阱 31 本身要修的东西

`git diff` 里唯一的 `[ORPHAN-REMOVE]` 块（31 行、只有 `-` 没有 `+`）看着像
「半截行编辑事故」，实则是**陷阱 31 修的就是这个**：
文件末尾曾有一整段陷阱 27 的**孤儿块**（有正文、无自己的 `## 陷阱 27：` 标题）。
本轮逐行核对：陷阱 27 的正式 section（行 1179–1214）**内容完整**，
`陷阱 23 给了同步方向的判据` / `### 现场（2026-11-10）` / `### ✅ 正确时序` /
`核对 sha1 要放在最后一步` 四个标记**全部在位** → 删掉的是末尾重复体，**不是**正文。
⇒ 判读这类 diff 时，**必须先确认被删的那份在别处是否有完整对应**，再判是不是事故。

## 8 步标准序列

| 步骤 | 结果 |
|---|---|
| 1 crawl_state | **IDENTICAL**（817 / 2,540,096 bytes，与 11-14 逐字节相同） |
| 2 index_hygiene | 零宽 **0** / 空标题 **0** / 空 snippet 34（上游空目录页，正常）/ 幻影 token 可达 **0** / 旧 API 可达 **0** → exit 0 |
| 3 retrieval_chain | **静默降级 ==800 = 0**；短正文 4 条 = 伺服报警占位页 61–71 B（上游本来就短）→ exit 0 |
| 4 proxy_health | open **817** + 姊妹 **560**，均 loaded=True → exit 0 |
| 5 e2e 探针 | 12/12 全 200（见下），**0 次 502** → 连续第 10 天 502 计数为 0 |
| 6 check_proxy_env --units | 5 个变量三处 sha12 逐项一致（`HERMES_TIMEOUT` sha12=`e49ec846db75` = 1800 ✅）→ exit 0 |
| 7 check_proxy_staleness | 线上 PID 1954151（11-14 11:17:36 起）源码 == HEAD `abb129c` → **NOT stale，无需 restart** |
| 8 check_reload_timer | 重载链存活（定时器线程 tid=1959345，07:17:55 触发 = start+20h 第 4 次 5h 排期，下次重载 12:17:55）；内存 817 == 磁盘 817 → **in_sync** |

补充：`check_shared_pitfalls_structure.py` 两份真实文件 → exit 0（修好之后）；
`diff_shared_pitfalls.py` → IDENTICAL（两份 sha1 均 `da8d63f40507`）。

journal 按进程切片（PID 1954151，35 行）：`Unknown key` **0** / HTTP 500 **0** /
HTTP 502 **0** / `RELOAD FAILED` **0** / `Traceback` **0** / HTTP 200 = 6。
端口仅 8643（proxy）+ 8642（gateway），无遗留压测进程。

## 未 commit 的工作（本轮已闭合）

11-14 遗留 5 个 `M` + 1 个 `??` → **陷阱 14 第 9 次复发**，本轮已 add + commit + push。
另外本轮新修的结构自检脚本 + 回归测试一并入库。

## proxy 未 restart 的两条理由

① index.json 逐字节未变（2,540,096 bytes 与 11-14 相同）→ **无需为内容 restart**；
② 线上源码 AST 等价于 HEAD `abb129c` → **无需为部署 restart**。
→ 顺带避开打断姊妹 KB 正在飞的 e2e 探针（陷阱 1 / 陷阱 20）。

## 并发观察

姊妹 KB 与本 skill **同窗口并发**（姊妹 11:00 起自己的 crawl + e2e 探针）。
两边探针同时在飞 → 再次印证 11-03 的结论「**并发争抢不是 502 根因**」。
