# open.inexbot.com 爬虫现场快照 — 2026-08-25

> 时间：2026-08-25 11:01–11:04 CST
> 来源：cron 定时任务，crawler.py 跑完一次后的实际验证
> 用途：与 2026-08-21 快照对比，确认站点持续小幅增长，并作为当前健康基线。

## 健康基线

```bash
curl -sS http://localhost:8643/health
# 期望：inexbot-open.docs = 721, loaded = true
#       inexbot.docs     = 547, loaded = true
```

| 指标 | 当前值 | 与 2026-08-21 对比 |
|------|-------|-------------------|
| `inexbot-open.docs` | **721** | 715 → 721（+6） |
| `inexbot.docs` | **547** | 不变 |
| zh locale 条目 | **365**（推算） | 359 → 365（+6，全部增量来自 zh） |
| en / kr locale 条目 | 178 / 178 | 不变 |
| 抓取耗时 | 2 min 49 s | 比 8-21 的 3 min 47 s 略快（页数只 +6） |
| 单次失败数 | 0 | 721 / 721 全成 |
| crawler 进程 PID | 1199906 | — |
| proxy 重启方式 | `sudo systemctl restart hermes-skill-proxy` | — |
| `/health` 返回格式 | `{"status":"ok","indexes":{...},"hermes_url":"http://localhost:8642"}` | 新增 `hermes_url` 字段（proxy 加的，向下兼容） |

## Locale 分布详情

```
index.json (721 docs) by locale path prefix:
  zh  : 365  (推算：721 - 178 - 178)
  en  : 178
  kr  : 178
```

> zh locale 单次增长 6 条，与 8-21 的 +79 大幅增长相比回落到正常节奏。
> 没有再观察到的「运营加 zh 内容」事件，符合上次快照末尾的预测。

## 与前一快照的差异

| 维度 | 2026-08-21 | 2026-08-25 | Δ | 解读 |
|------|-----------|-----------|---|------|
| inexbot-open docs | 715 | 721 | +6 | 站点内容继续小幅增长，全部来自 zh locale |
| inexbot docs | 547 | 547 | 0 | 姊妹 KB 本轮未爬（不在 cronjob 范围） |
| zh 条目 | 359 | 365（推算） | +6 | 与总增量同步 — 增长全部来自 zh |
| en 条目 | 178 | 178 | 0 | 不变 |
| kr 条目 | 178 | 178 | 0 | 不变 |
| 单次抓取耗时 | ~3m47s | ~2m49s | -58s | 页数只 +6，wall-clock 反而更快（说明站点响应这次比较快） |
| sidebar 链接数与 index.json docs 数一致性 | 715 = 715 | 721 = 721 | — | ✅ 一致，sidebar 提取 0 漏抓 |

## 本轮新发现 / 坑

1. **`sudo systemctl restart hermes-skill-proxy && curl /health` 在同一条命令里会假性失败**。
   本次尝试把重启 + 健康检查链在同一条 terminal 命令里（中间加 `sleep 2`），
   直接拿到 `exit_code=7`（Failed to connect to host）。systemd 重启发出后到
   socket 实际 listen 之间还有几百毫秒到 1–2 秒的窗口，`sleep 2` 不一定够。
   **对策**：分两条命令——先 `sudo systemctl restart hermes-skill-proxy`，
   再独立 `sleep 5 && curl -s http://localhost:8643/health`。
   或直接跑 `scripts/check_proxy_health.py`（脚本内部已经处理连接 / timeout）。
   已写进 SKILL.md 的「常见陷阱」章节。

2. **proxy 的 `/health` 新增 `hermes_url` 字段**。返回从
   `{"status":"ok","indexes":{...}}` 变成 `{"status":"ok","indexes":{...},"hermes_url":"http://localhost:8642"}`。
   向下兼容；check_proxy_health.py 不依赖这个字段，无影响。

3. **`process action=wait` 的 timeout 会被 clamp 到 60s**（与 2026-08-21 快照观察一致）。
   2 分 49 秒的 crawler 需要至少 3 次 wait + 1 次 poll 才能完整取出 output。
   `process action=wait` 内部 `timeout_note` 字段明确显示「Requested wait of Xs was clamped to configured limit of 60s」。
   配合 `process action=poll` 看 uptime 自己估算进度更靠谱。

## 版本历史（持续追加）

- 2026-08-25：inexbot-open **721 docs**（zh 365 推算 +6），check_proxy_health.py 基线同步到 721 / 547。
- 2026-08-21：inexbot-open 715 docs（zh 359）。
- 2026-07-31：inexbot-open 636 docs（zh 280 + en 178 + kr 178）。
- 2026-07-26：inexbot-open 552 docs，zh locale 196。
- 2026-07-18：inexbot-open 534 docs（178 × 3 locale），md 712。
- 之前：仅 zh+en，356 条。

## 现场流程时间线（2026-08-25 cron 实际跑）

```
11:01:39  cron job 启动 terminal(background=true) 调用 crawler.py
11:01:39  crawler 进程 PID 1199906 启动
11:01:39  正在获取 VitePress 站点配置...
11:01:40    发现 721 个页面，761 个 hash
11:01:40  jieba 词典加载 (~1.4s)
11:01:42  三 locale 并发下载开始（zh + en + kr 交错）
11:04:27  正在构建搜索索引...
11:04:29    索引完成，共 721 条
11:04:29  crawler 退出（exit 0，耗时 0:02:49.699448）
+ ~5s    sudo systemctl restart hermes-skill-proxy 完成（分两条命令）
+ ~6s    systemd 启动新进程，proxy 加载新索引
+ ~7s    /health 返回 721/547，loaded=True
+ ~0.5s  scripts/check_proxy_health.py 返回 [OK]，exit 0
```