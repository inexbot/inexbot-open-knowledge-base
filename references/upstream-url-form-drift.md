# 上游 URL 形态漂移 —— 本库（open.inexbot.com）视角（2026-11-21 实测）

> ⚠️ **姊妹 KB `inexbot-knowledge-base` 有同主题文件
> `references/upstream-url-suffix-routing.md`，写的是 doc.inexbot.com 的情况。
> 那边的「收紧（`.html` 后缀路由）」状态对**本库不适用**。**
> **本库走的是裸路径路由**，proxy 的 `url_suffix_mode: inexbot-open = "none"`。
> 本文件记录**本库**的形态与探测方法。

---

## ⭐ 0. 一句话结论（本库当前状态）

| 维度 | 本库 `inexbot-open`（open.inexbot.com） |
|---|---|
| index key 形态 | **明文中文**（`/zh/04.上位机/03.Python/02.接口/...`） |
| index 里的 `url_suffix` 字段 | **0 条存在**（本库 crawler 不写这个字段） |
| 路由形态 | **裸路径**（`/zh/...` 直接 200） |
| proxy 分派 | `url_suffix_mode: "none"` ⇒ 输出裸路径 |
| 2026-11-21 实测（30 条**真实 index 条目**） | **裸路径 30/30 = 200** ✅ |

⇒ **本库的 proxy 配置是正确，本轮不需要改任何代码。**

---

## 一、姊妹 KB 的「收紧」事故，本库**没有**中招

姊妹 KB（doc.inexbot.com）11-19 遇到：**上游改成 `.html` 后缀路由** →
裸路径全 404 → 用户点每个引用链接都是 404。
而当时 `/health`、检索链路、索引完整性、crawler（561/561 成功）**全部绿灯**。

11-21 姊妹复测发现上游又**放宽**了（两套并存）⇒ 姊妹写进共享 pitfalls §陷阱 43。

**本库在同一时间窗口内实测：裸路径 30/30 = 200 → 未受影响。**

⚠️ **但这不是永久保证** —— 上游**已经证明过它会切路由形态**
（姊妹那边 11-19 收紧、11-21 放宽，**两天切两次、方向相反**）。

⇒ **每轮 cron 都应跑一次双形态探测**：

```bash
/usr/bin/python3 scripts/check_citation_links.py --probe-both-forms
```

---

## 二、探测方法（三个要点，缺一个就会误判）

### 2.1 ⚠️ 必须用 `index.json` 的真实条目，**别手拼 URL**

姊妹 KB 11-21 实测踩到：手拼 `/zh/操作手册` 当普通页 + `.html` → **404**，
而 index 里同名的**真实条目**两种形态都 200
⇒ 手拼会得出「上游还在收紧」的**错误结论**。

**URL 必须从 index.json 取**，再按 `url_suffix` 拼出「带后缀」形态，两种都打一次。

### 2.2 归一化规则**必须按 KB 分开**（§陷阱 24 / 25）

| KB | index key 形态 | URL 构造 |
|---|---|---|
| `inexbot`（姊妹） | percent-encoded | `quote(path, safe="/%")`（保留既有 `%XX`） |
| `inexbot-open`（本库） | **明文中文** | `quote(path, safe="/")`（整体编码） |

**用同一条规则套两个 KB ⇒ 必然大面积假 miss。**

### 2.3 检测谓词必须作用在**已解码**的 key 上（§陷阱 26）

CJK 正则跑在**已编码**的 key 上 → **恒为空集** → 脚本静默退化成「全库随机抽」，
**看起来跑通了（60/60 200），但根本没测它声称要测的中文路径**。
⇒ **池子为空就应当报错退出**，绝不能静默兜底。

本库 key 本来就是明文中文，但脚本**仍然 `unquote()`** —— 万一将来 index 变编码态。

---

## 三、处置原则（照做，别自己推）

| 上游当前形态 | 该做什么 | 该**不**做什么 |
|---|---|---|
| **收紧**（裸 404 / 后缀 200） | 实施姊妹版 §四 的全套修复（crawler 写 `url_suffix` + proxy 按 KB 分派 + 6 个审计脚本） | ❌ 别只改 proxy 一个点 |
| **放宽**（两种都 200） | ⭐ **什么都不改** | ❌ **绝不**因为「裸形态现在能用」就删掉兼容层 / 把 proxy 改回别的方式 |

### 为什么「放宽」时也不能删兼容层

1. 上游**已经证明过**它会切路由形态 ⇒「今天能用」**不构成**「明天能用」的依据。
2. 一旦上游再次收紧，**删掉兼容层 = 100% 引用链接 404**，
   而且**表层检查会全绿** —— **只有实网链接检查能抓到**。
3. **保留兼容层在两种路由下都可达** ⇒ 保留是**严格更稳**的选择，**零成本**。

> **修复方向永远是「让链接在多种形态下都可达」或「让链接跟随上游当前形态」，
> 绝不是「因为当前形态能用就删掉兼容层」。**

---

## 四、本库的现成工具

| 工具 | 作用 |
|---|---|
| `scripts/check_citation_links.py` | 引用链接实网可达性（本库 URL 语义移植版） |
| `scripts/check_citation_links.py --probe-both-forms` | 双形态探测，判定当前路由档位 |
| `scripts/check_url_to_index_key.py` | proxy url → index key 反查（93/93） |

⚠️ **姊妹版的 `check_citation_links.py` 不要直接照抄** —— 它的
`kb_url()` 用 `safe="/%"` 且默认 `url_suffix=".html"`，那是**姊妹库**的语义。

---

## 五、姊妹 KB 的文件在哪（需要时去看）

- 姊妹 skill：`~/.hermes/skills/productivity/inexbot-knowledge-base/references/upstream-url-suffix-routing.md`
- 共享判读表：两库各自的 `references/shared-proxy-service-pitfalls.md` **§陷阱 39 / 43**
- 姊妹的实网探针：`~/.hermes/skills/productivity/inexbot-knowledge-base/scripts/check_citation_links.py`
