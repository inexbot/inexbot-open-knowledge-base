# 爬取状态快照 — 2026-11-17

> 本 KB（`inexbot-open`）每日 cron 轮次的完整快照。
> 姊妹 KB（`inexbot`）的快照在 `~/.hermes/skills/productivity/inexbot-knowledge-base/references/`。

## 一句话结论

**817/560 连续第四次持平**（817 = 11-14 突破 799 后的新基线）——
index.json **2,540,096 bytes 与 11-14/15/16 逐字节相同**（sha1 `40e809118867`）、
verdict=IDENTICAL、**零网络请求**（0 次 `✓`、raw/ 最新仍是 11-14 11:03）、
**4:06.7** 落在稳态带内、md/ 今日零重写、无 `.tmp` 残留；
姊妹 KB 维持 **560**；**8 步标准序列全绿**；**proxy 未 restart**（index 逐字节未变 + 线上源码 AST 等价于 HEAD）。

---

## 1. 爬取

| 项 | 值 |
|---|---|
| 起止 | 11:00:36 → 11:04:43 |
| 耗时 | **4:06.7**（稳态带 3:00–3:50，本轮略高但仍在可接受区间） |
| 发现的页面 | **817**（861 个 hash） |
| 成功 | **817 / 817** |
| 网络抓取次数 | **0**（日志 `✓` 行数 = 0 → 全部命中 `raw/` 缓存） |
| `raw/` 最新 mtime | **2026-11-14 11:03**（早于本次爬取 ⇒ 上游未动） |
| `md/` 今日重写 | **0 个** |
| `.tmp` 残留 | **无**（原子写修复生效） |

**结论：零网络请求的纯缓存复核 ⇒ 817 稳态是硬证据，不是「docs 数持平」的推测。**

### 字节级判据

```
index.json : 817 entries, 2,540,096 bytes, mtime 2026-11-17 11:04:43
locale     : zh=461, en=178, kr=178
verdict    : IDENTICAL to previous crawl (content byte-for-byte unchanged)
              previous: 817 docs, 2,540,096 bytes, 2026-11-16 11:05:15
sha1       : 40e809118867686158149cad5517a9ae3c7307e1
```

⇒ **docs 数持平 + 字节数完全相同 = 真稳态**（而非「docs 数持平 + 字节数不同」那种
需要 `diagnose_byte_change.py` 复核的模糊情形）。

---

## 2. 8 步标准序列

| # | 检查 | 结果 |
|---|---|---|
| 1 | `check_crawl_state.py` | ✅ **IDENTICAL**（817 docs, 2,540,096 bytes） |
| 2 | `check_index_hygiene.py` | ✅ 零宽 0 / 空标题 0 / 幻影 token 可达 0 / 旧 API 可达 0；空 snippet 34（上游空目录页） |
| 3 | `check_retrieval_chain.py` | ✅ **静默降级 ==800 = 0**；短正文 4 条 = 伺服报警占位页 61–71 B |
| 4 | `check_proxy_health.py` | ✅ open **817** + 姊妹 **560**，两个 `loaded=True` |
| 5 | `check_e2e_request.py` | ✅ **12/12 全 200**（见 §4） |
| 6 | `check_proxy_env.py --units` | ✅ 5 个变量 × 三处 sha12 逐项一致（`HERMES_TIMEOUT` sha12=`e49ec846db75` = 1800 ✅） |
| 7 | `check_proxy_staleness.py` | ✅ 线上 PID 1954151 源码 == HEAD `abb129c` → **NOT stale，无需 restart** |
| 8 | `check_reload_timer.py` | ✅ 重载链存活；内存 817 == 磁盘 817 → **in_sync** |

### 补充守卫（本轮额外跑）

