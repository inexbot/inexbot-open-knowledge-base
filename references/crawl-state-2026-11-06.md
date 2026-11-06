# 爬取状态报告 — 2026-11-06

**结论**：✅ **799/558 连续第十七次持平（纯稳态）**，index.json 与 11-05 逐字节相同，
零网络请求，3:23.5 落在稳态带内。**本轮同时闭合了 11-05 遗留的「未提交」问题。**

---

## 一、爬取结果

| 项目 | 值 | 与 11-05 对比 |
|---|---|---|
| 爬取页数 | 799 / 799 | 持平（连续第 17 次） |
| index.json 条目 | 799 | 持平 |
| index.json 字节 | **2,450,869** | **逐字节相同** ✅ |
| locale 拆分 | en=178, kr=178, zh=443 | 持平 |
| 耗时 | **3:23.5** | 稳态带内（3:00–3:47） |
| 网络抓取次数 | **0**（`grep -c "✓"` = 0） | 全缓存命中 |
| `raw/` 最新 mtime | 2026-10-23 | 未变 → 上游零变动 |
| `md/` 今日重写 | 0 | — |
| `.tmp` 残留 | 无 | ✅ 原子写正常 |

`check_crawl_state.py` verdict = **IDENTICAL**（content byte-for-byte unchanged）。

> ⚠️ 判读依据：docs 数持平 + **字节数完全相同** = 真稳态。
> 若字节数不同则需跑 `diagnose_byte_change.py` 区分「上游改动」vs「本地抽取变更」。
> 本轮两者皆无 → 纯稳态，无需任何进一步处置。

---

## 二、标准验证序列（5 步 + 1 步可选）

| # | 检查 | 结果 |
|---|---|---|
| 1 | `check_crawl_state.py` | ✅ IDENTICAL，799 条 / 2,450,869 B |
| 2 | `check_index_hygiene.py` | ✅ 零宽 0 / 空标题 0 / 幻影 token 可达 0 / 旧 API 可达 0 / 空 snippet 34（上游空目录页，正常） |
| 3 | `check_retrieval_chain.py` | ✅ 静默降级 0；短正文 4 条（61–71 B，上游占位页，与 10-25 基线一致） |
| 4 | `check_proxy_health.py` | ✅ inexbot-open=799 / inexbot=558，均 loaded=True |
| 5 | `check_e2e_request.py` | ✅ **12/12 全 200**，见下 |
| 6 | `check_proxy_env.py --units` | ✅ 线上 5 个变量全部到位且等于代码默认值；两份 unit 逐项一致 |

**未 restart proxy 的理由**（两条判据都指向「不需要」）：

1. **内容没变** → index.json 逐字节未变 → 爬前爬后都是 799 → 无需为内容 restart。
2. **代码差异是纯 docstring** → 线上进程加载的是 `846b3de`（11-05 11:03 启动），
   HEAD 是 `abb129c`（11-05 11:14），diff **只有 `_md_slug_candidates()` 里新增的注释**
   （AST 结构差异仅为 docstring 文本）→ **行为完全等价** → 无需为部署 restart。
   （11-05 遗留的 `HERMES_TIMEOUT=1800` 部署项**早已闭环**：线上 environ 实测
   `HERMES_TIMEOUT` sha12=`e49ec846db75` = 代码默认值 = unit 值，三方一致。）

---

## 三、e2e 探针（唯一能抓到 proxy→gateway→LLM 链路故障的检查）

- runs/query = 4，client timeout = 1860s，**12/12 全 200**
- 耗时区间见运行日志，**无一触到 timeout 边界**
- 进程切片后 journal：**HTTP 500 = 0、HTTP 502 = 0、HTTP 200 = 33、`Unknown key name` = 0**
- ⭐ 这连续第 2 天 **HTTP 502 = 0**（11-03 每天 3 次 → 11-05 修复后 → 11-05/11-06 连续为 0）
  → **`HERMES_TIMEOUT=1800` 的修复在真实链路上确认生效**

