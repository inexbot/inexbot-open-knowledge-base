# open.inexbot.com 爬虫现场快照 — 2026-07-26

> 时间：2026-07-26 11:00–11:02 CST
> 来源：cron 定时任务，crawler.py 跑完一次后的实际验证
> 用途：与 2026-07-18 快照对比，确认站点持续在增长，并作为当前健康基线。

## 健康基线

```bash
curl -sS http://localhost:8643/health
# 期望：inexbot-open.docs = 552, loaded = true
#       inexbot.docs     = 547, loaded = true
```

| 指标 | 当前值 | 与 2026-07-18 对比 |
|------|-------|-------------------|
| `inexbot-open.docs` | **552** | 534 → 552（+18，zh locale 增长） |
| `inexbot.docs` | **547** | 536 → 547（+11） |
| `md/` 文件数 | **1234** | 712 → 1234（zh-×364, en-×346, kr-×346, no-prefix×178） |
| zh locale 条目 | **196** | 178 → 196（+18，单 locale 涨幅最大） |
| en / kr locale 条目 | 178 / 178 | 不变 |
| 抓取耗时 | 1 min 52 s | 比 7-18 的 2 min 42 s 更快（CPU/网络条件差异） |
| 单次失败数 | 0 | 552 / 552 全成 |

## Locale 分布详情

```
index.json (552 docs) by locale path prefix:
  zh  : 196
  en  : 178
  kr  : 178

md/ (1234 files) by filename prefix:
  zh-         : 364
  en-         : 346
  kr-         : 346
  no-prefix   : 178   # 旧 crawler 残留，无害，详见 SKILL.md 的 i18n slug 碰撞陷阱
```

> 提示：md 文件数与 index.json 条目数比是 ~2.24 倍。index.json 只数 sidebar 链接去重后的 unique URL，而 md/ 包含 raw HTML（一份）+ markdown 化后输出（一份）两个文件 — 实际上「en」和「kr」一般只有 markdown 输出，「zh」既有 raw 也有 md，所以各 locale 数量略有差异。

## 与前一快照的差异

| 维度 | 2026-07-18 | 2026-07-26 | Δ | 解读 |
|------|-----------|-----------|---|------|
| inexbot-open docs | 534 | 552 | +18 | 站点内容持续增长，主要是 zh locale |
| inexbot docs | 536 | 547 | +11 | 姊妹 KB 也在长 |
| md 文件数 | 712 | 1234 | +522 | 不是「增长」，是历史 raw/md 双备份的累积；新版 crawler 行为没变 |
| 单次抓取耗时 | ~2m42s | 1m52s | -50s | 当次网络条件更好 |

## 故障排查快查表（沿用 2026-07-18，基线数字已更新）

| 现象 | 第一查 | 第二查 |
|------|--------|--------|
| `/health` 显示旧 docs 数 | `sudo systemctl restart hermes-skill-proxy` | `sudo journalctl -u hermes-skill-proxy --since "1h ago"` |
| `inexbot-open.docs` 突然变 0 | 重跑 `python3 scripts/crawler.py --force` | `references/vitepress-i18n-sidebar-diagnosis.md` |
| docs 数比基线**骤降** | sidebar 提取挂了，看 jieba/crawler.py 日志 | 翻 vitepress-i18n 诊断 |
| docs 数比基线**小幅上涨**（+5 ~ +30） | 良性增长，把 `BASELINES` 调上去即可 | 无 |
| docs 数比基线**大幅上涨**（> +50） | 可能是站点大改版；人工 review 新增内容质量后再决定是否上调基线 | 看 OpenAPI / sitemap 变更 |
| 任一 locale 条目数变 0 | 该 locale 已被运营下线，或 crawler 漏提取 | 检查 `__VP_SITE_DATA__.locales.<x>.themeConfig.sidebar` |
| `loaded: false` | proxy 还没加载完，或读 index.json 报错 | `sudo systemctl restart hermes-skill-proxy` |

## 版本历史

- 2026-07-26：inexbot-open 552 docs，zh locale 196；check_proxy_health.py 基线同步。
- 2026-07-18：inexbot-open 534 docs（178 × 3 locale），md 712。
- 之前：仅 zh+en，356 条。

## 现场流程时间线（2026-07-26 cron 实际跑）

```
11:00:32  crawler 启动
11:00:32  fetch_vitepress_metadata() 完成 → 552 个 unique 链接
11:00:33  jieba 词典加载 (~1.2s)
~11:01:30 三 locale 并发下载，CPU 单核
11:02:23  build_index() 启动（552 条）
11:02:24  index.json 写盘（1.69 MB）
11:02:24  crawler 退出（exit 0）
+ ~2s    sudo systemctl restart hermes-skill-proxy 完成
+ ~3s    systemd 启动新进程，proxy 加载新索引
+ ~5s    /health 返回 552/547，loaded=True
```