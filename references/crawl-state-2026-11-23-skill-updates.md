# 本轮（2026-11-23）的 skill 库更新记录

> 供下一轮 agent 追溯「SKILL.md / references 里那些条目是哪来的、依据是什么」。

## 本轮更新了哪些地方

| 文件 | 更新内容 | 触发场景 |
|---|---|---|
| `SKILL.md` | §陷阱 44 增补「本库连续两轮复现 ⇒ 固化成轮次第 0 步硬动作」 | 11-22 那轮 `Last run=ok` 但实测 2 处未入库 |
| `SKILL.md` | URL 形态章节增补「移植姊妹脚本后必须当场跑一次」（§陷阱 46 补充）+「共享脚本同步方向不能用『姊妹独有行 = 0』」 | 照搬姊妹的 `check_url_forms.py`（那份带 bug） |
| `SKILL.md` | 新增「第 6d 步」`check_url_forms.py` 用法段 | 本轮移植并实测通过 |
| `SKILL.md` | version → 1.38.0，`last_verified` → 2026-11-23 | — |
| `references/cron-completion-discipline.md` | 新增「轮次第 0 步：无条件核验上一轮的入库状态」整节 | §陷阱 44 连续两轮复现 |
| `references/shared-proxy-service-pitfalls.md` | §陷阱 44 增补「第 0 步三条命令 + 逐个核验新增物」 | 同上 |
| `references/shared-proxy-service-pitfalls.md` | §陷阱 46 增补「从姊妹 KB 移植脚本时，bug 可能就在你复制的那一份里」 | 姊妹那份 `check_url_forms.py` 带 unpack bug |

## 为什么这些值得写进 skill

### 1. §陷阱 44 的「本库复现」把它从「姊妹的经验」变成「本库的硬约束」

11-21（5 处未入库）、11-22（2 处未入库）**连续两轮**，且两轮 `Last run` 都是 `ok`。
⇒ 这不是偶发失误，是**流程缺陷** ⇒ 唯一有效的对策是**把核验动作固化成「第 0 步无条件执行」**，
而不是「看情况查」。

### 2. 「从姊妹移植脚本」是一个新的失败入口（§陷阱 46 的姊妹篇）

原 §陷阱 46 讲「**自己**固化的脚本没真跑过一次」。
本轮遇到的是**反方向**：**照搬姊妹的成品，而那份恰恰是带 bug 的**。
⇒ 姊妹的成品看起来比自己的更可信（来自另一个库、还有 sha1），
**实际上更危险** —— 因为「来自姊妹」会让人跳过验证。

⇒ 移植三步：**① 移植后立刻跑，看末尾判定行 ② 比对 sha1 与姊妹当前版本 ③ 判是否 KB 无关可移植**。

## ⚠️ 收尾纪律提醒（下一轮注意）

本轮这两处 SKILL.md / references 的改动**是在 cron 轮次结束后补做的**。
⇒ 下一轮开跑时**必须**先跑 `git status -sb`（第 0 步）——
如果这些改动还没入库，本轮就又犯了 §陷阱 44 自己警告的那个错。

**核验命令**：

```bash
cd ~/.hermes/skills/productivity/inexbot-open-knowledge-base
git status -sb
git log --oneline -3
git ls-files --others --exclude-standard
```

**入库清单（逐个核验，见 §陷阱 44）**：

- `SKILL.md`（§陷阱 44 增补 + 第 6d 步 + §陷阱 46 补充）
- `references/cron-completion-discipline.md`（第 0 步整节）
- `references/shared-proxy-service-pitfalls.md`（§陷阱 44 + §陷阱 46 增补）
- `references/crawl-state-2026-11-23-skill-updates.md`（本文件）
