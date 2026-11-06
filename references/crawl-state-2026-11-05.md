# 爬取状态快照 — 2026-11-05

> 纳博特开放平台知识库（`inexbot-open`）每日爬取快照。
> 姊妹 KB：`inexbot-knowledge-base`（doc.inexbot.com）。

## 一、总体结论

**799/558 连续第十六次持平（纯稳态）**，且本轮**闭合了 11-04 遗留的 502 修复部署项**。

| 项目 | 值 |
|---|---|
| 爬取页数 | **799 / 799 成功，0 失败** |
| 耗时 | **3:47.2**（稳态带 3:00–3:50 内，姊妹 KB 同窗口并发） |
| 网络请求 | **0**（全部命中 `raw/` 缓存；日志 `✓` 行数 = 0） |
| `raw/` 最新 mtime | **2026-10-23 11:18**（未动，纯缓存命中） |
| `index.json` | **2,450,869 bytes**（与 10-29 → 11-04 逐字节相同） |
| locale 拆分 | en=178 / kr=178 / zh=443 |
| `md/` 文件 | 1855 total（1677 locale-prefixed + 178 stale bare） |
| 漂移 verdict | **IDENTICAL**（与 11-04 快照逐字节相同） |
| `md/` 今日重写 | **0** 个文件 |
| `raw/` 今日重写 | **0** 个文件 |
| `.tmp` 残留 | **无**（原子写生效） |

## 二、本轮关键动作：502 修复**已部署上线**（闭合 11-04 遗留第 1 项）

11-04 的姊妹 KB 报告把「`HERMES_TIMEOUT=1800` 已写入 unit 与 repo 模板，但**尚未 restart 部署**」
列为「下一轮必须先接手」的遗留项。本轮已全部执行完毕：

| 步骤 | 结果 |
|---|---|
| `sudo -n systemctl daemon-reload` | exit 0 |
| `sudo -n systemctl restart hermes-skill-proxy.service` | exit 0，**新 PID 1844673**（旧 PID 1792095 启动于 10-31） |
| `/proc/<pid>/environ` 验证 | `HERMES_TIMEOUT` **已到位**（len=4, sha12=`e49ec846db75` = "1800"） |
| 其余 4 个环境变量 | 全部到位，`HERMES_API_KEY` len=21 / sha12=`23760f4462da` = **代码默认值**（未被脱敏污染） |
| `/health`（带重试） | **OK**（inexbot-open 799 + inexbot 558，`loaded=True`） |
| proxy repo commit | **`846b3de`**（纯 ASCII message），已 push，`a331618..846b3de` |

> ⚠️ **「补丁『写了』≠ 补丁『上线了』」的教科书案例**：
> unit 文件从 **11-04 11:36:49** 起就带着 `HERMES_TIMEOUT=1800`（`/etc` 与 repo 模板**两份都改对了**），
> 但线上进程 **10-31 11:36:48** 启动 → **早于补丁 4 天** → 一直跑的是旧代码（300s 上限）。
> 判据：`/proc/<pid>/environ` 里**有没有**这个变量，而不是「unit 文件里有没有」。
>
> 💡 本轮选择 restart 的时机：11:02 时**两个 crawler 都在跑，但没有任何 probe 在飞**
> （`ps` 确认只有 `crawler.py`）→ 是当日最安全的窗口，restart 不会打断姊妹 KB 的探针。

### ⚠️ 关于 `hermes...arch` / `hermes...rch` 的误读（再次确认）

用 `grep`/`cat` 看 unit 文件时，Hermes 的**输出脱敏**会把密钥渲染成带省略号的形式
（`hermes...rch` len=12、`hermes...arch` len=13），**看起来像被截断的占位符**。
实测两者**都是脱敏假象**：
- 部署版 unit 的真实值 len=**21**、sha12=`23760f4462da`
- 线上进程的 `/proc/<pid>/environ` 真实值 len=**21**、sha12=`23760f4462da`
- 代码默认值 `hermes-website-search` len=21、sha12=`23760f4462da`

