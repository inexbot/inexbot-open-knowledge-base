# open.inexbot.com 爬虫现场快照 — 2026-07-18

> 时间：2026-07-18 11:05–11:08 CST
> 来源：cron 定时任务，crawler.py 跑完一次后的实际验证
> 用途：下次怀疑 KB 出问题时作为「正常状态是什么」的对照基准。

## 健康基线

```bash
curl -sS http://localhost:8643/health
# 期望：inexbot-open.docs = 534, loaded = true
#       inexbot.docs     = 530, loaded = true
```

| 指标 | 当前值 | 含义 |
|------|-------|------|
| `inexbot-open.docs` | **534** | index.json 条目数 = 178 zh + 178 en + 178 kr（kr locale 自 2026-07 起被纳入） |
| `md/` 文件数 | ~712 | 178 (新版 zh-) + 178 (新版 en-) + 178 (新版 kr-) + 178 (旧版裸名残留) |
| 抓取耗时 | ~2 min 42 s | 534 页并发=8，单页 ~0.3s，CPU 单核 |
| 单次失败数 | 0 | crawler 把 raw+md 都存盘，下次增量扫描会跳过 |

## 版本历史

- 2026-07-18（v1.0.1）：kr locale 进入索引；总数从 356 → 534；md/ 残留裸名是 slugify 不带 locale 前缀的历史遗留，无害。
- 之前（v1.0.0）：仅 zh+en locale 进入索引，356 条。

## 故障排查快查表

| 现象 | 第一查 | 第二查 |
|------|--------|--------|
| `/health` 显示旧 docs 数 | `sudo systemctl restart hermes-skill-proxy`（手动重载索引，5h 才自动重载） | 看 journal 日志：`sudo journalctl -u hermes-skill-proxy --since "1h ago"` |
| `inexbot-open.docs` 突然变 0 | 通常是 sidebar 提取挂了，重跑：`python3 scripts/crawler.py --force` | 翻 `references/vitepress-i18n-sidebar-diagnosis.md` |
| crawler 报 "发现 N 个页面"，N 偏离 534 | 检查 `__VP_SITE_DATA__.locales` — 看 zh/en/kr sidebar 还在不在 | 可能某 locale 被运营下线，等一周再观察 |
| md/ 里出现"裸名"文件越来越多 | 当前 crawler 已带 locale 前缀，正常工作时不应增长；增长说明跑的是旧 crawler | `git pull` 升级 skill |
| 检索命中全是错的 locale | 看 proxy 的 top-3 注入里 path 第一段是不是用户预期的 locale | 改权重或在代理前用 user-language hint |

## 现场流程时间线（参考）

```
11:05:37  crawler 启动
11:05:37  fetch_vitepress_metadata() 完成 → 534 个 unique 链接
11:05:38  jieba 词典加载
~11:07:0X 进入 kr locale 下载，CPU 单核，~2 页/秒
11:08:17  534/534 下载完成
11:08:18  build_index() 启动
11:08:19  index.json 写盘（1.6 MB）
11:08:19  crawler 退出
~11:08:39  systemd restart proxy 完成（旧 index 仍加载，需要重新 reload）
11:08:44  /health 显示 534
```
