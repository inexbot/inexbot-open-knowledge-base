# Crawl state — 2026-11-13

**KB**: `inexbot-open`（open.inexbot.com）
**结果**：**799/560 连续第二十四次持平（本 KB 纯稳态）** — index.json 与 10-29→11-12 **逐字节相同**。

---

## 1. 爬取

| 项 | 值 |
|---|---|
| 启动 | 11:01:33 |
| 完成 | 11:05:00 |
| **耗时** | **3:26.7**（稳态带 3:00–3:50 内 ✅） |
| 页面 | 799 / 799 成功 |
| index.json | **2,450,869 bytes**（与 10-29→11-12 逐字节相同） |
| mtime | 2026-11-13 11:05:00 |
| 网络抓取次数 | **0**（日志 `✓` 行数 = 0） |
| `raw/` 最新 mtime | **2026-10-23**（早于本次爬取 → 上游零变更） |
| `md/` 今日重写 | **0** |
| `.tmp` 残留 | **无** |

**locale 分布**：zh=443 / en=178 / kr=178（与 11-12 相同）
**md/ 文件**：1855 total（1677 locale-prefixed + 178 stale bare）
**判读**：docs 数持平 + **字节数完全相同** → **真稳态**，上游自 2026-10-10 起 **34 天零新增**。

**姊妹 KB** `inexbot`：本轮 **560**（与 11-12 持平，本 skill 不负责其增长判定）

---

## 2. 8 步标准验证序列 — 全绿

| # | 检查 | 结果 |
|---|---|---|
| 1 | `check_crawl_state.py` | ✅ verdict=**IDENTICAL**（799 entries, 2,450,869 bytes） |
| 2 | `check_index_hygiene.py` | ✅ 零宽 **0** / 空标题 **0** / 幻影 token 可达 **0** / 旧 API 可达 **0**（空 snippet 34 = 上游空目录页，正常） |
| 3 | `check_retrieval_chain.py` | ✅ **静默降级 ==800 = 0**；短正文 4 条 = 伺服报警占位页 61–71 B（上游本来就短） |
| 4 | `check_proxy_health.py` | ✅ open **799** + 姊妹 **560**，两个都 `loaded=True` |
| 5 | `check_e2e_request.py` | ✅ **12/12 全 200**，**0 次 502** → 连续第 **9** 天 502 计数为 0；耗时 36.0–177.3s |
| 6 | `check_proxy_env.py --units` | ✅ 5 个变量在 **线上 environ / 代码默认值 / `/etc` unit / repo 模板** 四处 sha12 逐项一致；`HERMES_TIMEOUT` sha12=`e49ec846db75` = **1800** ✅ |
| 7 | `check_proxy_staleness.py` | ✅ 线上 PID **1844673** 源码 == HEAD `abb129c` → **NOT stale，无需 restart** |
| 8 | `check_reload_timer.py` | ✅ 重载链存活；定时器 tid=1936536（11-13 09:04:49 触发）→ **下次重载 14:04:49**；内存 == 磁盘（inexbot-open 799 == 799） |

**journal 按进程切片**（PID 1844673，since 2026-11-05 11:02:57，2383 行）：
`Unknown key` **0** / HTTP 500 **0** / HTTP 502 **0** / `RELOAD FAILED` **0** / `Traceback` **0** / HTTP 200 = **261**
（全量历史 500=606、502=28 —— 都是几十次重启前的老账，与本轮无关）

**端口**：仅 8643（proxy）+ 8642（gateway），无遗留压测进程。

---

## 3. 本轮闭合的 11-12 遗留（陷阱 14 第 8 次复发）

11-12 那轮结束时，工作树里留着 4 处**已完成但未入库**的工作：

```
 M SKILL.md
 M references/shared-proxy-service-pitfalls.md
?? references/git-push-channel-failures.md
?? scripts/check_git_channel.py
```

⇒ 若被 `git pull` 静默回退，**陷阱 30（github.com:443 假绿）的守卫生效条件会消失**
（`check_git_channel.py` 是「push 失败后快速定性」的唯一脚本）→
**看起来一切正常，实则失去守卫**（静默失效）。本轮已全部 `add` + `commit` + `push`。

