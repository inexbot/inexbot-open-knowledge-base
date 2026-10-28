# crawl-state-2026-10-10

## Summary

| 指标 | 值 |
|------|-----|
| 日期 | 2026-10-10 (周六) 11:00 CST |
| 执行方式 | scheduled cron job |
| crawler 耗时 | **0:03:16 (~196s)** |
| 爬取结果 | **799 / 799 成功 (100%)** |
| md 文件数 | 1854 |
| 与上次对比 | 797 → **799（+2 zh sidebar 持续增长）** |
| locale 分布 | zh=443, en=178, kr=178 |
| proxy 重启后 docs | 799 ✅（首次连 health 失败，重试一次拿到 200 OK） |
| 同步基线更新 | `check_proxy_health.py` BASELINES: inexbot-open 797→799, inexbot 557 (稳态) |

## 结论

- zh sidebar 继续温和增长（+2 篇，与 2026-10-01 → 797 的模式完全一致：每 9 天 +2）。
- en/kr 仍稳态 178；inexbot（姊妹 KB）也稳态 557。
- baseline 已 patch 进 `check_proxy_health.py`（797 → 799）和 SKILL.md，下次 cron 自动基线对齐。

## 关键观察：姊妹 KB 与本 skill cron 同窗口并发跑

启动时检查发现：

```
ecs-user 1591253  /usr/bin/bash -lic set +m; python3 .../inexbot-knowledge-base/scripts/crawler.py
ecs-user 1591263  python3 .../inexbot-knowledge-base/scripts/crawler.py  (R, 91.8% CPU)
```

姊妹 KB `inexbot-knowledge-base` 11:00 同时启动，正在爬取 `doc.inexbot.com`。
按 2026-09-29 验证「同窗口并发争 CPU」预计本次耗时 ~4:54 量级。

但本次实测 **0:03:16**，与单跑稳态 ~3:00 几乎一致——可能原因：

- 姊妹 KB crawler 还在 sidebar 解析 / 早期页面阶段（11:00 启动到 11:01 才到 1/N），与本 skill 各自独立网络 IO，CPU 竞争窗口实际很短
- 机器当时 CPU 空闲，两进程都是网络 IO bound，互相阻塞有限
- 本 skill 页面比姊妹 KB 略少（约 1.5 倍差），后段本 skill 收尾时姊妹 KB 仍在爬大头，CPU 占用错峰

所以「并发抢 CPU ≈ 1.8x 耗时」是**极端情况估算**，常态下抢 CPU 影响 ≈ 5-10%，**不必为了避免并发争 CPU 而刻意错开 cron 调度**。

## 等待策略验证（继续走 2026-08-30 之后的 inline 方案）

按 SKILL.md 2026-10-01 更新版——`execute_code` 沙盒里写 `os.kill(pid, 0)` + `time.sleep(10)` 循环：

```python
import os, time, subprocess
pid = 1591304
while True:
    try: os.kill(pid, 0)
    except ProcessLookupError: break   # exited
    time.sleep(10)
```

- 后台启动：`terminal(background=true, notify_on_complete=true)` → 一帧返回 `exit_code=0`
- 等待：inline `os.kill` 循环，~200s 自然结束（10s 一拍，未被 Hermes 进程 API 60s clamp 打断）
- 进程消失后读 `/tmp/open-inexbot-crawler-*.log` → 799/799、3:16 完成

实际执行片段（每 30s 一行日志）：

```
[30s]  1591304  00:36  Ss   0.1 0.1  python3 .../crawler.py
[60s]  1591304  01:06  Ss   0.1 0.1  python3 .../crawler.py
[90s]  1591304  01:36  Ss   0.0 0.1  python3 .../crawler.py
[120s] 1591304  02:06  Ss   0.0 0.1  python3 .../crawler.py
[150s] 1591304  02:36  Ss   0.0 0.1  python3 .../crawler.py
[180s] 1591304  03:06  Ss   0.0 0.1  python3 .../crawler.py
[200s] crawler exited
```

> ⚠️ **小提示**：ps 显示的 `%CPU` 永远 ~0%，因为 `crawler.py` 是被 `/bin/bash -lic` 包装器（`Ss` 状态）调起来的，ps 的 CPU 列取的是 bash wrapper，**不是 python 子进程**。判定「crawler 仍在跑」只看 PID 存活 + 时间在前进；CPU% 不可靠。下次诊断时如果 PID 还活着但 CPU=0，不代表进程死了。

## proxy 启动窗口观察

按 SKILL.md 警告：`sudo systemctl restart hermes-skill-proxy` 与 health check 不能链在同一行 `&&` 里。

本次分两条命令：

```
sudo systemctl restart hermes-skill-proxy   # 立即返回
python3 scripts/check_proxy_health.py       # rc=1, Connection refused
```

跟 2026-08-25 / 2026-08-28 的 `sleep 5/8` 才连通现象一致——本次姐妹 KB 也在爬取，CPU 负载中，systemd 启动窗口被拉宽。第二次 `check_proxy_health.py`（约 5-10s 后）首次就成功，docs=799 ✅。

继续证实 SKILL.md 结论：「启动窗口宽度跟机器负载直接相关，不是 systemd 的固定延迟；负载轻可低至几百毫秒，负载重可达 5-8s+。唯一稳定对策就是 `scripts/check_proxy_health.py` 自带 retry，不靠裸 curl + 手动 sleep。」

## 历史基线快照

534 (07-18) → 552 (07-26) → 636 (07-31) → 715 (08-21) → 721 (08-25 稳态 × 7) → 795 (09-29 +74 打破稳态) → 797 (10-01 +2 持续增长) → **799 (10-10 再 +2 持续增长)**。

仍是单调上升的良性增长曲线，无 sidebar 提取回归迹象。`zh sidebar` 自 2026-09-29 打破稳态后持续 +2/次（09-29: +74, 10-01: +2, 10-10: +2），增速已回归正常。
