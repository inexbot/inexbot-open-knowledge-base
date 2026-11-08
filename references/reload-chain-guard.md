# 重载链守卫：判定 proxy 的 5h 自动重载是否还活着

**2026-11-07 引入** —— 移植自姊妹 KB `inexbot-knowledge-base` 的修正版，
并改了它一处**硬编码**（见文末「移植时必须改的一处」）。

## 为什么需要它

每轮 cron 都要回答一个问题：**「新的 index.json 会不会自动生效，还是得 restart proxy？」**

有三种查法，**前两种都会骗人**：

| 查法 | 为什么不可靠 |
|---|---|
| `journalctl \| grep Total:` | systemd 下 Python stdout 是**块缓冲**的，重载行可能躺在用户态缓冲区里几小时。journal 里没有重载行**不代表**没重载 |
| `/health` 的 docs 数 | 只告诉你**当前**状态，不告诉你**下次重载什么时候** → 分不清「5h 窗口内，正常」和「重载链断了，永远不会更新」 |
| `ps -L` 找「age 落在 5h 附近」的线程 | ❌ **判据本身是错的**（见下） |

## ⚠️ 判据的坑：定时器 age 在 `[0, 5h)` 内**均匀分布**

`schedule_reload()` 每触发一次就**新建一个 `threading.Timer` 线程**。
该线程在**上次触发时出生**，活满一个 `RELOAD_INTERVAL`（5h）后再次触发
⇒ **它的 age 恒定落在 `[0, 5h)` 区间内，且在周期内均匀分布**。

链断了（2026-10-27 修之前的老 bug）→ 不再新建线程 → **没有任何 age < 5h 的非主线程**。

### ❌ 旧判据为何是假阳性发生器

姊妹 11-06 的首版守卫脚本找 **`age ∈ [3.5h, 5.25h]`** 的线程，找不到就报
`[FAIL] 重载链可能已断裂`。

**但 age 在 `[0, 5h)` 均匀分布 ⇒ 约 70% 的时间它落在那个窗口之外**
⇒ 脚本会**周期性误报「链断了」**。

**2026-11-07 实测（本 skill 现场撞上）**：定时器 age = **3.34h**
→ 落在 `[3.5h, 5.25h]` **之外** → 旧脚本报 `[FAIL]`。
但同时 `/health` 显示 `inexbot-open: 799` == 磁盘 799
→ **重载明明发生过，链是活的**。

**危害**：误报会让下一轮 cron 去 restart proxy —— 而 restart 会打断姊妹 KB
正在跑的 e2e 探针（陷阱 1 / 陷阱 20），**收益为零、风险为正**。

### ✅ 正确判据

1. **定时器 = age < RELOAD 的非主线程里最老的那一个**
   （请求工作线程都是秒级短命，天然比定时器年轻得多）
2. **交叉验证（ground truth）**：`/health` 的 `docs` 是否等于磁盘 `index.json` 的条目数
   —— 相等就**证明**重载确实发生过，链必然是活的
3. 只有「**既没有 age < 5h 的非主线程**」**且**「内存 ≠ 磁盘」**才判 FAIL

## 用法

```bash
/usr/bin/python3 ~/.hermes/skills/productivity/inexbot-open-knowledge-base/scripts/check_reload_timer.py
```

输出示例（2026-11-07 11:23 实测）：

```
proxy PID = 1844673
now      = 2026-11-07 11:23:35

tid=1844673  comm=python3    started=2026-11-05 11:02:58  age=174038s (48.34h)
tid=1871807  comm=python3    started=2026-11-07 08:03:33  age=12003s (3.33h)   ← 定时器
tid=1875689  comm=python3    started=2026-11-07 11:23:09  age=26s (0.01h)     ← 请求线程

磁盘 index.json : {'inexbot': 560, 'inexbot-open': 799}
proxy 内存索引   : {'inexbot': 559, 'inexbot-open': 799}

  inexbot       disk=560 mem=559 PENDING RELOAD
  inexbot-open  disk=799 mem=799 OK
[OK] 重载链存活：定时器线程 tid=1871807
  -> 上次触发 2026-11-07 08:03:33
  -> 下次重载 2026-11-07 13:03:33  (在 100 分钟后)
  -> 内存/磁盘同步: 是（尚未到重载时间，属正常窗口）
```

## 判读表

| 观测 | 结论 | 动作 |
|---|---|---|
| 本 KB 内存 == 磁盘 | 已重载，链是活的 | **不要 restart** |
| 内存 != 磁盘，但**下次重载在 1 小时内** | 正常重载窗口 | **不要 restart**（收益为零、风险为正） |
| 内存 != 磁盘，且**已过预定重载时刻**仍不更新 | 真故障 | 才考虑 restart |
| `[FAIL]`（无 age<5h 非主线程 **且** 内存≠磁盘） | 链真断了 | `sudo systemctl restart hermes-skill-proxy` |

**通则**：「磁盘 index 与 proxy /health 的 docs 不一致」**本身不是故障** ——
先算「下次自动重载在什么时候」。只要自动重载还在 1 小时内，就**不要 restart**。

## 📌 排期基准是「定时器线程自身的出生时刻」，不是进程启动时刻

主线程 11:02:58 启动，理论上「+5h」= 16:02:58 首次重载 —— **但没有发生**。

因为 `schedule_reload()` 是**自续期**的：定时器在触发时出生，并排下下一次。
⇒ **下次触发 = 定时器线程的出生时间 + RELOAD_INTERVAL**。

## ⚠️ 移植脚本后必查硬编码

姊妹 KB 那份 `check_reload_timer.py` **只读 `~/.hermes/kb/inexbot/index.json`** ——
对以 `kb/inexbot-open` 为对象的 skill **判据无意义**（会比出一个错的 KB）。

**本 skill 版已改为同时检查两个 KB**：

```python
KB_DIRS = {"inexbot": ".hermes/kb/inexbot", "inexbot-open": ".hermes/kb/inexbot-open"}
```

并以 **`inexbot-open`** 为 `in_sync` 判据；姊妹 KB 的 stale 状态只作为
`PENDING RELOAD` 一行显示，**不**影响本 KB 的 PASS/FAIL 结论。

> 💡 **通则：姊妹 KB 的脚本不一定是「可直接 cp」的** ——
> 移植后必须**逐行检查硬编码的路径 / KB 名 / 基线值**，
> 否则会得到一个「能跑但判错对象」的探针（同样是**静默**失效）。

## ⚠️ 探针本身也会制造假阳性

写完判据后**先用「已知健康」的 proxy 跑一遍**：
若报 FAIL 但 `/health` 的 docs 与磁盘一致，**是脚本错了，不是 proxy 错了**。

2026-11-07 的姊妹 KB 就是这么发现自己的旧判据有 70% 假阳性率的。

## 相关

- SKILL.md「什么时候该 restart proxy」—— 两判据 + 本守卫的用法
- SKILL.md「每轮 cron 的标准验证序列」—— 第 8 步
- `references/shared-proxy-service-pitfalls.md` §陷阱 21 —— 姊妹 KB 的权威版
