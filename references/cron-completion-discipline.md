# Cron 收尾纪律：报告写「遗留：无」之前必须 `git status` 核过

**2026-11-01 实测** —— 本 KB 的 10-31 那轮 cron 报告最后一节写着「## 遗留 **无**」，
但实际有 **3 处已完成的工作没提交**：

```
M SKILL.md                                ← 新增「标准验证序列」章节
M references/crawl-state-2026-10-31.md   ← 新增 §④ §⑤ 两节
M scripts/check_staleness.py              ← 修了 slugify 漏 `|`
?? scripts/check_index_hygiene.py         ← 10-29 三修的自动化守卫，压根没入库
```

10-31 那轮 agent 以为自己做完了（文档写了、报告发了），**但没 `git add` / `commit` / `push`**。

## 为什么这是真故障，不只是「忘了提交」

未提交 = **下次 `git pull` 会静默回退**。具体后果：

- `check_index_hygiene.py` 是 **10-29 三修**（零宽字符 / 空标题 / 幻影 token）的**唯一自动化守卫**。
  它没入库 → 下次有人 `git pull` 后这个文件消失 → **三修悄悄失去守卫**，
  而三修本身还在 `crawler.py` 里（`clean_text()`），所以**看起来一切正常**，
  直到有人手写探针才发现守卫不见了。
- SKILL.md 里的「标准验证序列」章节回退 → 下一个 agent 不知道该跑哪几步。

**这类失效是静默的**：代码还在、行为不变，只是**少了检测**。最难查。

## 判据：cron 结束前固定跑一次

```bash
cd ~/.hermes/skills/productivity/inexbot-open-knowledge-base
git status --short          # ← 报告写「遗留：无」之前必须看这个
git log --oneline -3         # 确认 remote 是否已跟上
```

**分类处理**：

| `git status` 输出 | 含义 | 动作 |
|---|---|---|
| 只有 ` M references/.index-snapshot.json` | **良性** —— `check_crawl_state.py` 每轮刷新它，而它被 git 跟踪 | 连同当轮文档一起 commit 即可 |
| 有 ` M` / `??` 的**代码或文档** | ⚠️ **真未提交工作** | 必须 `git add` + `commit` + `push` |
| 有 ` M` 的**姊妹 KB 仓库**文件 | 那是**它自己** cron 的职责 | 本 skill **不要替它提交**，只在报告里点名 |

> 📌 见 SKILL.md「`references/.index-snapshot.json` 是被跟踪文件 → 每轮 crawl 都会脏工作树」。

## 报告措辞纪律

- ❌ 不要写「遗留：无」除非**刚跑过 `git status` 且确认干净**
- ✅ 要写就写具体清单：哪些提交了（commit hash）、哪些**故意没提交**（及原因）
- ✅ 姊妹 KB 仓库的未提交改动 → 明确写「**非本 skill 职责，未代提交**」

## 通则：cron 的「完成」= 磁盘改完 **且** 已入库

这两个是不同的状态：

```
改文件 → git add → git commit → git push → 报告里给 commit hash
```

中间的任一步漏掉，**下一个 session 看到的就是「上轮说做完了但代码不在」**。
本 skill 里已有同族教训：「补丁『写了』≠ 补丁『上线了』」——
那条讲的是 **restart 服务**，这条讲的是 **git 提交**，两者是同一个模式的两个面：

> **凡是需要「下一轮生效」的东西（重启服务 / 提交代码），做完必须验证它真的生效了，
> 并把证据（PID / commit hash）写进报告。**
