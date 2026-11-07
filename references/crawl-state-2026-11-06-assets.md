# 2026-11-06 复用资产：两个新脚本的由来

本轮（799/558 连续第 17 次持平的纯稳态 cycle）没有上游变更，但产出了**两个
可复用的脚本**，此前都是临时写在 `/tmp` 里 —— 现已入库为永久 `scripts/`。

---

## 一、`scripts/merge_shared_pitfalls.py`

### 触发场景

`scripts/diff_shared_pitfalls.py`（既有）诊断出两份
`references/shared-proxy-service-pitfalls.md` 的漂移，并在决策表末尾给出：

```
- both have distinct sections    -> hand-merge, keep BOTH
```

本轮实测正是这一档：

| | 行数 | 字节 | sha1 |
|---|---|---|---|
| 姊妹（`inexbot`） | 787 | 38,872 | `1843b3db9eef` |
| 本 skill（合并前） | 760 | 37,406 | `8bb8808046e4` |

**双方各有独有内容**：
- 姊妹独有 → 陷阱 11 的「三连假阳性指纹」表 + 陷阱 17 的「2026-11-05 已闭环」注解
- 本 skill 独有 → 陷阱 20 里的 `check_proxy_env.py --units` 守卫段 +
  `deployment-readiness-checklist.md` 交叉引用

### 为什么「hand-merge」不够

手工合并一个 **39 KB / 21 个编号 section** 的文件，极易漏掉或重复，
而且失败是**静默的**——文件看起来完全正常，只是 `git diff` 里冒出一个很大的 hunk。
更糟的是**漏掉的正是「对方独有的段落」**，而那往往正是刚被另一位 agent 写进去的
新坑记录（陷阱 11 的指纹表就是「已复发 4 次」的归纳，丢了就没了）。

### 脚本做的事

difflib 三方合并，**以姊妹为基底**：

| opcode | 取谁 | 理由 |
|---|---|---|
| `equal` | 姊妹 | 相同部分 |
| `delete` | **姊妹** | 姊妹独有内容必须**保留** |
| `insert` | **本 skill** | 本 skill 独有的 hunk 必须**贴回**（盲 cp 会丢） |
| `replace` | 姊妹 + 本 skill | 两边都保留 |

然后**按 section 标题双向校验**：
- 姊妹的每个 `## ` 标题都必须出现在合并结果里（missing 必须 = 0）
- 本 skill 的每个 `## ` 标题都必须出现在合并结果里（lost 必须 = 0）

任一不满足 → **exit 1，明确提示「DO NOT commit」**。

### 本轮实测结果

```
sister sections: 21 | merged sections: 21 | missing from merged: 0
our sections lost: 0
merged: 797 lines / 39,560 bytes (our-only hunks re-added: 2)
```

合并后两份 sha **归一**为 `50ce85500979`，5 个交叉引用全部可解析
（3 个在本 skill、2 个在姊妹 skill）。

### 用法

```bash
python3 scripts/merge_shared_pitfalls.py --check         # 干跑
python3 scripts/merge_shared_pitfalls.py                   # 写盘到本 skill
python3 scripts/merge_shared_pitfalls.py --sync-sister     # 同时同步姊妹那份
```

⚠️ **只有「双方各有独有 section」才需要跑它。**
若一方是严格超集，走「反向补齐」更简单，**不要**跑 merge（merge 在超集情形下
会产生冗余重复）。

---

## 二、`scripts/check_proxy_staleness.py`

### 触发场景

SKILL.md 原有的「该不该 restart proxy」判据第 2 条是
「用**补丁文件 mtime** vs 进程启动时间确认线上是否带最新代码」。

本轮实测触发了这个判据：

```
proxy .py mtime      : 2026-11-05 11:13:01
live process started : 2026-11-05 11:02:57   (PID 1844673)
repo HEAD            : abb129c (11-05 11:14)
进程实际加载的 commit: 846b3de
```

