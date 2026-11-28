---
name: proxy-health-baseline-semantics
description: "为什么 check_proxy_health.py 用「floor + target」两个数，而不是一个 baseline —— 以及 KB 增长后如何避免健康检查假报故障。"
version: 1.0.0
metadata:
  hermes:
    tags: [knowledge-base, proxy, health-check, false-positive, trap-47]
    category: productivity
    related_skills: ["inexbot-open-knowledge-base", "inexbot-knowledge-base"]
---

# 健康检查的基线语义：floor + target，而不是单一 baseline

**2026-11-27 实测**（本 KB cron 轮次，爬取使 KB 从 832 涨到 944 时踩到）。

## 问题：单一 baseline 会在每次 KB 增长后假报故障

`check_proxy_health.py` 原本的判据是：

```python
ok = docs >= baseline and loaded     # baseline = 当时的 docs 数
```

而运维惯例是「**每次良性增长都把 baseline 往上 patch**」（SKILL.md 里明写了这条）。

两个事实叠加 ⇒ **每次 KB 增长，健康检查都会在重载窗口内误报故障**：

| 事实 | 说明 |
|---|---|
| proxy 每 **5h** 才自动重载索引 | 爬完的那一刻，proxy 内存里还是**旧索引** |
| baseline 被 patch 成**新值** | `docs`（旧） < `baseline`（新） ⇒ 判 DIFF ⇒ **exit 1** |

⇒ 2026-11-27 实测：磁盘 944 / 内存 832 / baseline 944 ⇒ **exit 1**，
但这是**完全正常的状态**（13:06:34 的自动重载会把 944 送进去）。

⇒ **更危险的是它会一直红**：在下次自动重载之前（最长 5 小时），
每一轮 cron 跑这个脚本都会得到 exit 1 ⇒ **真故障被淹没**
（这正是 SKILL.md §陷阱 47 的镜像：判据写错 ⇒ 每次都报 FAIL）。

## 解法：floor + target 双阈值

把「一个期望值」拆成两个语义不同的数：

| 名字 | 含义 | 本轮实例 |
|---|---|---|
| **FLOOR**（`BASELINES`） | 上一个 **known-good** 索引的 docs 数 —— **下限** | 832 |
| **TARGET**（磁盘 `index.json` 条数） | 下次自动重载后 proxy **将会**服务的 docs 数 —— **目标** | 944 |

判据：

```
loaded is False                  -> FAIL   (proxy 看不到索引)
docs >= FLOOR                    -> 健康
docs >= TARGET (磁盘)             -> 健康
docs <  FLOOR 且 docs <  TARGET   -> FAIL   (真回归：sidebar 抽取挂了)
docs <  TARGET 但 >= FLOOR        -> 健康，标注 "awaiting 5h auto-reload"
```

⇒ **「内存落后于磁盘」不再被当成故障**；只有「**比上一个好状态还差**」才是故障。

### 为什么不能只把 baseline patch 成旧值（floor）

那样确实能消掉假阳性，但会**丢掉一个真实信号**：proxy 若因重载链断裂而
永远停在旧索引，内存值就永远 < floor ⇒ 除非重载链断裂正好低于 floor，
否则**报不出来**。
floor + target 保留了这个信号（`docs < FLOOR` ⇒ 真的坏了）。

## ⭐ 必须用合成样本回归验证（否则会变成「恒绿」）

§陷阱 47 说「恒红」危险；**镜像的「恒绿」同样无用** ——
一个从不报 FAIL 的检查等于没有检查。

⇒ `scripts/test_proxy_health_regression.py` 用 **5 个合成样本**覆盖两个方向：

| 用例 | 期望 exit | 覆盖什么 |
|---|---|---|
| 增长 + proxy 尚未重载（memory == floor < disk） | **0** | 不误报正常重载窗口 |
| 健康（memory == disk == floor） | **0** | 基本正确性 |
| proxy 超前于磁盘（memory > disk） | **0** | 上游缩容后不误报 |
| **真回归**（memory < floor 且 < disk） | **1** | **必须能报出来** |
| `loaded=False` | **1** | proxy 读不到索引 |

```bash
/usr/bin/python3 ~/.hermes/skills/productivity/inexbot-open-knowledge-base/scripts/test_proxy_health_regression.py
```

⚠️ **两个方向都要跑**：只跑「完好样本」查不出**假绿**（漏报真故障），
只跑「故障样本」查不出**恒红**。
（§陷阱 47 的方法论，对本检查的移植。）

## 对姊妹 KB 的建议

姊妹 KB `inexbot-knowledge-base` 的同名脚本若仍是「单一 baseline + 往上 patch」
的写法，**会有同样的假阳性问题** —— 她每次 KB 增长后也会红。
⇒ 本库已修好并提供回归脚本，**建议姊妹 KB 同步**（两边跑的是同一个 proxy，
但判据各自的脚本负责）。

## 关联

- SKILL.md §陷阱 47（审计脚本「恒定红灯」比「没有脚本」更危险）
- SKILL.md §陷阱 20 / 「什么时候该 restart proxy」（内存≠磁盘属正常重载窗口）
- `scripts/check_reload_timer.py`（判定重载链是否还活着 + 下次重载时刻）
