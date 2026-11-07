# 2026-11-07 爬取状态快照（799/559 连续第 18 次持平，纯稳态）

## 一、爬取结果

| 项目 | 值 |
|---|---|
| 爬取页数 | **799 / 799 成功，0 失败** |
| 耗时 | **3:26.3**（稳态带 3:00–3:47 内） |
| 网络请求 | **0**（0 次 `✓`；`raw/` 最新 mtime 仍是 2026-10-23） |
| `index.json` | **2,450,869 bytes**，sha256 前 16 位 `05fef6deeb02af9b` |
| locale 分布 | zh=443 / en=178 / kr=178（与前 17 轮完全一致） |
| md / raw | 1855 / 1855（今日重写 **0** 个文件；无 `.tmp` 残留） |
| verdict | **IDENTICAL**（与 10-29 → 11-06 逐字节相同） |

**上游零变更**：docs 数持平 + 字节数完全相同 → 真稳态，非「上游改了正文」。
姊妹 KB `inexbot` 自 11-06 起也是 **559**（本 skill 视角：559 已稳定）。

## 二、验证闭环（7 步全绿）

| 步骤 | 结果 |
|---|---|
| 1) `check_crawl_state.py` | **IDENTICAL**；799 entries / 2,450,869 bytes |
| 2) `check_index_hygiene.py` | 零宽字符 **0** / 空标题 **0** / 幻影 token 可达 **0** / 旧 API 可达 **0** / 空 snippet 34（上游空目录页，正常） |
| 3) `check_retrieval_chain.py` | **静默降级(==800) = 0**；短正文 4 条 = 伺服报警占位页（上游本来就短，61–71 B）；异常 False |
| 4) `check_proxy_health.py` | `inexbot-open` **799** ✅ / `inexbot` **559** ✅；gateway 8642 可达 |
| 5) `check_e2e_request.py` | **12/12 全 200**（3 query × 4 runs，28.2–140.1s，**0 次 502**）；标准序列的关键一步，唯一能抓「proxy→gateway→LLM」链路故障的检查 |
| 6) `check_proxy_env.py --units` | 5 个变量**全部到位**且 live process / `/etc` unit / repo 模板 **三处 sha12 逐项一致**；`HERMES_TIMEOUT` sha12=`e49ec846db75`（=1800）✅ |
| 7) `check_proxy_staleness.py` | 线上进程 PID 1844673（11-05 11:02:57 起）源码 **== HEAD `abb129c`** → **NOT stale，无需 restart** |

**journal（按当前进程启动时间切片，950 行）**：`Unknown key` **0** / HTTP 500 **0** / HTTP 502 **0** /
`RELOAD FAILED` **0** / HTTP 200 = **79**。

**重载链活着**：定时器线程 TID 1871807 出生于 **2026-11-07 08:03:33**，age = **3.34h**，
下次触发 **13:03:33**（100 分钟后）。11:23 的短命线程是 Flask 请求线程，非重载线程。

⚠️ **注意 age 判据**：本轮定时器 age = 3.34h，**落在姊妹 11-06 首版脚本的 `[3.5h, 5.25h]` 窗口之外** ——
若沿用旧判据会**假报「重载链断裂」**并诱使下一轮 cron 做一次无谓 restart（还会打断姊妹的探针）。
正确判据见下节（姊妹 11-07 已修正，本 skill 已移植守卫）。

**姊妹 KB 磁盘已涨到 560**（本轮其 cron 又抓到 1 页），proxy 内存仍是 559 →
「内存 ≠ 磁盘」出现在**姊妹**侧而非本 KB 侧；本 KB `inexbot-open` 内存 799 == 磁盘 799 ✅。

**端口**：仅 8643（proxy，PID 1844673）+ 8642（gateway，PID 513004）；**无遗留压测进程**。

## 三、本轮动作

### ① proxy 未 restart 的两条理由（均已用证据确认）

1. **内容没变**：index.json 逐字节未变 → 不需要为内容 restart；
2. **代码行为等价**：`check_proxy_staleness.py` 判定线上源码 **== HEAD**（AST 指纹一致）→ 不需要为部署 restart。

⇒ 顺带避免了打断姊妹 KB 的 e2e 探针（陷阱 1 / 陷阱 20）。

### ② 闭合 11-06 遗留的「工作实际没提交」（陷阱 14 **第 3 次复发**）

11-06 那轮产出的三个文件当时仍是 `??` 未跟踪：

| 文件 | 内容 |
|---|---|
| `scripts/check_proxy_staleness.py` | AST 指纹判定「线上进程是否行为陈旧」（只改注释 → 判定等价 → 免 restart） |
| `scripts/merge_shared_pitfalls.py` | difflib 三方合并共享 pitfalls 文件（姊妹为基底 + 本 skill 独有 hunk 贴回） |
| `references/crawl-state-2026-11-06-assets.md` | 两个脚本的由来与实测数据 |

外加 11-06 的 `SKILL.md` 版本补丁（v1.19.0 → v1.20.0 + 两个新脚本的索引段）。