→ **三者完全一致**，部署版**没有**截断污染。
**判读方式必须用 sha 摘要，不要看裸字符串**（姊妹 KB `shared-proxy-service-pitfalls.md` §陷阱 9）。

## 三、验证闭环（5 步标准序列全绿）

| 步骤 | 结果 |
|---|---|
| `check_crawl_state.py` | **IDENTICAL**，799 entries / 2,450,869 bytes |
| `check_index_hygiene.py` | **exit 0** —— 零宽字符 **0** / 空标题 **0** / 幻影 token `cppset_tool_hand_number` 可达 **0** / 旧 API `star_servo_...` 可达 **0**；空 snippet **34**（上游空目录页，预期值） |
| `check_retrieval_chain.py` | **exit 0** —— 静默降级(==800) **0**；`snippet_len` 实测 2367 / 3274 / 2578 / 4000 / 4000 全为正文命中；短正文(<200) **4** 条 = 上游伺服报警占位页（`0x0008/0x000B/0x0050/0x0051`，与 10-25 基线一致） |
| `check_proxy_health.py` | **exit 0** —— inexbot-open **799** / inexbot **558**，均 `loaded=True` |
| `check_e2e_request.py` | **12/12 全 200**，42.9s – 152.6s，**零 502**（3 query × 4 runs） |

### e2e 探针细节（本轮是修复后的首次回归）

| query | 4 次耗时 | 状态 |
|---|---|---|
| `C1102 控制器 通讯接口 有哪些` | 108.1 / 49.6 / 42.9 / 69.1 s | 4/4 = 200 |
| `冲压工艺 手册 参数设置` | 93.1 / 101.5 / 95.8 / 152.6 s | 4/4 = 200 |
| `示教器 操作手册 功能说明` | 131.3 / 81.8 / 92.8 / 131.5 s | 4/4 = 200 |

→ **修复前**（300s 上限）这三类长手册查询会随机 502（11-03 实测 `p90=153s p95=471s max=1457s`，
4 次 > 300s）；**修复后**本轮 12 次全部落在 42.9–152.6s，**无一触到 300s 边界** → 0 502。

### 进程切片后的 journal 计数（按当前 PID 1844673 切片）

| 指标 | 计数 |
|---|---|
| `Unknown key name` | **0** |
| HTTP **500** | **0** |
| HTTP **502** | **0** |
| `RELOAD FAILED` | **0** |

### 服务与端口

- `NRestarts=0`（本次是人工 restart，不是崩溃重启）
- 端口干净：仅 **8643**（proxy，PID 1844673）+ **8642**（gateway，PID 513004）
- 无遗留压测进程（`ss -ltnp | grep 864[0-9]` 只有这两条）
- **重载链代码已带 try/except/finally**（`hermes-skill-proxy.py:195-205`：
  `print(f"[proxy] RELOAD FAILED: ...", file=sys.stderr, flush=True)` + `finally` 里重新排期）
  → 一次回调异常**不会**让定时器链条永久断裂

## 四、共享文件同步

`references/shared-proxy-service-pitfalls.md` 两份已**完全一致**：

```
sister  695 lines  34177 bytes  sha1=fcb7c00f4b671bcaa4980db3746189707c28fd30
ours    695 lines  34177 bytes  sha1=fcb7c00f4b671bcaa4980db3746189707c28fd30
```

`diff_shared_pitfalls.py` → **IDENTICAL — nothing to sync**（exit 0）。
本 skill 工作树里那 138 行未提交 diff 正是**陷阱 17–19**（姊妹 KB 11-03 写的，
已被姊妹 KB 在 11-04 的 commit `131c7fd` 收录），我们这份已追平 → 本轮随 commit 一并入库。

## 五、本轮踩到 / 复核的坑

