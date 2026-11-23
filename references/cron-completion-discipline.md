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

## 🩸 「半截行」编辑事故：`git diff` 里只有 `-` 没有 `+` → 段落被截断（2026-11-13 实测）

**这是陷阱 14 的姊妹坑**：陷阱 14 说「工作没提交」，这条说「**提交了，但提交的是一份坏文档**」——
后者更隐蔽，因为它**能通过 `git status` 干净、`git push` 成功、报告写「遗留：无」**，
而 SKILL.md 里的某个段落已经**语法断裂、语义不完整**。

### 现场（2026-11-13 继承 11-12 的遗留）

11-12 那轮用 `patch` 改 SKILL.md 的「最新一轮爬取快照」段落时，
把一个**两行**的段落只删掉了**第一行**：

```diff
 **最新一轮爬取快照**见 `references/crawl-state-2026-11-12.md`
-（**799/560 连续第二十三次持平（本 KB 纯稳态）**：index.json **2,450,869 bytes 与 10-29→11-11 逐字节相同**、
 verdict=IDENTICAL、零网络请求（0 次 `✓`、raw/ 最新仍是 10-23）、**3:41.4** 落在稳态带内、
```

结果：
- 第 708 行只剩 `verdict=IDENTICAL、…` —— **括号不闭合**（`（` 开了没 `）` 收）
- 句子从「（**799/560 连续第二十三次持平…**：index.json …」**直接跳到**「verdict=IDENTICAL…」，
  读起来是断裂的
- **但 `git diff --stat` 只会告诉你「SKILL.md | 1 -」** —— 看着像「精简了一行」，
  没人会立刻看出这是**事故**

### 判据（diff 形状）

| diff 形状 | 判读 |
|---|---|
| `-` 行与 `+` 行**一一对应** | 正常替换 ✅ |
| `-` 行**有**对应 `+`（内容不同） | 正常修改 ✅ |
| **只有 `-`、没有 `+`**，且 `-` 的是段落**前半截** | 🔴 **编辑事故**（不是「精简内容」） |
| 只有 `-`、没有 `+`，且 `-` 的是**独立完整**的一行 | 有可能真是「精简」—— 但要**读上下文确认** |

### 通则

1. **改长段落前先 `read_file` 看完整上下文**（尤其带 `offset`/`limit` 的分段读会漏行）。
   2026-11-13 那次 `read_file` 只读了 703–718 行，正好**没看到**第 719 行是段落的另一半
   → 才让事故溜进来。
2. **改完立刻 `git diff` 复核**，重点看「**有没有孤立的 `-` 行**」。
3. **发现 `-` 删的是段落前半截 → 用完整段落替换整块**，而不是补一行了事。
4. 收尾时若 SKILL.md 有 `M`，**`git diff` 必须亲自看一遍**，不能只看 `--stat`。

### 与陷阱 14 的关系

| | 陷阱 14 | 本条（半截行） |
|---|---|---|
| 症状 | 工作没入库 | 工作入库了，但**内容是坏的** |
| `git status` | 脏 | **可能干净**（已 commit） |
| 发现手段 | `git status` | **`git diff` 的形状** |
| 危害 | 守卫丢失（静默失效） | 文档不可读 / 下一个 agent 误读（静默误导） |

⇒ **两者都要防**：收尾时**既**要 `git status` 核过（陷阱 14），
**又**要 `git diff` 复核每个改动块的形状（本条）。

## ⭐ 同步**共享脚本**到姊妹 KB：不要只用「姊妹独有行 = 0」判定（2026-11-23 实测）

> ⚠️ **本条补充共享 pitfalls §陷阱 23 的判据。** §陷阱 23 说「姊妹独有行 = 0 ⇒ 可以直接 cp 覆盖」——
> 那条对**共享文档**（`shared-proxy-service-pitfalls.md`）成立，
> 但对**共享脚本**（两个 KB 各有一份同名 `scripts/*.py`）**会误判**。

#### 现场（2026-11-23，修 `check_url_forms.py`）

我方改了 `scripts/check_url_forms.py`（修一个 unpack bug），需要同步到姊妹 KB 的同名副本。
按 §陷阱 23 跑集合差集：

```
sister-only (would be lost by cp): 7
ours-only   (bug fix to propagate): 7
```

⇒ **sister-only = 7 ≠ 0** ⇒ 按 §陷阱 23 的字面判据，**不能 cp 覆盖**。

**但那 7 行「姊妹独有行」恰恰就是需要被替换掉的 buggy 行本身**
（`picked = rnd.sample(...)` / `chosen = {k: v for k, v in picked}` / `for k, v in picked:` …）
⇒ **姊妹没有「独有内容」，只是内容不同。**

#### ✅ 正确判据：「变化行是否全部与本次改动相关」

```python
import difflib
hunks = [l for l in difflib.unified_diff(sister.splitlines(), ours.splitlines(), lineterm="", n=0)
         if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
related_tokens = ("picked", "chosen", "by_key", "picked_keys")   # 本次改动涉及的标识符
unrelated = [l for l in hunks if not any(t in l for t in related_tokens)]
if not unrelated:
    sister_path.write_text(ours)     # 安全：全部差异都跟本次改动有关
```

| 判据 | 含义 | 动作 |
|---|---|---|
| `sister-only == 0` | 姊妹是**子集** | ✅ 直接 cp（§陷阱 23） |
| 变化行**全部**与本次改动相关 | 姊妹只是**内容不同**，没有独有内容 | ✅ 可以覆盖 |
| 存在**无关**的变化行 | 姊妹有**真正的独有内容** | ⚠️ 不能覆盖 → 手动合并 |

#### 💡 通则

> **「姊妹独有行 = 0」是「共享文档」的安全判据，不是「共享脚本」的。**
> 脚本在被同步时**本来就会两边不同**（我方在修 bug，姊妹还是旧版）。
> ⇒ 对**脚本**要用「**变化行是否全部相关**」判定；对**文档**才用「姊妹独有行 = 0」。
>
> ⚠️ **别把两者混用**：对脚本套 §陷阱 23 会得到「不能覆盖」的错误结论，
> 于是 bug 修复**只留在一个 KB**，另一个 KB 继续跑着同一个坏脚本 ——
> **而两边跑的是同一个 proxy**，等于没修。

#### 同步后必须做 sha1 双向核对

```bash
sha1sum <our>/scripts/check_url_forms.py <sister>/scripts/check_url_forms.py
# 两个 sha1 必须完全相同
```

2026-11-23 实测：同步后两侧 sha1 均为 `5041d0e938873a57d572fd4564ab66ca3e6ccfdb` ✅

## ⭐ 新脚本入库前必须**真跑一次**（2026-11-23 实测，补充陷阱 46）

**判据不是「脚本在仓库里」，而是「脚本的**末尾判定行**出现了」。**

```bash
/usr/bin/python3 scripts/check_url_forms.py | tail -5
# ✅ 期望：末尾出现 "VERDICT: ..." 且退出码 0
# ❌ 若只看到头部统计行（url_suffix 分布 / 池子大小）而末尾没有 VERDICT
#    ⇒ 脚本中途崩了（异常被顶层 except 吞掉，仍 exit 1）
```

⚠️ **头部输出正常不能证明跑通** —— 一个在 60% 处崩溃的探针会先打印一屏漂亮的统计行。
⇒ **验收新脚本时，永远 `tail` 一下末尾的汇总/判定行。**

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
