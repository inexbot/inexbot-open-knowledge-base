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
from urllib.parse import urljoin, unquote
from html import unescape

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
    return re.sub(r'[<>:\|"?*]', '', text.strip().replace("/", "-").replace("\\", "-"))

def _pre_to_md(pre):
    """Render a <pre> element as a fenced code block.

    VitePress/shiki puts the language on the wrapper <div class="language-xxx">
    or on <code class="language-xxx">, not necessarily on <pre> itself, so
    look in all three places before falling back to an untagged fence.
    """
    lang = ""
    for holder in (pre, pre.parent, pre.find("code")):
        if holder is None:
            continue
        for cls in (holder.get("class") or []):
            if cls.startswith("language-"):
                lang = cls[len("language-"):]
                break
        if lang:
            break
    if not lang:
        for holder in (pre, pre.parent):
            if holder is None:
                continue
            m = re.search(r"language-([A-Za-z0-9+#]+)", str(holder.get("class") or ""))
            if m:
                lang = m.group(1)
                break
    code = pre.find("code")
    ct = code.get_text() if code else pre.get_text()
    return [f"```{lang}", ct.rstrip(), "```", ""]

def _text_without_pre(li):
    """Return the text of a list item with any embedded <pre> code removed."""
    clone = BeautifulSoup(str(li), "html.parser")
    for pre in clone.find_all("pre"):
        pre.decompose()
    return clone.get_text(strip=True)

# 零宽字符：U+200B / U+200C / U+200D（零宽空格/非连接符/连接符）+ BOM
# 用显式转义而不是字面量 —— 字面零宽字符在源码里不可见，容易被误删/被编辑器吞掉。
_ZERO_WIDTH = "[" + "".join(chr(c) for c in (0x200B, 0x200C, 0x200D, 0xFEFF)) + "]"

def clean_text(s: str) -> str:
    """
    清洗文本：去掉零宽字符（U+200B 等）、NBSP 和行尾空白。

    open.inexbot.com 的 <h1> 普遍带一个 U+200B 零宽空格（VitePress 编辑器残留），
    例如 'C++ 上位机开发\\u200b'。不去掉的话：
      1. 每个注入给 LLM 的标题末尾都挂一个不可见字符，引用链接显示时带怪字符；
      2. 标题分词时 jieba 会把 U+200B 单独切成一个 token（len=1，被
         `len(w) >= 2` 过滤掉，影响有限），但对展示和精确匹配仍有干扰。

    注意：只去零宽字符 + 行尾空白，**不压缩内部空格/制表符** —— 正文含代码块，
    压缩缩进会破坏代码内容。

    （姊妹 KB inexbot-knowledge-base 的 crawler.py 已有同名实现并先行落地，
      本函数是同步过来的，两边行为保持一致。）
    """
    if not s:
        return ""
    # 零宽字符 + BOM：直接删除（不是替换成空格，避免把词切开）
    s = re.sub(_ZERO_WIDTH, "", s)
    # NBSP 不换行空格 → 普通空格（中文正文里常出现）
    s = s.replace("\xa0", " ")
    # 行尾空白
    s = "\n".join(line.rstrip() for line in s.split("\n"))
    return s.strip()