1. **`terminal(foreground)` 的 60s clamp 又中了一次** —— 跑 `check_e2e_request.py` 时被
   `Command timed out after 60s` 打断，**但那个 probe 进程其实没死**（`timeout 900` 包装仍在跑），
   于是变成**两个 probe 并发**。已 `kill` 掉重复的那个（1845300/1845302），
   保留单实例重跑到 12/12 —— 否则两个完整 agent 跑同时压 gateway，会污染 502 判定
   （11-03 已证实「并发争抢不是根因但会加剧」）。
   → **正确姿势**：e2e 探针一律 `terminal(background=true)`；跑之前先 `ps` 确认**没有别的 probe 在飞**。
2. **`execute_code` 沙盒 5 分钟上限** —— 等待长任务时用 `os.kill(pid,0)` 循环，
   但 `execute_code` 自身 300s 会被杀 → 需要**分段等待**（每次 ≤280s），不要指望一次等到底。
3. **`grep` 看密钥会被脱敏** → 一律用 sha 摘要判读（见第二节）。
4. **姊妹 KB 11:07 起也在跑自己的 e2e 探针**（`/tmp/e2e-inxbot-20261105.log`）
   → 本轮 restart 抢在了它启动**之前**（11:02:57 vs 11:07），
   未打断对方（对方 11-04 遗留第 3 项提到的「姊妹探针日志未落盘」本轮已落盘 ✅）。

## 六、遗留事项

| # | 事项 | 归属 | 状态 |
|---|---|---|---|
| 1 | `HERMES_TIMEOUT=1800` 部署 | 本 KB | ✅ **本轮已闭合**（restart + 验证 + commit `846b3de` + push） |
| 2 | `verify_kb.py` 的 4 项 `[inexbot-open]` FAIL（1855 vs 799 死缓存 / 零长度 snippet / 含图反查 73/177） | 姊妹 KB 范围 | 沿用 11-03 结论：历史遗留且**架构上不可达**，但**新引入算回归** |
| 3 | 姊妹 KB 探针日志缺失 | 姊妹 KB | ✅ 本轮已落盘 `/tmp/e2e-inxbot-20261105.log` |
| 4 | **注入体积偏大**（单库 top-5 = 11.3k–21.0k 字符） | 需人工权衡 | **未决** —— 降体积会牺牲长手册正文完整度，属产品决策，两 KB 共用链路，不单方面改 |

## 七、提交状态

| 仓库 | HEAD | 状态 |
|---|---|---|
| `inexbot-open-knowledge-base` | 本轮 commit | ✅ 待 push（见当轮报告） |
| `hermes-skill-proxy` | **`846b3de`** | ✅ 已 push，`a331618..846b3de`，工作树干净 |
| `inexbot-knowledge-base`（姊妹） | `131c7fd` | 有未提交改动（`M SKILL.md` + 2 个 `??` reference）→ **本 skill 不代提交**，仅报告点名 |

## 八、本轮新增的可复用资产

| 文件 | 用途 |
|---|---|
| `scripts/check_proxy_env.py` | **「补丁真的上线了」守卫**：校验线上 `/proc/<pid>/environ` 的 5 个环境变量是否到位且等于代码默认值；`--units` 时额外比对 `/etc` 部署版与 repo 模板两份 unit。hash-only 输出（避免密钥明文 + Hermes 输出脱敏误判）。exit 0/1/2 |
| `references/proxy-deployment-verification.md` | 完整分析：①「文件在磁盘 / systemd 知道 / 进程带着」三个「在」的区分；② 2026-11-05 的「补丁滞留 4 天」现场；③ sha 摘要判读法与脱敏陷阱表；④ restart 的最佳时机（无 probe 在飞的窗口）；⑤ 三层 timeout 改动要同时改的三处；⑥ 并发 commit 良性竞态的判读 |
| `SKILL.md` | 新增「什么时候该 restart proxy」一节 + 「跑 e2e 探针的两个前置条件」一节；标准验证序列新增第 6 步（可选，改过 unit/proxy 后必跑） |
