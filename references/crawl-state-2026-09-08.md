# 2026-09-08 姊妹 KB 故障复盘 + 对本 skill 的预警

## 事件

`inexbot-knowledge-base`（doc.inexbot.com）的每日 cron job 自 9/4 起连续 3 天报 `成功: 0 / 0`，KB 索引被清空到 `{}`，proxy 用通用 system prompt 顶住（所有 KB 检索回退到无 KB 模式）。

| 日期 | 状态 | 索引 docs |
|---|---|---|
| 2026-08-30 | 547 | ✅ 正常 |
| 2026-09-04 | 0 | ❌ cron 跑 0 页（首次故障） |
| 2026-09-07 | 0 | ❌ cron 跑 0 页 |
| 2026-09-08 | **557** | ✅ 现场诊断 + 修复完成 |

## 根因（与本 skill 不同场景）

doc.inexbot.com 已升级到 **VitePress v2.0.0-alpha.18**，触发连锁 4 个变化：

1. 根 `/` 是 client-side JS 语言检测跳转页（456 字节），无 VP 元数据
2. `themeConfig.sidebar` 完全消失（被拆到外部 JS chunk），site_data 里只剩 `i18nRouting + search`
3. `<article class="page">` 不存在，正文是扁平 h1/h2/p/table
4. URL 用 `.html` 后缀

**与本 skill 之前的 i18n 修复不同**：本 skill 的 i18n 站点把 sidebar 放在 `locales.*.themeConfig.sidebar`（还能取到），v2 alpha 是直接没有了。

完整诊断命令、patch 模板、对比表都在 `inexbot-knowledge-base/references/vitepress-v2-alpha-migration.md`。本次 fix 把 crawler.py 改成用 `/sitemap.xml` 作为 link 源 + 从 `<h1>` 抓正文 + slugify 加 unquote + 字节截断。

## 对本 skill 的影响

**本次无影响**：open.inexbot.com 仍是 VitePress v1.x，sidebar 在 `locales.*` 下，i18n fix 仍然有效。9/8 验证仍是 721/547 稳态。

**预警（已写进 SKILL.md「预警」章节）**：如果 open.inexbot.com 也升级到 v2 alpha（首页 `generator` meta 显式标记），本 skill 的 i18n 修复会同样失效。届时按 `inexbot-knowledge-base/references/vitepress-v2-alpha-migration.md` 走 sitemap.xml 路径，**但** v1.x 站点不一定有 sitemap.xml，可能要 fallback 到 `__VP_HASH_MAP__` 的 keys 直接拼 URL + 试访问（hit-or-miss）。

## 跨 skill 经验

i18n + VitePress 站点升级到 v2 alpha 的组合，最稳的页面发现源是 `/sitemap.xml`，**不要**相信 `__VP_*`。两个 skill 互相 reference 诊断模板，避免下次重新发明轮子。

## 行为准则

下次发现某 KB 突然 0 页且 cron 报成功时（**尤其是姊妹 skill**），不要假设是「同一根因」：
- 抓首页长度判断是否 JS 跳转
- 抓 site_data 判断 sidebar 位置（顶层 / `locales.*` / 完全没有）
- 看 `<meta name="generator">` 判断 VP 版本

三步之后才能选对 fix 路径。

## 当次琐碎发现

- `process(poll, timeout=N)` 仍是 60s clamp——8/30 那次的诊断依然有效，本次没踩新坑。
- `terminal(background=true)` 跑 557 页 ~9:39 完成，比 open 站 721 页 ~2:45 慢（doc 站有 372 页「常见问题/伺服报错」单页内容大）。两个站的总页数差不多，但单页 HTML 大小差 1 个数量级（401KB vs 较小）。
- 本地 security policy 仍然拦截 `python3 -c "..."` 和 `curl ... | python3`，全程走文件路径——见 8/30 那次的规则。
