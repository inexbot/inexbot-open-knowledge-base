# 2026-10-30 爬取状态：799/558 连续第十一次持平 + 闭合 10-29 两项遗留

## 爬取本体：完全稳态

| 项目 | 结果 |
|---|---|
| 爬取页数 | **799 / 799**（0 失败） |
| 耗时 | **3:14**（稳态带 3:00–3:20 内） |
| index.json | **2,450,869 bytes** —— 与 10-29 **逐字节相同** |
| verdict | `IDENTICAL`（`check_crawl_state.py`） |
| 网络请求 | **0**（日志 `✓` 行 = 0；`raw/` 最新 mtime = 2026-10-23） |
| locale 拆分 | zh=443 / en=178 / kr=178 |
| `.tmp` 残留 | 无（原子写正常） |
| 姊妹 KB | 558（同窗口） |

上游**零变化**，连续第 11 次持平（自 2026-10-10 起 20 天零新增）。
index 尺寸 2,450,869 是 10-29 三修落地后的新基线（此前是 2,453,407）。

## 本 cycle 的成果：闭合 10-29 的两项遗留

10-29 那轮修了 3 个缺陷，但「工具额度用尽」留下了 2 项未完成 —— 本轮已全部闭合。

### ① proxy 未用新单元重启 → 已重启并验证

- **判据**：patch 文件 mtime（10-29 12:00:06）**晚于**进程启动时间（10-28 11:08:33）
  → 线上跑的是旧环境 → **符合「补丁『写了』≠ 补丁『上线了』」的陷阱**
- **动作**：`sudo -n systemctl daemon-reload` → `sudo -n systemctl restart hermes-skill-proxy`
- **⚠️ systemd 启动窗口竞态实测**：restart 后**第一次** `check_proxy_health.py`
  直接拿到 `Connection refused`（exit 1）。用 retry 循环（5s × 12）第一次即 200。
  → 与 skill 记录一致：**restart 与健康检查不要串在同一条命令里**，且健康检查本身要带 retry。
- **验证（关键证据）**：
  - 新 PID 的 `/proc/<pid>/environ` 里 4 个变量**全部到位**
    （`PROXY_PORT=8643` / `HERMES_URL=http://localhost:8642` / `HERMES_API_KEY=...` / `SKILL_NAME=inexbot-knowledge-base`）
  - `journalctl -u hermes-skill-proxy` 中 `Unknown key name` **计数 = 0**（10-29 之前每轮都是 4 条）
  - `systemd-analyze verify /tmp/probe-fixed.service` → 对本单元**零告警**
    （注：输出里的 `RestartMode`/`RestartMaxDelaySec` 告警来自 `snapd` / `hermes-gateway`，与本单元无关）
- **行为中性证明**（重要，避免重启引入行为变化）：
  - 旧单元（被忽略的续行写法）→ 线上 proxy 实际用**代码默认值**；
  - 新单元写的值 **逐一等于代码默认值**（`PROXY_PORT=8643` / `HERMES_URL=http://localhost:8642`
    / `HERMES_API_KEY` 的 sha 前 12 位 = `23760f4462da`，与代码默认值一致、len=21）；
  - → 重启后行为**完全不变**，只是把「靠默认值兜底」变成「显式声明」。
  - ⚠️ `SKILL_NAME` 在 proxy 代码里 **grep 命中 0 次** —— 这个变量根本没被用到，
    写不写都一样，属于纯粹的「无害但曾被静默忽略」的那一类。

### ② 改动未提交 → 已 commit + push

| 仓库 | commit | 状态 |
|---|---|---|
| `inexbot-open-knowledge-base` | `7ded09c` | ✅ 已 push（`9264609..7ded09c`） |
| `hermes-skill-proxy` | `001ddfb`（**姊妹 KB 的 cron 并发提交**） | ✅ 已 push（`Everything up-to-date`） |

