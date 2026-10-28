# 2026-08-29 cron crawl 状态快照

## 结果

- **成功**：721 / 721（零失败）
- **耗时**：2:44（2 分 44 秒）
- **index.json**：2,148,657 字节，mtime 2026-08-29 11:03:07

## Locale 分布（连续第三次一致）

| locale | 条目 | 与 8/25、8/28 对比 |
|---|---|---|
| zh | 365 | 一致 |
| en | 178 | 一致 |
| kr | 178 | 一致 |
| **合计** | **721** | 一致 |

## Proxy 健康（重启后 check_proxy_health.py 验证）

- inexbot-open: docs=721, loaded=True ✅
- inexbot: docs=547, loaded=True ✅
- gateway reachable: http://localhost:8642 ✅

## 流程记录

1. 后台启动：`terminal(background=true)` → 第一帧 `exit_code=0` 仅代表启动成功
2. 多次 `process(action=poll, timeout=180)` 轮询（用了 `tail -100` 管道，导致中间轮询看不到实时输出，下次建议去掉 `tail`）
3. `sudo systemctl restart hermes-skill-proxy`
4. `sleep 10 && python3 check_proxy_health.py`（裸 curl 直连首次返回 Connection refused，符合 SKILL.md 中 2026-08-28 验证的 systemd 重启窗口期观察）

## 清理尝试

- 尝试 `rm` KB 目录下残留的 `check_crawl_20260821.py` 被 security policy 拦截（标 `delete in root path`，KB 路径前缀也在拦截列表）
- 按 SKILL.md 指引不强行删，下次 cron 自然覆盖
- 写了 `check_crawl_20260829.py` 做一次性 locale 验证（按惯例同样不清理，让下次 cron 覆盖）

## 基线漂移结论

连续三次（8/21: 715、8/25: 721、8/28: 721、8/29: 721）观察：
- 8/25 之后 zh locale 不再增长（365 持平三次）
- en/kr 长期稳定 178
- 当前 721/547 即为稳态基线，无需调整 `check_proxy_health.py` 的 BASELINES
- 站点内容无变化，下次 cron 大概率仍是 721/547

## 注意点

- `tail -N` 管道 + 后台 `process(poll)` 看不到实时进度（`tail` 缓存到 EOF 才输出）——建议后台跑时不带 `tail`，让 poll 能拿到增量日志。下次写 cron 可考虑改成把整个输出重定向到日志文件。