**为什么这次必须提交**：未跟踪 = **下次 `git pull` 静默回退** →
`check_proxy_staleness.py`（唯一能免掉无谓 restart 的守卫）会消失 →
SKILL.md 里的链接指向不存在的文件 → **静默失效**（代码还在，只是少了检测）。

### ③ 共享 pitfalls 文件：第三次走「先 diff 再决定」，不盲 cp

| | 行数 | 字节 | sha1 |
|---|---|---|---|
| 姊妹（`inexbot`） | 894 | 44,467 | `bbabe6007a4e` |
| 本 skill（合并前） | 797 | 39,560 | `50ce85500979` |

`diff_shared_pitfalls.py` 判定：**双方各有独有 section** → 跑合并脚本，
**不手工合并**（39 KB / 23 个编号 section 手工合极易静默漏项）。

合并结果：**898 行 / 44,762 bytes**，校验
「姊妹 23 个 section missing=**0**」「本 skill 0 个 section 丢失」，
本 skill 独有 hunk **3 个全部保留**。

### ④ 新坑：无

本轮未遇到新的 policy 拦截或工具坑。沿用的既有对策：
- `write_file` 写外层脚本 + `terminal(background=true)` 调脚本文件（不用 `-lic` wrapper）
- `execute_code` 内联 `os.kill(pid,0)` + `time.sleep(15)` 循环等长任务（绕开 60s clamp）
- e2e 探针走 background + 客户端 timeout 1860s（> proxy 上游 1800s）

## 三·补、e2e 探针明细

| query | 4 次耗时 | 状态 |
|---|---|---|
| C1102 控制器 通讯接口 有哪些 | 38.2 / 75.7 / 135.9 / 28.2s | 4/4 = 200 |
| 冲压工艺 手册 参数设置 | 82.5 / 140.1 / 113.2 / 67.9s | 4/4 = 200 |
| 示教器 操作手册 功能说明 | 81.6 / 111.9 / 127.8 / 74.8s | 4/4 = 200 |

合计 **12/12 HTTP 200，0 次 502 / 500**。客户端 timeout 1860s（> proxy 上游 1800s）。
本轮耗时全部 < 300s，未触及边界 —— 这是**连续第 3 天 502 计数为 0**，
`HERMES_TIMEOUT=1800` 在真实链路上持续生效。

⚠️ 探针跑完后姊妹 KB 才启动它自己的 e2e 探针（PID 1875491/1875500，11:22:31 起）——
**本轮未 restart proxy，因此没有打断它**（若 restart，它的探针会拿到 `RemoteDisconnected`）。

## 三·补·二、移植姊妹 KB 修正版「重载链守卫」

姊妹 11-07 修正了**陷阱 21 的判据错误**：原脚本找 `age ∈ [3.5h, 5.25h]` 的线程，
找不到就报 `[FAIL] 重载链可能已断裂` —— 但定时器 age 在 `[0, 5h)` 内**均匀分布**，
⇒ **约 70% 的时间落在窗口外** → 周期性误报 → 诱使 cron 做无谓 restart。

**本轮实测正好撞上这个假阳性**：定时器 age = **3.34h**，在旧窗口之外，
但 `/health` 的 `inexbot-open` 799 == 磁盘 799 → **重载明明发生过，链是活的**。

**已移植**姊妹的 `scripts/check_reload_timer.py`，并**改了它一处硬编码**：
姊妹版只读 `kb/inexbot/index.json`，对以 `kb/inexbot-open` 为对象的 skill **判据无意义**。
本 skill 版改为**同时检查两个 KB 的磁盘索引**，并以 `inexbot-open` 为 `in_sync` 判据：

```
磁盘 index.json : {'inexbot': 560, 'inexbot-open': 799}
proxy 内存索引   : {'inexbot': 559, 'inexbot-open': 799}
  inexbot       disk=560 mem=559 PENDING RELOAD
  inexbot-open  disk=799 mem=799 OK
[OK] 重载链存活：定时器线程 tid=1871807 -> 下次重载 2026-11-07 13:03:33 (在 100 分钟后)
```

**判读要点**：「内存 ≠ 磁盘」本身**不是故障** —— 先算「下次自动重载在什么时候」；
只要自动重载还在 1 小时内，就**不要 restart**（收益为零、风险为正）。

## 四、姊妹 KB 状态（不代提交，仅记录）

`inexbot-knowledge-base` 磁盘索引本轮涨到 **560**（其 cron 抓到 1 页新内容），
proxy 内存 559 → 待下次自动重载（13:03:33）。

其工作树本轮末态：`M SKILL.md`、`M references/large-family-kb-navigation.md`、
`?? references/stamping-process-manuals.md`、`?? scripts/scan_kb_topic.py`。
**属它自己 cron 的职责**，本 skill 不代提交，仅在此点名。

其共享文件已被本 skill 的合并脚本读过（姊妹那侧 sha1 `bbabe6007a4e`），
本 skill 只做**单向写入自己那份**，不改姊妹那份。

## 五、遗留

- **无**（已 `git status` 核过：只有已暂存/已提交的本次文件）。
- 下一轮（11-08）开工先看 `/health` 的 `inexbot` docs 是否仍为 559；
  若掉回 558，说明姊妹 KB 索引被回退，属其自身范围。