| 守卫 | 结果 |
|---|---|
| `check_token_consistency.py` | ✅ **PASS**：inexbot 0 处不一致 / inexbot-open 0 处不一致 |
| `check_shared_pitfalls_structure.py` | ✅ exit 0（两份都完好；3 条 WARN 是不同 section 复用同一 shell 片段 → 正常） |
| `test_shared_pitfalls_structure.py` | ✅ 回归测试 exit 0（完好 → 0；孤儿体 → 1） |
| `diff_shared_pitfalls.py` | ✅ **姊妹独有 section = 0**（详见 §5） |
| md 可达性反查 | ✅ **817/817 全部解析成功**（走 proxy 的 `_md_slug_candidates()`） |

---

## 3. 索引与检索链路细节

### 3.1 检索链路（`check_retrieval_chain.py`）

10 条查询全部命中正文，**静默降级（==800）= 0**：

| 查询 | 代表性 snippet 长度 |
|---|---|
| JSON RPC 上位机 通信 协议 | 3245 / 4000 / 1494 |
| NRC_GetRobotTypeConfig 机器人结构类型 | 1335 / 2844 / 3274 / 4000 |
| servo_point_position_motion_control 运动控制 | 4000 / 1692 |
| ROS 主站 库 二次开发 | 1397 / 4000 / 3673 / 258 / 663 |
| HAL 上位机 接口 | 1024 / 4000 / 1765 / 1948 / 681 |
| 伺服报警 0x0051 IPM故障 | 71 / 61 / 71 / 62 ← **上游占位页** |
| 示教器 换图 | 4000 / 1362 / 440 |
| 通讯协议 地址码 Modbus 寄存器 | 2701 / 4000 / 1378 |
| 冲压工艺 手册 参数设置 | 4000 ×5 |
| 工业机器人控制器 C1102 | 2844 / 3139 / 2367 / 3274 / 2578 |

> ⚠️ **「伺服报警」4 条短正文（61–71 B）不是回归** —— 那是上游本来就只有一行的
> 占位页（与 11-13 / 11-16 基线一致），已用 `_md_slug_candidates()` 核对 md 实际大小。

### 3.2 md 可达性

**817 / 817** 全部通过 proxy 的 `_md_slug_candidates()` 解析到 md 文件，
unresolved = **0**。

> 💡 **本轮又差点踩陷阱 34**（第 7 次）：先用**自写** `crawler.slugify()` 的直连
> 做可达性统计，得到「790 / 817」这个**假阳性**，看起来像 KB 回归。
> 换成 proxy 的 `_md_slug_candidates()` 后立刻变成 817/817。
> ⇒ **再次印证：反查 md 文件必须走 proxy 的 slug 契约，绝不自己重写。**
> 判读口径不变 —— **「检索链路实测正常却报 slug 断裂，几乎一定是检查脚本自己写错了。**

### 3.3 孤儿 md

`md/` 共 **1873** 个文件（1695 locale 前缀 + 178 裸名），
其中 **1083** 个不可达 —— 全部是 10-29 离线重建之前遗留的**死缓存**
（上游改过目录结构，旧 slug 成孤儿）。**架构上不可达**（proxy 只按 index path 定位 md），
**无副作用，不需要处置**。

---

## 4. 端到端请求探针

**12/12 全 200，0 次 502**（连续第 12 天 502 计数为 0）：

| # | 查询 | HTTP | 耗时 |
|---|---|---|---|
| 1–4 | C1102 控制器 通讯接口 有哪些 | 200 ×4 | 52.4 / 90.9 / 55.2 / 67.8 s |
| 5–8 | 冲压工艺 手册 参数设置 | 200 ×4 | 146.1 / 175.0 / 164.7 / 111.6 s |
| 9–12 | 示教器 操作手册 功能说明 | 200 ×4 | 72.9 / 91.1 / 145.8 / **230.3** s |

> **最大的一次 230.3 s** ⇒ 在旧的 300 s 上限下**必然 502**，现在返回 200
> → 再次实证 `HERMES_TIMEOUT=1800` 在真实链路上生效。
> 整轮探针耗时约 **23 分钟**（11:00:37 → 11:23:xx）。