def save_json(obj, path):
    """
    原子写入 JSON。

    ⚠️ 必须先写临时文件再 os.replace()：hermes-skill-proxy 每 5 小时读一次
    index.json，直接 open(path,"w") 会先把文件截断成空，再慢慢写入 ——
    这期间 proxy 若正好读到，会 json.load() 抛错（进而触发定时重载链断裂）。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def save_yaml(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, allow_unicode=True, default_flow_style=False)

# ── 第1步：获取页面列表 ────────────────────────────────────────────────────────

def fetch_vitepress_metadata():
    log("正在获取 VitePress 站点配置...")
    resp = httpx.get(urljoin(BASE_URL, "/nonexistent-page-test"),
                     headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
    # VitePress returns 404 for nonexistent pages but embeds metadata in the body.
    # Only raise on server errors (5xx); allow client errors (404 etc.) to proceed.
    if resp.status_code >= 500:
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

        # VitePress i18n sites put themeConfig.sidebar under each locale.
        # Merge sidebar lists from all locales so we crawl both zh and en pages.
        locales = site_data.get("locales", {}) or {}
        theme_cfg_top = site_data.get("themeConfig", {}) or {}
        sidebar_groups = []
        if isinstance(locales, dict) and locales:
            for _loc_key, loc_data in locales.items():
                if not isinstance(loc_data, dict):
                    continue
                loc_tc = loc_data.get("themeConfig", {}) or {}
                sb = loc_tc.get("sidebar") or loc_tc.get("nav")
                if isinstance(sb, list):
                    sidebar_groups.append(sb)
        else:
            sb = theme_cfg_top.get("sidebar") or theme_cfg_top.get("nav")
            if isinstance(sb, list):
                sidebar_groups.append(sb)

        for sidebar in sidebar_groups:
            for section in sidebar:
                collect_links(section.get("items", []) if isinstance(section, dict) else [])
                if isinstance(section, dict):
                    for sub in section.get("items", []) or []:
                        if isinstance(sub, dict) and "items" in sub:
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
    title = clean_text(h1.get_text(strip=True)) if h1 else ""
    desc_tag = soup.find("meta", attrs={"name": "description"})
    description = desc_tag["content"].strip() if desc_tag and desc_tag.get("content") else ""

    # 标题兜底：open.inexbot.com 上有 34 个「分类索引页」没有 <h1>
    # （如 /zh/06.控制器/01.文档/、/zh/07.示教器/04.参考/变更日志），
    # 它们在 sidebar 里有链接、正文却是空的（上游就是空目录页）。
    # 标题为空 = 丢掉 proxy 检索的标题权重（标题 ×3 / 短语命中 ×20），
    # 这些页只能靠 description（"纳博特科技官方SDK文档"）勉强参与匹配。
    # 这里依次回退 og:title → URL 末段 → description。
    if not title:
        og = soup.find("meta", attrs={"property": "og:title"})
        if og and og.get("content"):
            title = clean_text(og["content"])

    if not title:
        # URL 末段就是文档真实名称（如 '错误码表'），比通用 description 更贴题
        seg = unquote(url.rstrip("/").split("/")[-1]) if url.rstrip("/") else ""
        seg = unescape(seg)          # &amp; → &
        seg = clean_text(seg)
        seg = re.sub(r"\.html?$", "", seg).strip()
        if seg and not seg.lower().startswith(("readme", "index")):
            title = seg[:120]

    if not title:
        cand = clean_text(description)[:120]
        # 通用描述（如 '纳博特科技官方SDK文档'）信息量太低，跳过
        if cand and cand != "纳博特科技官方SDK文档" and cand.lower() != "not found":
            title = cand

    article = soup.find("article", class_="page") or \
              soup.find("div", id="content-container") or \
              soup.find("main") or soup.find("div", class_="content")

    content_md, keywords_set = "", set()
    if article:
        for tag in article.find_all(["nav", "script", "style", "footer", "aside", "button", "input"]):
            tag.decompose()
        # VitePress renders a language badge as <span class="lang">cpp</span> right
        # before <pre>.  get_text() glues it onto the following code text, which
        # fabricates identifiers like "cppset_tool_hand_number" (badge "cpp" +
        # "set_tool_hand_number").  Strip the badges before extracting text.
        for badge in article.find_all("span", class_="lang"):
            badge.decompose()
        content_md, keywords_set = _element_to_md(article, base_url=url)

    return {"title": title, "description": description, "content_md": clean_text(content_md.strip()), "url": url, "keywords": sorted(keywords_set)}

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
            lines.extend(_pre_to_md(child))
        elif tag in ("ul", "ol"):
            for i, li in enumerate(child.find_all("li", recursive=False), 1):
                prefix = "- " if tag == "ul" else f"{i}. "
                pre = li.find("pre")
                if pre is None:
                    lines.append(prefix + li.get_text(strip=True))
                    continue
                # List item that embeds a code block: keep the prose as the list
                # item and render the code as its own fenced block, instead of
                # flattening the code into the prose line.
                prose = _text_without_pre(li)
                if prose:
                    lines.append(prefix + prose)
                for ln in _pre_to_md(pre):
                    lines.append(("  " + ln) if ln else "")
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
