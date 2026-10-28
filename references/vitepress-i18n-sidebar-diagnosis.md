# VitePress i18n sidebar — diagnosis & fix

When the crawler reports `成功: 0 / 0` but the site loads fine in a browser, the cause is almost always **VitePress i18n layout**: `themeConfig.sidebar` is nested under `locales.*` instead of being at the top level.

## Quick diagnostic

```bash
curl -s https://open.inexbot.com/nonexistent-page-test-xyz | \
  grep -oE 'window\.__VP_SITE_DATA__\s*=\s*deserializeFunctions\(JSON\.parse\(".{0,80}' | head -1
```

If the embedded `themeConfig` only contains `i18nRouting` (no `sidebar`), the site is i18n — the sidebar lives in `locales.<key>.themeConfig.sidebar`.

## Symptom in the crawler log

```
[11:00:32] 正在获取 VitePress 站点配置...
[11:00:33]   发现 0 个页面，382 个 hash
[11:00:33] 正在构建搜索索引...
[11:00:33]   索引完成，共 0 条
[11:00:33] 爬取完成！耗时 0:00:00.79
[11:00:33]   成功: 0 / 0
```

The "382 hash" is a hint — the hash map is global, but the sidebar links are locale-scoped. Crawler reads the wrong key.

## Correct extraction pattern

```python
import re, json, httpx

html = httpx.get(f"{BASE_URL}/nonexistent-test", timeout=30).text
sd = json.loads(
    re.search(r'window\.__VP_SITE_DATA__\s*=\s*deserializeFunctions\(JSON\.parse\("((?:[^"\\]|\\.)*)"',
              html, re.DOTALL).group(1)
    .replace('\\"', '"').replace('\\\\', '\\')
)

sidebar_links = []
def collect(items):
    for it in items or []:
        if isinstance(it, dict):
            if it.get("link"):
                sidebar_links.append(it["link"])
            if it.get("items"):
                collect(it["items"])

# ✅ Walk every locale, then dedupe
for loc in sd.get("locales", {}).values():
    sb = (loc.get("themeConfig") or {}).get("sidebar")
    if isinstance(sb, list):
        for section in sb:
            collect(section.get("items", []) if isinstance(section, dict) else [])
            if isinstance(section, dict):
                collect(section.get("items"))  # recurse into sub-groups

seen, unique = set(), []
for l in sidebar_links:
    if l not in seen:
        seen.add(l); unique.append(l)
```

## Expected counts for open.inexbot.com

- **zh (`/`)**: 178 pages
- **en (`/en/`)**: 178 pages
- **Total after dedupe**: 356

If you get significantly fewer, the site added/removed pages — re-check `__VP_HASH_MAP__` count (currently 382) vs. sidebar link count.

## Likely affects sister skill too

`inexbot-knowledge-base` (doc.inexbot.com) shares this crawler pattern. If it ever reports 0 docs, apply the same fix there — but verify first, since `doc.inexbot.com` may use a different site layout.