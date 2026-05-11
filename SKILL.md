---
name: inexbot-open-knowledge-base
description: "纳博特开放平台知识库 RAG：每天定时爬取 open.inexbot.com，由 hermes-skill-proxy 在请求时进行内存检索并注入 system prompt。"
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [knowledge-base, rag, inexbot, open-platform, crawler]
    category: productivity
    related_skills: ["inexbot-knowledge-base"]
---

# 纳博特开放平台知识库（RAG）

知识库源：https://open.inexbot.com

## 架构

```
用户问题 → hermes-skill-proxy (8643)
              ↓ 内存检索 index.json（双索引并行，毫秒级）
              ↓ 注入检索结果到 system prompt
              → Hermes Gateway (8642)
                → MiniMax LLM
                  → 流式回答
```

hermes-skill-proxy 同时检索两个知识库：
- **inexbot** — doc.inexbot.com（产品技术文档，126 篇）
- **inexbot-open** — open.inexbot.com（开放平台/二次开发，本仓库）

## 知识库信息

| 项目 | 值 |
|------|-----|
| 源站 | https://open.inexbot.com |
| 内容 | 纳博特开放平台文档：控制器/示教器/上位机二次开发、JSON 协议、ROS、主站库、HAL |
| 存储路径 | `~/.hermes/kb/inexbot-open/` |
| 索引文件 | `~/.hermes/kb/inexbot-open/index.json` |
| Markdown | `~/.hermes/kb/inexbot-open/md/` |

## 爬虫

### 手动爬取

```bash
python3 ~/.hermes/skills/productivity/inexbot-open-knowledge-base/scripts/crawler.py
python3 ~/.hermes/skills/productivity/inexbot-open-knowledge-base/scripts/crawler.py --force  # 强制重爬
```

### 依赖

```bash
pip3 install httpx jieba pyyaml beautifulsoup4
```

## Proxy 检索逻辑

每次收到用户问题时，hermes-skill-proxy 在两个知识库中并行检索：

1. jieba 分词
2. 标题命中 ×4，描述命中 ×2，正文词频 ×0.5
3. 每个知识库取 top-3 结果
4. 合并注入 system prompt

Proxy 每 5 小时自动重载索引（与 cronjob 每日爬取配合）。

## 定时任务

建议在 Hermes 上配置 cronjob 每日爬取：

```bash
cronjob action=create \
  name="open-inexbot daily crawl" \
  prompt="运行 python3 ~/hermes-skill-proxy/../.hermes/skills/productivity/inexbot-open-knowledge-base/scripts/crawler.py" \
  schedule="0 12 * * *" \
  deliver=local
```
