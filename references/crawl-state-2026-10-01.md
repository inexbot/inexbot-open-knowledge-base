# crawl-state-2026-10-01

## Summary

| 指标 | 值 |
|------|-----|
| 日期 | 2026-10-01 (周四) 11:00 CST |
| 执行方式 | scheduled cron job |
| crawler 耗时 | **0:03:01 (~181s)** |
| 爬取结果 | **797 / 797 成功 (100%)** |
| md 文件数 | 1852 |
| 与上次对比 | 795 → **797（+2 zh sidebar 持续增长）** |
| locale 分布 | zh=441, en=178, kr=178 |
| proxy 重启后 docs | 797 ✅（`sudo systemctl restart hermes-skill-proxy` 后立即就绪，无需 sleep） |
| 同步基线更新 | `check_proxy_health.py` BASELINES: inexbot-open 795→797, inexbot 557 (稳态) |

## 结论

- zh sidebar 继续温和增长（+2 篇）。en/kr 仍稳态 178，inexbot（姊妹 KB）也稳态 557。
- baseline 已 patch 进 `check_proxy_health.py`（795 → 797）和 SKILL.md，下次 cron 自动基线对齐。

## 关键观察：单跑 vs 并发跑

本次 crawler 耗时 **3:01**，与历史稳态 ~2:45 接近（没有姊妹 KB 并发争 CPU）。
作为对比：2026-09-29 同窗口并发跑耗时 4:54（+78%），验证了「姊妹 KB 与本 skill cron 同 11:00 CST 窗口抢 CPU」这个 09-29 假设。

```
2026-10-01 11:00:25  inexbot-open crawler 启动 (pid 1517395, single)
2026-10-01 11:00:27  [1/797] ✓ /zh/04.上位机/00.AI 助手先读
2026-10-01 11:03:25  索引构建完成
2026-10-01 11:03:26  797/797 成功；index.json 写入 2,438,320 bytes
```

姊妹 KB `inexbot-knowledge-base` 今日未与本 skill 同窗口运行（推测调度器已错开），所以本 KB 恢复到稳态 ~3:00 完成。

## 等待策略验证

按 2026-09-29 / 2026-08-30 教训，**只用 `ps` + sleep 循环**等长任务，绕开 Hermes `terminal(wait)` / `process(poll)` 60s clamp：

- 后台启动：`terminal(background=true, notify_on_complete=true)` → 一帧返回 `exit_code=0`（误导，不代表完成，只代表启动成功）
- 等长任务：`ps -p <pid>` 每 15s 一次，直到 PID 消失
- 进程消失后读完整日志：`/tmp/crawler_*.log` → 797/797、3:01 完成

耗时：

| 阶段 | wall time |
|------|-----------|
| 后台启动 | <1s |
| 等待 crawler 完成 | ~181s（每 15s poll，无中断）|
| proxy 重启 + health 验证 | ~4s |

总计约 186s，一次到位。

## proxy 启动窗口观察

`sudo systemctl restart hermes-skill-proxy` + 立即 urllib.request.urlopen(health) **首次就成功**（4.26s 内拿到 200 OK）。

与 2026-08-25 / 2026-08-28 的 `sleep 5/8` 才连通的窗口比，这次窗口明显更短。可能是：
- systemd 单元文件成熟后启动顺序稳定
- 机器当前负载低（无姊妹 KB 并发爬取）

未来若再遇到 Connection refused，还是推荐用 `scripts/check_proxy_health.py`（带 retry）而不是裸 curl + 手动 sleep。

## 历史基线快照

534 (07-18) → 552 (07-26) → 636 (07-31) → 715 (08-21) → 721 (08-25 稳态 × 7) → 795 (09-29 +74 打破稳态) → **797 (10-01 +2 持续增长)**。

仍是单调上升的良性增长曲线，无 sidebar 提取回归迹象。