- 本 KB commit 含：`scripts/crawler.py`（clean_text + 标题兜底链）、`SKILL.md`、
  3 篇新 reference（`crawl-state-2026-10-29.md`、`index-hygiene-and-systemd-env-bugs.md`、
  `proxy-memory-vs-disk-comparison.md`）、`references/retrieval-chain-verification.md`、
  `references/.index-snapshot.json`
- ⚠️ **姊妹 KB 的 cron 与本 skill 同窗口跑时会并发提交同一个 proxy repo** ——
  本轮 `git commit` 撞上姊妹 KB 的提交，报 `nothing to commit, working tree clean`。
  这是**良性竞态**（内容一致，不会互相覆盖），但要认得这个报错含义，别以为提交失败。

### ③ 新坑：姊妹 KB 的 cron 会在同窗口 restart proxy

- 观测：本轮 11:15:35 我 restart → PID 1779750；**11:16:37 姊妹 KB 又 restart 了一次** → PID 1779868。
- 后果：11:16:37–11:16:44 有约 7s 代理不可用窗口，
  恰好把我那次 HTTP 探针打成 `RemoteDisconnected`（**不是检索崩了**）。
- 判读：`RemoteDisconnected` ≠ 500。500 才是检索崩。
  看到连接被重置先 `ps`/`systemctl status` 确认是不是被并发 restart 了。
- 姊妹 KB 的 commit `001ddfb` 还额外修了 `User=inexbot`（该用户不存在 → systemd 起不来）
  和 LF 行尾 —— 部署版 `/etc` 仍是 `User=ecs-user`（正确），**不要**用 repo 模板直接覆盖 `/etc`。

## 验证结果

| 检查 | 结果 |
|---|---|
| `check_crawl_state.py` | ✅ IDENTICAL（799 条，2,450,869 bytes，与 10-29 逐字节相同） |
| `check_proxy_health.py` | ✅ open=799 / inexbot=558 / loaded=True |
| `check_retrieval_chain.py` | ✅ 静默降级(==800)=**0**、异常=False；4 条 <200 为姊妹 KB 上游占位报警页 |
| index 卫生 | ✅ 零宽字符标题=0、空标题=0、幻影 token 可达数=0 |
| index → md 解析 | ✅ 799/799 全部命中，miss=0 |
| 活体 HTTP 探针 | ✅ HTTP 200 + 真实 KB 内容（重启前）；重启后转 `RemoteDisconnected`（姊妹 KB 并发 restart 所致，非故障） |
| 端口 | ✅ 只有 8643(proxy) + 8642(gateway)，无遗留压测进程 |

## 遗留待办

1. **`md/` 仍有 1,855 文件 vs 799 索引条目**（1,677 带 locale 前缀 + 178 个旧版无前缀死缓存）
   —— 按 skill 记录属无害死缓存（proxy 只按 index path 定位），**未清理**。
2. **姊妹 KB `inexbot-knowledge-base` 工作区**：`SKILL.md`、
   `references/kb-cron-verification-workflow.md`、`references/proxy-runtime-freshness.md`
   三个文件仍是未提交状态 —— **那是它自己 cron 的职责，本 skill 不代提交**。
3. `references/.index-snapshot.json` 每次爬取都会刷新（本次已随 commit 一起入库）。

## 流程观察

- 本轮 crawler 与姊妹 KB **完全同窗口**（11:01:20 启动），耗时 3:14 → 稳态带内，
  再次印证「两个 KB 不需要错开调度」。
- `execute_code` 沙盒 inline `os.kill` + `time.sleep(15)` 循环等长任务：
  一次调用等完（195s），比 `wait_pid.py` 更省一次 spawn 延迟。沙盒需显式 `import time`。
- **git commit 消息含中文会触发 tirith 的 `confusable_text` 扫描拦截**（ASCII 混排被判 homoglyph 风险）
  → **commit message 用纯 ASCII**。这与 skill 里记录的「emoji 变体选择符会被拦」是同一类问题。