**另外修掉一个「半截行」编辑事故**：11-12 遗留的 `M SKILL.md` 里，
第 708 行的 `（**799/560 连续第二十三次持平（本 KB 纯稳态）**：index.json **2,450,869 bytes 与 10-29→11-11 逐字节相同**、`
被删掉了，只留下 `verdict=IDENTICAL、…` → **括号不闭合、句子读起来断裂**。

> ⚠️ **教训**：这是「用 `patch` 改长段落」时的典型事故 —— 删掉的是**两行**里的第一行，
> 而第二行接上来后语法就破了。**判据**：`git diff` 里若某处只有 `-` 没有对应的 `+`，
> 且 `-` 的是段落的**前半截** → 是编辑事故，不是「精简内容」。
> **本轮处置**：用完整的 11-13 段落替换整块（并把 11-12 段落作为「上一轮快照」保留）。

---

## 4. 共享文件同步

- 姊妹 KB 那份 `references/shared-proxy-service-pitfalls.md`：
  **1435 行 / 71,228 B / sha1 `8cb3d16624a6573b6157547708080bfe961d0766`**
- 本 skill 那份：**1435 行 / 71,228 B / sha1 `8cb3d16624a6573b6157547708080bfe961d0766`**
- 姊妹新增 **陷阱 30**（github.com:443 不稳 → socket 探针「假绿」），本 skill 独有行 = 0 → **`cp` 覆盖**
- 同步后复跑 `diff_shared_pitfalls.py` → **exit 0（IDENTICAL）**，30 个 section 标题完全一致

**跨 KB 共享的 `references/git-push-channel-failures.md`**：两边各有一份，内容**不完全一致**
（本 skill 6,763 B vs 姊妹 6,637 B；差异在**开头措辞**与**第 2 步的代码块**，
section 标题集合完全相同）→ 本 skill 那份**保留了姊妹没有的更完整表述**，**未覆盖**。

---

## 5. 并发与 proxy 处置

- **姊妹 KB 本轮与本 skill 同窗口并发**：姊妹 11:01:xx 起自己的 crawler + e2e 探针，
  本 skill 11:01:33 起自己的 crawler + e2e 探针。
  → 两边 **12/12 全 200、0 次 502** → **再次印证 11-03 的结论「并发争抢不是 502 根因」**
  （11-03 隔离复现：姊妹探针退出后单独重跑仍每轮恰好 1 次 502 @ 300.1s）。
  → 本 skill 探针耗时 36.0 / 60.4 / 59.4 / 50.6 / 91.6 / 104.3 / 67.8 / 91.2 /
    177.3 / 132.7 / 168.6 / 127.8 秒 —— **3 次 > 150s**（177.3 / 168.6 / 132.7），
    在旧的 300s 上限下本来可能触发 502，现全部 200 → **`HERMES_TIMEOUT=1800` 持续生效**。
- **本 skill 爬取 3:26.7 落在稳态带内**，与姊妹同窗口并发**未**出现 09-29 那种 1.78x 劣化
  → 再次印证「**不要为避免并发而刻意错开两个 KB 的调度**」。
- **proxy 未 restart**，两条理由：
  1. index.json 逐字节未变 → 无需为内容 restart；
  2. 线上源码 AST 等价于 HEAD `abb129c` → 无需为部署 restart。
  → 顺带**避免打断姊妹 KB 正在飞的探针**（陷阱 1 / 陷阱 20）。

---

## 6. 遗留

**无**（`git status` 已核对：仅剩 `M references/.index-snapshot.json`，属良性 ——
每轮 `check_crawl_state.py` 都会刷新它，且被 git 跟踪）。

---

## 7. 下一轮关注点

1. **github.com:443 通道**（陷阱 30）：本轮 push 前先跑 `scripts/check_git_channel.py` 探针，
   但**记住探针会假绿** —— 真正的判据是 push 本身的结果；
   push 失败后**立即复探**，不通就切 `git push git@github.com:owner/repo.git main:main`。
2. **探针起跑时机**：继续把 e2e 探针放在**轮次最开始**（本轮 11:01 起跑，
   其余 7 步并行做完时探针也已跑到第 4 次请求）。
3. **陷阱 14**：每轮收尾必须 `git status` 核过再写「遗留：无」。
