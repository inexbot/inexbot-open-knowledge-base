#!/usr/bin/env python3
"""
inexbot-open 知识库爬虫
============================
VitePress 站点，https://open.inexbot.com

与 inexbot-knowledge-base/crawler.py 完全相同的逻辑，只改了目标站点。

爬取策略：
1. 从 404 页面解析 __VP_HASH_MAP__ 获取所有页面链接
2. 逐页抓取 HTML，提取正文转 Markdown
3. 用 jieba 分词构建倒排索引 → index.json

存储结构：
  ~/.hermes/kb/inexbot-open/
  ├── raw/           # 原始 HTML
  ├── md/            # 提取的 Markdown
  ├── index.json     # 全量搜索索引
  └── meta.yaml      # 爬取元数据
"""

import os, sys, re, json, time, hashlib, datetime
from pathlib import Path
from urllib.parse import urljoin

import httpx, jieba, yaml
from bs4 import BeautifulSoup

# ── 配置 ────────────────────────────────────────────────────────────────────

BASE_URL = "https://open.inexbot.com"
KB_ROOT = Path.home() / ".hermes" / "kb" / "inexbot-open"
RAW_DIR  = KB_ROOT / "raw"
MD_DIR   = KB_ROOT / "md"
INDEX_F  = KB_ROOT / "index.json"
META_F   = KB_ROOT / "meta.yaml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; HermesBot/1.0)",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

TIMEOUT = 30
CONCURRENCY = 8
PAUSE_MIN = 0.3
PAUSE_MAX = 0.8

# ── 工具 ─────────────────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def slugify(text):
    return re.sub(r'[<>:\"|?*]', '', text.strip().replace("/", "-").replace("\\", "-"))

