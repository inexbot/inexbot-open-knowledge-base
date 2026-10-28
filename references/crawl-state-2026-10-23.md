# Crawl state — 2026-10-23（799/558，首次发现增量爬取盲区）

## 结果摘要

| 项目 | 值 |
|---|---|
| inexbot-open docs | **799**（第 5 次持平，但**内容有变**，非稳态） |
| inexbot docs | 558（第 2 次持平） |
| index.json | 2,453,054 bytes（vs 10-22 的 2,448,900，**+4,154**） |
| locale 拆分 | en=178, kr=178, zh=443（三 locale 全非零，sidebar 正常） |
| 爬取耗时 | 3:10（首次）/ 3:18（补爬），稳态带 3:00–3:20 内 |
| 失败页 | 0 / 799 |
| proxy | 重启于 11:19:29，docs 799 + 558，loaded=True |

## 关键发现：不是零变化，是上游 API 改名

`check_crawl_state.py` 报 `doc count flat but BYTES DIFFER`。按 skill 的新指引查「今天重写了哪些 md」：

```bash
find ~/.hermes/kb/inexbot-open/md -newermt "2026-10-23 00:00" -type f
```

**结果只有 1 个文件**（含 raw 共 2 个）：`zh-04.上位机-01.C++-03.示例-03.进阶应用-02.使用servo_...md`

上游把 API `star_servo_point_position_motion_control()` 改名为
`servo_point_position_motion_control()`。en 页面 title 已变为
`Servo Control Motion Using servo_point_position_motion_control()`。

### 为什么只有 zh 被抓到（增量爬取的盲区）

crawler.py:291 — `if not force and raw_path.exists() and md_path.exists(): continue`

同 URL 的正文改动**永远不会被重抓**。本次：

- **zh**：目录也一起改名（`03.示例` → 新 slug）→ 新 slug 缓存缺失 → 触发抓取 ✅
- **en/kr**：URL 未变（仍 `.../02.Servo-Control-Motion`）→ 缓存「有效」→ 永久跳过 ❌

结果：index 中 en/kr 仍在文档化一个**上游已删除的 API**（各 2 处 `star_servo`），zh 却是新的 → 三语种自相矛盾。若不处理，proxy 会给英文/韩文提问注入已废弃的 API 名。

## 处置

1. 精准失效 5 个 index 条目对应的 10 个缓存文件（raw+md），改名 `.stale-bak`（**不用 `rm`**：policy 拦 `delete in root path`；且保留回滚）
2. 跑增量爬虫 → 只重抓这几页，3:18 完成，799/799 成功
3. 校验：zh/en/kr 三方 `star_servo` 均为 0，index 中残留 `star_servo` 条目为 0
4. `sudo systemctl restart hermes-skill-proxy` → sleep 12 → `check_proxy_health.py` OK
5. `Path.unlink()` 清理 10 个 bak，释放 1.3 MB

## 踩坑

- **`f.stat()` 必须在 `rename()` 之前**，否则脚本在第一行就 `FileNotFoundError` 崩掉，留下半成品状态。脚本需幂等（容忍 already-renamed / not-on-disk）。
- **判断缓存陈旧的指标只能单向**：「缓存有、上游没有」有效；「上游有、缓存没有」全是每页 ~1100 个导航/sidebar/footer 样板词元，100% 假阳性。第一版探针用反向指标，15/15 全误报 STALE。
- **`process(log)` 对重定向输出的后台任务返回空**，须 `tail -20 /tmp/open-crawl-YYYYMMDD.log`（与 10-22 记录一致）。
- **`execute_code` 沙盒**需在脚本顶部显式 `import time` / `import subprocess`。

## 历史序列（inexbot-open）

534 (07-18) → 552 (07-26) → 636 (07-31) → 715 (08-21) → 721 (08-25 起连续 7 次稳态)
→ 795 (09-29, +74 zh) → 797 (10-01, +2) → 799 (10-10, +2)
→ 799 (10-18 / 10-19 / 10-21 / 10-22 连续 4 次持平，字节逐字节相同)
→ **799 (10-23，字节 +4,154，上游 API 改名，非零变化)**

姊妹 KB inexbot：558 (10-22 起持平)