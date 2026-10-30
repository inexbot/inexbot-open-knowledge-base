# 检索链路验证（两个 KB 共用 proxy 的 read_full_content）

## 为什么这是独立于「爬虫」的一条轴

爬虫成功 ≠ 检索正常。这两件事被 proxy 的**同一个函数**隔开：

```
crawler.py  ──slugify()──▶  md/<slug>.md
                                 ▲
                                 │  read_full_content() 必须用同一套 slug 算法找得到
                                 │
hermes-skill-proxy.py ──search_all_kb()──▶ content_snippet 注入 system prompt
```

两边 slug 算法一旦不一致，后果分两档：

| 档位 | 表现 | 危险度 |
|---|---|---|
| `md_path.exists()` 抛 `OSError [Errno 36]` | 冒泡到 `search_single_kb` → `search_all_kb` → **整个 `/v1/chat/completions` 500** | 高（有报错，容易发现） |
| 两个候选 slug 都没找到 | **静默降级**成 index.json 的 800 字 `content_snippet` | **最高（无任何报错线索）** |

第二种最危险：`/health` 照样返回 `docs=558 loaded=true`，爬虫照样报「558/558 成功」，
索引无缺失无孤儿 —— **所有表层健康检查都看不出问题**。

## 判定标准：看长度，不看有没有报错

| `snippet_len` | 含义 |
|---|---|
| `> 800` | 正文命中 ✅（正文上限 4000） |
| `== 800` | **静默降级成 index 摘要 = BUG** |
| `< 200` | 该页正文本来就短（如伺服报错页只有一行）—— **不是 bug**，对照 `md/` 实际大小确认 |

`800` 是 `index.json` 里 `content_snippet` 的硬上限，**是个特征值**：
「恰好等于 800」几乎必然是摘要兜底，不是巧合。

### ⚠️ 短正文（`< 800`）还要再看一层：md 实际字节数（2026-10-29 补充）

`verify_kb.py` 输出的 `note: 短 snippet 247 inexbot / ... ← 疑似静默降级`
只是「长度 < 800」的粗筛，**不等于有 BUG**。真正的判别是看 md 文件的实际字节数：

| `snippet_len` | md 实际字节数 | 结论 |
|---|---|---|
| `== 800` | — | **静默降级**（index 摘要兜底）→ BUG |
| `< 800` | `== snippet_len` | **正文已完整读取**，只是这一页本身就很短（FAQ 页）→ 正常 |
| `< 800` | `> snippet_len` | 部分读取 → 查 slug 契约 |

2026-10-29 实测（姊妹 KB）：5 条 note 全部满足 `md_bytes == snippet_len`
（247 / 277 / 418 / 440 / 468 字节），即**磁盘正文被完整取出**，
是「示教器无法开机」「伺服错误」这类本身就两三行的 FAQ 页 → **无 BUG**。

> 💡 核验脚本见姊妹 skill
> `inexbot-knowledge-base/references/proxy-memory-vs-disk-comparison.md`
> （也收录了姊妹 KB 现场更正的两条：内存索引必须**token 级**比对、
> 手写 slug 检查会崩在 `OSError [Errno 36]`）。

## 两个 KB 共用同一个函数 —— 必须一起验

`hermes-skill-proxy` 同时服务 `inexbot`（doc.inexbot.com）和 `inexbot-open`
（open.inexbot.com），**共用 `read_full_content()`**。所以：

- 姊妹 KB 修好了，**不代表**本 KB 也好了
- 两个 KB 的 URL 形态不同，slug 碰撞的表现也不同：
  - `inexbot`：URL 长、中文 + URL 编码混杂、`/zh/` 前缀，容易超 255 字节触发 `OSError`
  - `inexbot-open`：URL 短、带 `en-`/`kr-`/`zh-` locale 前缀，slug 形态不同

**因此验证脚本要一次覆盖两个 KB**，用同一个脚本、同一套判定标准。

## 标准动作

```bash
/usr/bin/python3 ~/.hermes/skills/productivity/inexbot-open-knowledge-base/scripts/check_retrieval_chain.py
```

- 对两个 KB 各跑若干条查询，检查每条结果的 `content_snippet` 长度
- 打印每条：`score` / `title` / `snippet_len` / 判定标记
- 汇总：静默降级数、短正文数、是否抛异常
- exit 0 = 链路正常；exit 1 = 有降级或异常

⚠️ 两个硬约束：
- **必须 `/usr/bin/python3`**（proxy 依赖 flask，沙盒 `python3` 没装）
- **必须走文件路径**（本地 security policy 禁 `python3 -c` 和 `rm`）

## 2026-10-24 实测结果

**`inexbot`（姊妹 KB）—— 已修复 ✅**

proxy 侧已改为 `_md_slug_candidates()`：生成多个候选（`unquote` 后的真名、
`url_quote` 再编码等），谁先存在用谁，且 `exists()` 包在 try/except 里
（文件名过长等异常一律降级成 `""`，绝不冒泡成 500）。

| 查询 | 结果 |
|---|---|
| `冲压工艺 手册 参数设置` | 5 条全部 `snippet_len=4000` |
| `示教器 换图` | 顶层 `snippet_len=4000` |
| `通讯协议 地址码 Modbus 寄存器` | 顶层 `通讯协议与地址码`，`snippet_len=2701` |
| `伺服报警 0x0051 IPM故障` | 顶层 `snippet_len=71` —— **该页正文本来就只有一行，不是 bug** |
| `NexAutoCail 标定` | 顶层 `snippet_len=4000` |

**`inexbot-open`（本 KB）—— 需用 `check_retrieval_chain.py` 实测确认。**

2026-10-23 的记录写的是「极可能同样中招，但需实测确认」——这个待办**至今没人做**。
跑一次 `check_retrieval_chain.py` 就能结案：它同时覆盖两个 KB，有降级就 exit 1。

## 触发复验的时机

- 改了 `hermes-skill-proxy.py` 的 `read_full_content()` / `_md_slug_candidates()`
- 改了任一 KB 的 `crawler.py` 里 `slugify()`（**两边各自复刻必然漂移**）
- 改了任一 KB 的 `retrieve.py` / `check_crawl_state.py` 里的 slug 副本
- proxy 升级 / 换机器后首次跑

## 与「增量爬虫盲区」的关系

这是**两个独立的盲区**，别混淆：

| 盲区 | 位置 | 症状 | 对策 |
|---|---|---|---|
| 增量爬虫不重抓 | crawler 的 `raw/`+`md/` 存在就跳过 | 上游改了正文，本地永远停在旧内容 | `refresh_drift.py`（姊妹 skill）/ 精准失效 `.stale-bak`（本 skill） |
| slug 契约断裂 | proxy 的 `read_full_content()` | 本地 md 有内容，但 proxy 读不到 | `check_retrieval_chain.py` |

前者是「数据没更新」，后者是「数据更新了但读不出来」。**两个都得查。**