> 💡 **姊妹 KB 的探针同窗口并发**（11:01 起）→ 两边均 12/12 全 200、**0 次 502**
> → 再次印证 11-03 的结论「并发争抢不是 502 根因」。

### journal（按当前进程启动时间切片，928 行）

| 计数 | 值 |
|---|---|
| HTTP 500 | **0** |
| HTTP 502 | **0** |
| `Unknown key name` | **0** |
| `RELOAD FAILED` | **0** |
| `Traceback` | **0** |
| HTTP 200 | 84 |
| HTTP 404 | 15 —— **全是外部扫描器**（`GET /`、`OPTIONS /`、`/nice%20ports,/Trinity.txt.bak`、`/server-info`、`/version`，来源 `101.133.224.200`） |

---

## 5. 共享文件同步（`shared-proxy-service-pitfalls.md`）

| | 行数 | 字节 | sha1 | section 数 |
|---|---|---|---|---|
| 姊妹 | 1678 | 84,106 | `97830fa33e66f916` | 35 |
| 本 skill | **1782** | **89,536** | `d3cf373efa8368db` | **37** |

- **姊妹独有 section = 0** ⇒ 姊妹没有我们缺的东西
- **本 skill 独有 section = 2**：**陷阱 36**（姊妹 agent 会在你的 skill 目录里新建文件
  —— 你不拥有内容，但你拥有路径）、**陷阱 37**（收尾时姊妹改了共享文件 ⇒ 先比对
  `git show HEAD:` 再决定要不要重新提交）

⇒ **同步方向 = 保持本 skill 版本，不 `cp` 覆盖**（盲目 cp 会直接抹掉这两条）。

---

## 6. 本轮闭合的遗留工作（陷阱 14 第 11 次复发）

上一轮（11-16）在本 skill 仓库里留下了**未入库**的改动：

```
 M references/shared-proxy-service-pitfalls.md    ← 陷阱 36 + 陷阱 37，104 行新增
```

核对结果：`git show HEAD:references/shared-proxy-service-pitfalls.md` 只有 **35** 个
section，而工作树有 **37** 个 ⇒ **陷阱 36/37 从未入库**。

> ⚠️ **上一轮报告是 `ok` 结束的，但它的「提交并推送」结论不可信** ——
> 11-16 那轮把姊妹 agent 写进本仓库的两条陷阱留在了工作树里。
> **未跟踪/未提交 = 下次 `git pull` 静默回退** ⇒ 这两条新知识会消失。
> 本轮已闭合入库。

**同时确认**：`scripts/check_token_consistency.py` **已在 HEAD 里**（commit `618bc57`），
姊妹 KB 仓库（commit `39498cf`）也已入库 ⇒ **两边都引用、两边都有实体**，无悬空引用。

---

## 7. 未 restart proxy 的两条理由

1. **内容**：index.json **逐字节未变**（2,540,096 bytes，sha1 `40e809118867`）
   ⇒ 爬前 `/health` 已是 817，爬后必然也是 ⇒ 无需为内容 restart。
2. **部署**：`check_proxy_staleness.py` 判定线上 PID 1954151 加载的源码
   **== HEAD `abb129c`**（AST 指纹一致）⇒ 无需为部署 restart。

重载链活着：定时器线程 tid=1981581 出生于 **09:18:22**（age 1.71h），
上次触发 09:18:22，**下次重载 14:18:22**；内存 817 == 磁盘 817 → **in_sync**。

---

## 8. 端口与遗留进程

- `8643` = hermes-skill-proxy（PID 1954151）、`8642` = gateway（PID 513004）
- **无遗留压测进程**（无 8646 之类）

---

## 9. 下一轮关注点

1. `raw/` 最新 mtime 若不再是 11-14 11:03 ⇒ 上游真的动了 → 需重新评估 817 基线。
2. zh locale（当前 **461**）是否继续增长。
3. 姊妹 KB 560 是否变化。
4. **收尾前必须 `git status` 核过再写「遗留：无」**（陷阱 14）。