mtime 晚于进程启动 → 按旧规则「线上跑的是旧代码」→ **要 restart**。

**但实际 diff 只有 5 行，且全在 `_md_slug_candidates()` 的 docstring 里**：

```diff
     这里对两个 KB 都把「解码版」和「原样版」都作为候选，逐个试，
     谁先存在用谁 —— 这样即便某个 crawler 改了 slug 规则也不会全线崩。
+
+    ⚠️ 返回值是**不带 .md 后缀的裸 slug** —— 调用方必须自己拼后缀：
+        md_dir / f"{slug}.md"        # ← proxy 内部 read_full_content() 的写法
+    漏掉后缀会让自写审计脚本报「slug 契约 0/558 + 孤儿 = 全量」的假阳性
+    （陷阱 11，已复发 4 次；详见 shared-proxy-service-pitfalls.md §陷阱 11）。
     """
```

**行为完全等价** → 不该 restart。而如果按 mtime 规则 restart，就会打断
姊妹 KB 当时正在飞的探针（陷阱 1 / 陷阱 20）——**纯净伤害**。

### 脚本做的判据

按**内容**而不是按**时间**：

1. **推定线上进程加载的 commit** = 进程启动时间之前的最新 commit
2. diff 该 commit 的 `hermes-skill-proxy.py` 与 HEAD 的
3. **剥掉 docstring 后做 AST 指纹比对**（遍历所有 `FunctionDef`/`ClassDef`，
   去掉首个 docstring 表达式，再 `ast.dump`）
   - 指纹**相同** → 只差注释/文档 → **行为等价** → **不需要 restart**
   - 指纹**不同** → 行为真变了 → **需要 restart**（并提示先确认无 probe 在飞）

exit 0 = 不需要 restart；exit 1 = 需要；exit 2 = 判不出来。

### 为什么 AST 而不是简单的字符串 diff

字符串 diff 只能告诉你「有差异」，**不能告诉你「差异是否影响行为」**。
本次的差异是 5 行 docstring —— 纯字符串比较必然报「有差异」，
从而诱导一次不必要的 restart。**剥掉 docstring 的 AST 指纹**才回答了真正的问题：
「线上跑的行为和 HEAD 一样吗？」

### 与 `check_proxy_env.py` 的分工

| 脚本 | 查什么 | 判据 |
|---|---|---|
| `check_proxy_env.py --units` | **环境变量**（unit / process） | sha 摘要比对 |
| `check_proxy_staleness.py` | **代码** | AST 指纹比对 |

两个都要在「改了 unit 或 proxy 代码后」跑。

---

## 三、通用教训

**「mtime 晚于进程启动 = 线上陈旧」是一条太粗的尺子。**
它把「改了注释」和「改了行为」混为一谈，而在共享服务的语境下，
前者触发的一次 restart 会打断**另一个 agent 正在跑的验证**。

⇒ 判定「线上是否需要重启」时，**先问「行为变了吗」，而不是「文件变了吗」**。
能用 AST / 结构化判据回答的问题，就别用时间戳猜。

⇒ 同理，**「共享文件该 cp 还是该 merge」也不能靠「谁是权威」猜**，
必须**先 diff**；而 diff 之后如果结论是「两边都有独有内容」，
**别手工合并**——用一个可校验的脚本合并（并让脚本自己断言「没丢 section」）。

---

## 四、尚未入库的部分（留给下一轮 cron 收尾）

本轮 cron 的工作树在提交时是**干净**的（`f358822` + `783678a` 已 push），
但上述两个新脚本是**之后**才写入的 —— 因此下一轮 cron 开头必须：

```bash
cd ~/.hermes/skills/productivity/inexbot-open-knowledge-base
git status --short     # ← 会看到两个 ?? 未跟踪文件
```

→ **必须 `add` + `commit` + `push`**，否则下次 `git pull` 会静默回退，
这两个脚本就消失了（陷阱 14 第 4 次复发的风险点）。
**报告写「遗留：无」之前一定要核过 `git status`。**
