# 端到端请求探针（`scripts/check_e2e_request.py`）

**唯一能抓到「proxy → gateway → LLM」整条链路故障的检查。**

来源：姊妹 KB `inexbot-knowledge-base` 2026-10-31 编写，本 KB 2026-11-01 移植。

## 为什么前 4 步不够

2026-10-31 姊妹 KB 发现了一个**真实用户故障**：proxy 转发到 gateway 的 read timeout
被硬编码成 120s，而 KB 注入后 system prompt 达 12k–20k 字符、gateway 实测需 **30–140s**
→ 用户查「冲压工艺手册参数」这类**命中长手册**的问题时**随机 502**（实测 2/4 失败，
2 次精确卡在 120.1s）。

**当时所有常规检查全绿**：

| 检查 | 结果 |
|---|---|
| `/health` | ✅ `{"status":"ok", ...}` |
| `check_retrieval_chain.py` | ✅ 正文命中，无 800 字降级 |
| 引用链接实网抽样 | ✅ 12/12 HTTP 200 |
| md slug 契约 | ✅ 558/558 |

**只有真正打一次完整请求才暴露。** 所以这步不能省，也不能用前 4 步替代。

## 用法

```bash
/usr/bin/python3 ~/.hermes/skills/productivity/inexbot-open-knowledge-base/scripts/check_e2e_request.py
# 默认每查询打 4 次，共 3 个查询
/usr/bin/python3 scripts/check_e2e_request.py --runs 6
/usr/bin/python3 scripts/check_e2e_request.py --query "冲压工艺 手册 参数设置"
/usr/bin/python3 scripts/check_e2e_request.py --gateway-probe   # 额外直打 8642 量真实耗时
```

⚠️ **必须用 `/usr/bin/python3`** —— 沙盒 `python3` 没装 flask / requests。
⚠️ **客户端 timeout 必须 > proxy 的上游 timeout**（现 300s）→ 默认 360，别调小。
⚠️ **timeout 类故障是随机的** —— 单次 200 **不能**证明通过，必须连打多次。

## 原理

脚本故意用**不存在的 model**（`definitely-not-a-real-model-xyz`），
让 gateway 快速拒绝，从而**快速区分两条路径**：

```
proxy_request() → search_all_kb() 先跑 → 再转发 gateway
                        │
                        ├─ 抛异常 → Flask 默认处理器 → HTTP 500（快，几秒）
                        └─ 成功   → 转发 gateway → 502（gateway 超时）或 200
```

## 状态码判读表

| 现象 | 含义 | 动作 |
|---|---|---|
| **200** | ✅ 全链路通 | 但**单次不作数**（timeout 类是随机的） |
| **500** | 🔴 **检索真的崩了** | slug 契约断裂 / index 读取异常 → 查 `_md_slug_candidates()` 与 crawler `slugify()` |
| **502** | gateway 侧超时，**检索多半成功** | 量网关真实耗时；> proxy timeout 就必然 502，与 KB 无关 |
| **RemoteDisconnected** | ⚠️ **大概率被并发 restart 打断** | 查 PID + journal，**不是**检索故障 |
| **000 / ERR** | 客户端 timeout 给太小 | 用 `-m 360`（proxy 上游是 300s） |

> 📌 完整版（含并发 restart 判读）见 `references/shared-proxy-service-pitfalls.md` §陷阱 1、3、10。

## 判读「502 是 timeout 还是真慢」

直接打 gateway 绕过 proxy，用真实注入量级的 system prompt：

```bash
# 小 prompt ~1.4s；12k 字符 KB prompt ~64s；35k 字符 ~135-161s
```

只要**真实耗时 > proxy 的 timeout**，就必然 502 —— **与检索无关**。

## 2026-11-01 实测（证明 timeout 修复已上线）

本 KB 移植后连打 11 次，**11/11 HTTP 200**：

```
69.9s / 36.4s / 28.8s / 67.5s / 143.6s   ← 143.6s 在旧 120s 上限下必然 502
32.2s / 50.4s / 55.8s / 67.4s / 70.5s / 88.5s
```

→ 证明姊妹 KB 的 proxy commit `a331618`（`HERMES_TIMEOUT` 默认 300s）**已在线上生效**。
