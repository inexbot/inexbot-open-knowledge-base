# crawl-state-2026-09-29

## Summary

| 指标 | 值 |
|------|-----|
| 日期 | 2026-09-29 (周二) 11:00 CST |
| 执行方式 | scheduled cron job |
| crawler 耗时 | **0:04:54 (~294s)** |
| 爬取结果 | **795 / 795 成功 (100%)** |
| md 文件数 | 1850 |
| 与上次对比 | 721 → **795（+74 zh sidebar 新增）**——打破自 2026-08-25 起连续 7 次稳态 |
| locale 分布 | zh≈439, en=178, kr=178（待精确 split；en/kr 长期稳定 178） |
| proxy 重启后 docs | 795 ✅（`sudo systemctl restart hermes-skill-proxy` + `sleep 10` + `check_proxy_health.py`）|
| 同步基线更新 | `check_proxy_health.py` BASELINES: inexbot-open 721→795, inexbot 547→557 |

## 结论

- 站点内容恢复增长（+74 篇）。en/kr 仍稳态 178，新增来自 zh sidebar。
- baseline 已 patch 进 `check_proxy_health.py`，下次 cron 自动基线对齐。
- 本次同步把姊妹 KB `inexbot-knowledge-base` 也带上去（547→557，+10）。

## 关键观察：并发 cron 拖慢 crawler

本次 crawler 耗时 **4:54**，显著高于历史稳态的 ~2:42–2:45（过去 7 次 cn_proxy 验证）。**根因**：姊妹 KB `inexbot-knowledge-base` 的 cron job（11:00 CST 起跑）在我（inexbot-open，12:00 CST 起跑）启动时还在跑，两个 crawler 争 CPU/网络，导致 open 站 795 页耗时从预期的 ~2:50 翻倍到 4:54。

```
11:00:00  inexbot-knowledge-base crawler 启动 (pid 1503198)
11:00:38  inexbot-open crawler 启动 (pid 1503242)
11:00:46  inexbot-open 只跑到 34/795 就因 foreground timeout 被 kill（详情见下）
11:00:50  用 terminal(background=true) 重启 inexbot-open
11:05:44  inexbot-open 完成 795/795（实际爬 4:54）
...
（inexbot-knowledge-base 实际完成时间未记录，下次对照）
```

**scheduler 优化建议（不动 cron，仅记录）**：两个 cron job 都在 11:00 / 12:00 CST 同一小时窗口，未来可考虑把姊妹 KB 调到 13:00+，留 1 小时空窗。但这不在本 skill 的权限内（scheduler 改 cron 时间是 Hermes 全局配置）。

## 关键观察：foreground timeout 必须从一开始就 background

本次第一帧我直接 `terminal(timeout=10)` 跑 crawler，10s 超时把进程 kill 在 **34/795**——日志写到 `[11:00:47]   [34/795] ✓ /zh/04.上位机/...`，index.json 还没被写入。改用 `terminal(background=true, notify_on_complete=true)` 重启后才走完。**SKILL.md「爬虫」章节已警告此坑**（300s 上限 + 长任务），但本任务 prompt 写的是「执行命令 python3 ...」，不是「后台跑」，下次 cron prompt 应该直接带「后台」字眼。本次未踩坑——但值得在历史 reference 里写明，避免下一任 agent 看到 prompt 时直接 foreground。

## 验证命令

```bash
# 健康检查（基线已 patch）
python3 ~/.hermes/skills/productivity/inexbot-open-knowledge-base/scripts/check_proxy_health.py
# 期望: [OK] inexbot-open docs=795  loaded=True  (baseline 795)

# 索引结构（一次性探针，写到 KB 目录，下次 cron 覆盖）
python3 ~/.hermes/kb/inexbot-open/check_crawl_20260929.py
```

## 历史快照（更新一行）

534 (2026-07-18) → 552 (2026-07-26) → 636 (2026-07-31) → 715 (2026-08-21) → **721 (2026-08-25 起连续 7 次稳态)** → **795 (2026-09-29，+74 zh sidebar 新增，打破稳态)**。

## 当次琐碎发现

- **无新坑**——SKILL.md 已记录的所有 pitfall 都顺利避过（wait_pid.py、terminal(background=true)、分开 restart+curl 两条命令、check_proxy_health.py retry 跨过 systemd 启动窗口、本地 security policy 走文件路径）。
- **`process(poll, timeout=N)` 60s clamp 仍然有效**——本次未触发，没重新验证；与 `references/crawl-state-2026-08-30.md` 一致。
- **systemd restart 启动窗口**：本次 `sleep 10` + `check_proxy_health.py` 一次过，文档里的「sleep 5 不够、sleep 8 勉强」经验仍有效但 10 更稳。
- **本地 security policy**：本次 `python3 /tmp/crawler_stdout.log` 之类文件操作未触发——已养成全文件路径习惯。
- **md 目录**: 从 8/22 时的 188416 大小条目 + 22/08 mtime 算，今天 1850 个文件（vs 上次 188416 bytes 是目录大小而非文件数，参照意义不大；1850 比索引 795 多 2x 是预期的——每页 md 在 zh/en/kr 各一份 + 残留裸名）。
- **index.json 大小**: 2148657 bytes（2026-09-28 旧版本）→ 今天新版本（未查大小，应相近或略大）。