def save_json(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def save_yaml(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, allow_unicode=True, default_flow_style=False)

# ── 第1步：获取页面列表 ────────────────────────────────────────────────────────

def fetch_vitepress_metadata():
    log("正在获取 VitePress 站点配置...")
    resp = httpx.get(urljoin(BASE_URL, "/nonexistent-page-test"),
                     headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
    resp.raise_for_status()
    html = resp.text

    # 从 404 页面提取 __VP_HASH_MAP__
    hm_match = re.search(
        r'window\.__VP_HASH_MAP__\s*=\s*JSON\.parse\("((?:[^"\\]|\\.)*)"',
        html, re.DOTALL
    )
    hash_map = {}
    if hm_match:
        raw = hm_match.group(1)
        raw = raw.replace('\\"', '"').replace('\\\\', '\\')
        hash_map = json.loads(raw)

    # 提取 __VP_SITE_DATA__
    sd_match = re.search(
        r'window\.__VP_SITE_DATA__\s*=\s*deserializeFunctions\(JSON\.parse\("((?:[^"\\]|\\.)*)"',
        html, re.DOTALL
    )
    sidebar_links = []
    if sd_match:
        raw = sd_match.group(1)
        raw = raw.replace('\\"', '"').replace('\\\\', '\\')
        site_data = json.loads(raw)

        def collect_links(items):
            for item in items:
                if isinstance(item, dict):
                    if item.get("link"):
                        sidebar_links.append(item["link"])
                    if "items" in item:
                        collect_links(item["items"])

        theme_cfg = site_data.get("themeConfig", {})
        sidebar = theme_cfg.get("sidebar", theme_cfg.get("nav", []))
        if isinstance(sidebar, list):
            for section in sidebar:
                collect_links(section.get("items", []))
                for sub in section.get("items", []):
                    if "items" in sub:
                        collect_links(sub["items"])

    seen, unique = set(), []
    for link in sidebar_links:
        if link not in seen:
            seen.add(link)
            unique.append(link)

    log(f"  发现 {len(unique)} 个页面，{len(hash_map)} 个 hash")
    return {"links": unique, "hash_map": hash_map}

# ── 第2步：提取正文 ───────────────────────────────────────────────────────────

def extract_content(html, url):
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""
    desc_tag = soup.find("meta", attrs={"name": "description"})
    description = desc_tag["content"].strip() if desc_tag and desc_tag.get("content") else ""

    article = soup.find("article", class_="page") or \
              soup.find("div", id="content-container") or \
              soup.find("main") or soup.find("div", class_="content")

    content_md, keywords_set = "", set()
    if article:
        for tag in article.find_all(["nav", "script", "style", "footer", "aside", "button", "input"]):
            tag.decompose()
        content_md, keywords_set = _element_to_md(article, base_url=url)

    return {"title": title, "description": description, "content_md": content_md.strip(), "url": url, "keywords": sorted(keywords_set)}

def _element_to_md(element, depth=0, base_url=""):
    lines, keywords = [], set()
    for child in element.children:
        if isinstance(child, str):
            text = child.strip()
            if text:
                lines.append(text)
                keywords.update(jieba.cut(text))
            continue
        tag = child.name or ""
        if tag in ("script", "style", "svg", "path", "noscript"):
            continue
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            text = child.get_text(strip=True)
            if text:
                lines.append(f"{'#' * level} {text}")
                keywords.update(jieba.cut(text))
        elif tag == "table":
            rows = child.find_all("tr")
            if rows:
                hc = rows[0].find_all(["th", "td"])
                lines.append("| " + " | ".join(c.get_text(strip=True) for c in hc) + " |")
                lines.append("| " + " | ".join("---" for _ in hc) + " |")
                for row in rows[1:]:
                    cells = row.find_all(["td", "th"])
                    lines.append("| " + " | ".join(c.get_text(strip=True) for c in cells) + " |")
                lines.append("")
        elif tag == "pre":
            code = child.find("code")
            ct = code.get_text() if code else child.get_text()
            lang = code.get("class", [""])[0].replace("language-", "") if code else ""
            lines.append(f"```{lang}")
            lines.append(ct.rstrip())
            lines.append("```")
            lines.append("")
        elif tag in ("ul", "ol"):
            for i, li in enumerate(child.find_all("li", recursive=False), 1):
                prefix = "- " if tag == "ul" else f"{i}. "
                lines.append(prefix + li.get_text(strip=True))
            lines.append("")
        elif tag == "hr":
            lines.append("---")
            lines.append("")
        elif tag == "blockquote":
            for ln in child.get_text(strip=True).splitlines():
                lines.append(f"> {ln}")
            lines.append("")
        elif tag in ("p", "div"):
            inner, ik = _element_to_md(child, depth + 1, base_url)
            if inner.strip():
                lines.append(inner)
                keywords.update(ik)
            else:
                text = child.get_text(strip=True)
                if text:
                    lines.append(text)
                    keywords.update(jieba.cut(text))
        elif tag == "img":
            src = child.get("src", "")
            alt = child.get("alt", "")
            if src:
                abs_src = urljoin(BASE_URL, src) if BASE_URL else src
                lines.append(f"![{alt}]({abs_src})")
        else:
            inner, ik = _element_to_md(child, depth + 1, base_url)
            if inner.strip():
                lines.append(inner)
            keywords.update(ik)
    return "\n".join(lines), keywords

# ── 第3步：构建索引 ──────────────────────────────────────────────────────────

def build_search_index(pages):
    log("正在构建搜索索引...")
    index = {}
    for page in pages:
        path = page["path"]
        title = page.get("title", "")
        desc = page.get("description", "")
        content = page.get("content_md", "")[:1000]  # 前1000字作摘要
        full_text = f"{title} {desc} {content}"
        words = [w for w in jieba.cut(full_text) if len(w) >= 2]
        word_counts = {}
        for w in words:
            word_counts[w] = word_counts.get(w, 0) + 1
        index[path] = {
            "title": title, "description": desc, "path": path,
            "content_snippet": content[:800],
            "keywords": list(word_counts.keys())[:50],
            "word_counts": word_counts,
        }
    log(f"  索引完成，共 {len(index)} 条")
    return index

# ── 第4步：主流程 ──────────────────────────────────────────────────────────

def crawl(force=False):
    start = datetime.datetime.now()
    log(f"开始爬取 open.inexbot.com → {KB_ROOT}")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    MD_DIR.mkdir(parents=True, exist_ok=True)

    if force:
        import shutil
        for d in [RAW_DIR, MD_DIR]:
            if d.exists():
                shutil.rmtree(d)
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        MD_DIR.mkdir(parents=True, exist_ok=True)
        log("强制重爬：已清除缓存")

    meta = fetch_vitepress_metadata()
    links = meta["links"]

    client = httpx.Client(headers=HEADERS, timeout=TIMEOUT,
                          limits=httpx.Limits(max_connections=CONCURRENCY))

    pages, failed = [], []
    total = len(links)
    for i, link in enumerate(links, 1):
        url = urljoin(BASE_URL, link)
        slug = slugify(link.lstrip("/"))
        raw_path = RAW_DIR / f"{slug}.html"
        md_path = MD_DIR / f"{slug}.md"

        if not force and raw_path.exists() and md_path.exists():
            try:
                with open(raw_path, encoding="utf-8") as f:
                    html = f.read()
                pd = extract_content(html, url)
                pd["path"] = link
                pages.append(pd)
                continue
            except Exception:
                pass

        try:
            resp = client.get(url, follow_redirects=True)
            html = resp.text
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(html)
            pd = extract_content(html, url)
            pd["path"] = link
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(f"# {pd['title']}\n\n")
                if pd['description']:
                    f.write(f">{pd['description']}\n\n")
                f.write(pd['content_md'])
            pages.append(pd)
            log(f"  [{i}/{total}] ✓ {link}")
        except Exception as e:
            failed.append((link, str(e)))
            log(f"  [{i}/{total}] ✗ {link}: {e}")
        time.sleep(PAUSE_MIN + (PAUSE_MAX - PAUSE_MIN) * (i % 5) / 5)

    client.close()

    index = build_search_index(pages)
    save_json(index, INDEX_F)

    meta_info = {
        "crawled_at": start.isoformat(),
        "finished_at": datetime.datetime.now().isoformat(),
        "total_links": total,
        "pages_crawled": len(pages),
        "pages_failed": len(failed),
        "version": start.strftime("%Y%m%d"),
    }
    save_yaml(meta_info, META_F)

    elapsed = datetime.datetime.now() - start
    log(f"\n爬取完成！耗时 {elapsed}")
    log(f"  成功: {len(pages)} / {total}")
    if failed:
        log(f"  失败: {len(failed)}")
    return pages, index, meta_info

if __name__ == "__main__":
    force = "--force" in sys.argv
    pages, index, meta = crawl(force)
    print(f"\n最终结果：爬取 {meta['pages_crawled']} 页，索引: {INDEX_F}")