> 📌 探针跑法（勿忘两个前置条件）：
> ① 先 `ps -eo pid,etime,cmd | grep -E "[c]heck_e2e|[c]heck_retrieval"` 确认**没有别的 probe 在飞**；
> ② 必须 `terminal(background=true)`，foreground 会被 60s clamp 掐掉且**探针进程往往还活着**
> → 变成两个 probe 并发 → 污染 502 判定。

---

## 四、本轮闭合的遗留：11-05 的工作**实际没提交**

11-05 报告的 commit hash 写的是 `b321dcc`，但那**只 commit 了文档**，
以下 3 个文件当时是**未跟踪 / 未提交**状态（`git status` 实测）：

| 文件 | 11-05 状态 | 本轮动作 |
|---|---|---|
| `scripts/check_proxy_env.py` | `??` 未跟踪 | ✅ 已 `add` + `commit` + `push` |
| `references/proxy-deployment-verification.md` | `??` 未跟踪 | ✅ 已入库 |
| `references/deployment-readiness-checklist.md` | `??` 未跟踪 | ✅ 已入库 |
| `SKILL.md`（v1.17.0 → v1.18.0） | `M` 未提交 | ✅ 已入库 |
| `references/shared-proxy-service-pitfalls.md` | `M` 未提交 | ✅ 合并姊妹版后入库 |

> 📌 **教训复现（陷阱 14 第 3 次复发）**：11-01、11-02 各复发一次，本轮**第 3 次**。
> **未提交 = 下次 `git pull` 静默回退** → `check_proxy_env.py` 这个
> 「补丁真的上线了」守卫会**悄悄消失**，而 `crawler.py` 里的三修还在 →
> **看起来一切正常，实则失去守卫**。这类失效是**静默的**。
> → **本轮起，报告写「遗留：无」之前必须 `git status` 核过。**

---

## 五、共享文件同步（`references/shared-proxy-service-pitfalls.md`）

**本 skill 那份 vs 姊妹那份的 diff 结果**：

| | 行数 | 字节 | sha1 |
|---|---|---|---|
| 姊妹（`inexbot`） | 787 | 38,872 | `1843b3db9eef` |
| 本 skill（合并前） | 760 | 37,406 | `8bb8808046e4` |

**diff 结论：双方各有独有内容 → 不能盲目 `cp`。**

- 姊妹独有（我们缺）→ 已补：
  - **陷阱 11 的「三连假阳性指纹」**（11-05 第 4 次复发时归纳的归纳表：slug 契约 0/558 +
    孤儿数恰等条目数 + 检索链路实测正常 ⇒ 几乎必然是审计脚本自己写错）
  - **陷阱 17 的「2026-11-05 已闭环」注解**（300s 时代的历史状态 + 归因法判据要跟着 timeout 变）
- 本 skill 独有（姊妹缺）→ **已保留**：
  - 陷阱 20 里「本 KB 已有现成的自动化守卫 `check_proxy_env.py --units`」段落
  - 「手工等价流程见姊妹 skill 的 `deployment-readiness-checklist.md`」交叉引用

**合并方式**：`/tmp/merge_shared_pitfalls.py`（difflib 三方合并：**以姊妹为基底 +
把本 skill 独有的 hunk 重新贴回**），**不是** `cp`。
校验结果：**姊妹 21 个 section 全部保留（missing=0）**、**本 skill 0 个 section 丢失**。

---

## 六、其它核查

- **重载链活着**：定时器线程 `Fri Nov 6 07:03:19`（= 主进程启动 + 20h = 第 4 次 5h 排期）
- **端口干净**：`8643`（proxy）+ `8642`（gateway），无遗留压测实例
- **共享文件交叉引用全部可解析**：5 个 `references/*.md` 引用 → 3 个在本 skill、2 个在姊妹 skill，均存在
- **姊妹 KB 未代提交**：姊妹 `inexbot-knowledge-base` 工作树的改动是它自己 cron 的职责，本 skill 未触碰

---

## 七、待办

**无。** 本轮已完成：爬取 + 5 步验证 + 共享文件合并 + 11-05 遗留入库（已 push）。
`git status` 已核过，工作树干净（除被跟踪的 `.index-snapshot.json`，良性）。
