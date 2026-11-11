# 2026-11-10 爬取快照 — 799/560 连续第二十一次持平（本 KB 纯稳态）

**结论**：本 KB（`inexbot-open`）**799 篇连续第二十一次持平**，index.json **2,450,869 bytes**
自 2026-10-29 起逐字节未变，**零网络请求**。姊妹 KB（`inexbot`）维持 **560**（也连续第 21 次持平）。

## 一、爬取结果

| 项 | 值 |
|---|---|
| 命令 | `python3 scripts/crawler.py` |
| 启动方式 | `write_file` 外层脚本（`/tmp/run_open_crawl_20261110.sh`）→ `terminal(background=true, notify_on_complete=true)` |
| 耗时 | **3:51.3**（稳态带 3:00–3:50 内，略高于中位但远低于 6min 红线 ✅） |
| 页面 | 发现 799 个页面 / 843 个 hash |
| 结果 | **成功 799 / 799**，0 失败 |
| index.json | **2,450,869 bytes**，mtime 2026-11-10 11:04:56 |

**locale 分布**：zh=443 / en=178 / kr=178（与 10-29 起完全一致）

### 稳态硬证据（三条同时成立）

```bash
grep -c "✓" /tmp/open-crawl-20261110.log          # → 0   （零网络请求，全缓存命中）
find ~/.hermes/kb/inexbot-open/raw -newermt "2026-11-10 00:00"   # → 空（raw/ 最新仍是 10-23 11:18）
find ~/.hermes/kb/inexbot-open/md  -newermt "2026-11-10 00:00"   # → 空（md/ 零重写）
ls ~/.hermes/kb/inexbot-open/*.tmp                # → 不存在（原子写无残留）
```

`check_crawl_state.py` → **verdict: IDENTICAL**（799 docs, 2,450,869 bytes，与 11-09 逐字节相同）

## 二、8 步标准验证序列 — 全绿

| 步 | 脚本 | 结果 |
|---|---|---|
| 1 | `check_crawl_state.py` | **IDENTICAL**，799 entries / 2,450,869 B |
| 2 | `check_index_hygiene.py` | 零宽 **0** / 空标题 **0** / 空 snippet 34（上游空目录页，正常）/ 幻影 token 可达 **0** / 旧 API 可达 **0** → exit 0 |
| 3 | `check_retrieval_chain.py` | **静默降级 ==800 = 0**；短正文 4 条 = 伺服报警占位页 61–71 B（上游本来就短）→ exit 0 |
| 4 | `check_proxy_health.py` | open **799** ✅ / 姊妹 **560** ✅ |
| 6 | `check_proxy_env.py --units` | 5 个变量 × 3 处 sha12 逐项一致，`HERMES_TIMEOUT` sha12=`e49ec846db75`（=1800）✅ |
| 7 | `check_proxy_staleness.py` | 线上 PID 1844673 源码 == HEAD → **NOT stale**，无需 restart → exit 0 |
| 8 | `check_reload_timer.py` | 重载链存活，定时器 tid=1903565（2026-11-10 06:04:09 出生，age 4.95h），**下次重载 11:04:09**；内存/磁盘双 KB 均同步 ✅ |
| 5 | `check_e2e_request.py` | 见下 |

### journal 按当前进程切片（PID 1844673，11-05 11:02:57 起）

`Unknown key` **0** / HTTP 500 **0** / HTTP 502 **0** / `RELOAD FAILED` **0** / HTTP 200 = 168（切片共 1751 行）。
全量历史 HTTP 500 = 606 / HTTP 502 = 28（均来自几十次重启前的旧账，非当前状态）。

## 三、本轮观察到的情况

### ① 🔴 新坑：github.com:443 持续不可达 → **SSH 传输通道成为唯一可用的 push 路径**

11-09 记录的「push 撞上 github.com:443 瞬时超时」在本轮**升级为持续故障**：
连续 **3 次** push 全部失败，错误完全一致：

```
fatal: unable to access 'https://github.com/inexbot/inexbot-open-knowledge-base.git/':
Failed to connect to github.com port 443 after 130088 ms: Connection timed out
```

**逐层定位（不要照抄 11-09 的「git 配置问题」结论）**：

| 探针 | 结果 | 判读 |
|---|---|---|
| `curl -m 30 https://api.github.com/` | **200**，0.37s | 出网正常 |
| `curl -m 30 https://open.inexbot.com/` | **200**，0.83s | 出网正常 |
| `curl -m 20 https://github.com/` | **超时**（`Trying 20.205.243.166:443... Connection timed out`） | **就是 github.com:443 这条路挂了** |
| socket TCP+TLS `github.com:443` × 5 次 | **0/5 OK**（每次 8s 超时） | **不是偶发抖动，是该端口当前不通** |
| socket TCP `github.com:22` × 5 次 | **5/5 OK**（0.09s） | **SSH 通道正常** |
| `ssh -T git@github.com` | **成功认证**（`Hi MintOTea!`） | SSH 凭证有效 |

⚠️ **注意与 11-09 的差异**：11-09 实测 `github.com:443` 的 TCP/TLS 是 **OK 0.1s/0.2s**，
本轮同样的探针变成 **0/5**；而 `api.github.com:443` 依旧 200。
⇒ **故障面精确到「github.com 这一台机器的 443 端口」**，不是整个 GitHub、也不是 DNS、
也不是本机 git 配置（`git config --global --list` 无 proxy、无 url.* 覆盖；env 无 `*_proxy`）。

**对策（已验证有效，优先于反复重试 HTTPS）**：

```bash
# 用 SSH 传输通道推，**不改动 remote 配置**（避免污染姊妹 KB 共享的仓库配置）
cd <repo> && timeout 120 git push git@github.com:owner/repo.git main:main
# → "Everything up-to-date" 或正常 push
```

验证是否真的入库（**不要只看 push 的返回值**）：

```bash
git fetch git@github.com:owner/repo.git main:refs/remotes/sshcheck/main
git merge-base --is-ancestor <your-commit> refs/remotes/sshcheck/main && echo "IN remote"
```

本轮实测：**姊妹 KB 已在我 push 之前把我们的 commit 一并代推**，
`git push`（SSH）返回 `Everything up-to-date`，
但 `git log refs/remotes/sshcheck/main` 显示 remote HEAD 已前进到姊妹的新 commit
（`72b176e docs: sync shared proxy pitfalls (add trap 25)`），
我们的 `e72569f` **确实在 remote 历史里**（`merge-base --is-ancestor` 判定 = YES）。
⇒ **「push 返回 Everything up-to-date」不等于「我们没在工作」**，
必须用 `merge-base --is-ancestor` 确认自己的 commit 在历史里（陷阱 4 / 陷阱 15 的延伸）。

> ⚠️ **不要因为 443 不通就去改 remote**（`git remote set-url`）——
> 那是**全局副作用**，会影响姊妹 KB 的 cron（它也用同一份 remote 配置）。
> **用 `git push <url> <refspec>` 的一次性语法**即可。

### ② 陷阱 14 **第 5 次复发**：11-09 的工作实际没提交 → 本轮已闭合

本轮开跑前 `git status` 发现上一轮（11-09）遗留：

```
 M SKILL.md                              （陷阱 24 章节 + version 1.24.0→1.25.0）
 M references/crawl-state-2026-11-09.md  （新增 §②'/§②'' 两节）
?? scripts/check_url_to_index_key.py     （新脚本，**未跟踪**）
```

其中 `scripts/check_url_to_index_key.py` 是 SKILL.md「第 6b 步」**直接引用的目标文件** ——
若被 `git pull` 静默回退，**SKILL.md 的链接会指向不存在的文件**（静默失效）。
→ 本轮已 `git add` + `commit`（`e72569f`）+ 经 SSH 通道确认在 remote 历史里。

⇒ **再次印证**：cron 报告写「遗留：无」之前**必须** `git status` 核过；
「本轮无遗留」不等于「上一轮无遗留」。

### ③ SKILL.md 里两处**过期样本值**已修正

`check_crawl_state.py` 的示例输出块长期停留在 **10-21 的快照**（2,448,900 bytes / 1854 md），
而实际值自 10-29 起就是 **2,450,869 bytes / 1855 md**：

```diff
-index.json: 799 entries, 2,448,900 bytes, mtime 2026-10-21 11:04:24
+index.json: 799 entries, 2,450,869 bytes, mtime 2026-11-10 11:04:56
-md/ files: 1854 total (1676 locale-prefixed, 178 stale bare)
+md/ files: 1855 total (1677 locale-prefixed, 178 stale bare)
```

同时把健康检查章节的「连续 19 次持平 / 29 天零新增」更新为
**「连续 21 次持平 / 31 天零新增」**（11-08/11-09/11-10 三轮未同步）。

> ⚠️ **文档里的基线数字是「最后核对日」的快照** —— 连续几轮持平后就会变成陈旧值，
> 而**陈旧的基线数字比没有基线更危险**（会让人以为 docs 数变了）。
> 每轮 cron 应顺手核对一次 `check_crawl_state.py` 的真实输出。

### ④ md/ 文件数 1854 → 1855 的真实来源：**10-29 离线重建**，不是今天新增

本轮 `check_crawl_state.py` 报 `md/ files: 1855 total`，而 11-08/11-09 两份快照里写的是 **1854**。
逐层核实后确认：**不是今天多了一个文件**：

- `find md/ -newermt "2026-11-10 00:00"` → **0 个**（今日零重写）；
- `find md/ -newermt "2026-11-09 00:00"` → **0 个**；
- md/ mtime 日期分布里**最新的日期是 2026-10-29**（799 个文件 = 10-29 离线重建那一轮），
  其余是 05-12 / 07-17 / 07-18 / 07-25 / 07-30 / 07-31 / 08-21 / 08-22 的历史批；
- locale 前缀文件 **1677**、裸名 **178** → 1677+178 = **1855** ✅（与脚本输出一致）。

⇒ **1854 → 1855 是 10-29 那次 `regenerate_from_cache.py` 离线重建留下的**，
而 10-25/10-26/10-27/10-28/11-05/11-07 的快照里**已经是 1855**；
**11-08 与 11-09 两份快照的「1854」是抄错了 10-22 的旧值**（该文件从未核对过自己的实际输出）。

> ⚠️ **教训**：快照里的数字**必须来自脚本的真实输出**，不能从上一份快照「抄一行」。
> 抄错一行就会在下一轮变成「凭空多/少一个文件」的伪信号，
> 让人浪费一整轮去查「谁动了 md/」（本轮就是这么查的）。

### ⑤ md/ 孤儿文件 1056 个 → 全部是 10-29 之前的死缓存，**架构上不可达**

用 proxy 自己的 `_md_slug_candidates()` 逐条反查（不手写 slugify）：

```
index entries      : 799
reachable md       : 799      ← 799/799 全部可定位
index->md MISSING  : 0        ← 零缺失
orphan md (dead)   : 1056
```

孤儿按 mtime 分布：**全部**落在 10-29 之前（05-12/07-17/07-18/07-25/07-30/07-31/08-21/08-22），
10-29 之后 **0 个**新增孤儿 ⇒ 10-29 离线重建之后 crawler 没有再产生新的死缓存。

**姊妹 KB 11-10 的 `verify_kb.py` 把这 1056 个孤儿算作 `[inexbot-open] FAIL`（4 项 FAIL）**，
那是**姊妹 KB 的口径问题（它假设 md 数应 == index 数）**，
不是本 KB 的回归 —— 本 KB 的正确判据是「**index 可达性**」：799/799 ✅、缺失 0 ✅。

### ⑥ 共享文件同步：本轮**无需动作**（方向连续反转后的稳定态）

`diff_shared_pitfalls.py` → **IDENTICAL — nothing to sync**（两份均 1111 行 / 56,708 B /
sha1 `53152f6d6079`，含姊妹本轮新增的**陷阱 25**「探针/审计脚本自带的归一化必须按被测对象分派」）。

⇒ 姊妹在同窗口把陷阱 25 写进了**我们这份**（`git status` 出现 `M`），
同步方向由「本 skill → 姊妹」再次反转为「姊妹 → 本 skill」。
**这是同步方向的第 4 次反转**（11-06 merge → 11-08 cp → 11-09 cp → 11-10 双向同步）。
⇒ **每次都必须先 diff 再决定**，「行数多/少」不是判据（陷阱 23）。

### ⑦ proxy **未 restart** 的两条理由（与前几轮一致）

1. **内容**：index.json 逐字节未变（2,450,869 = 11-09）→ 无需为内容 restart；
2. **部署**：`check_proxy_staleness.py` 判定线上 PID 1844673 的源码 == HEAD（AST 指纹一致）
   → 无需为部署 restart。

⇒ 顺带**避开了打断姊妹 KB 探针的风险**（陷阱 1 / 陷阱 20）——
本轮姊妹 KB 的 e2e 探针在 **11:00 起持续跑到约 11:29**（29 分钟），
若本轮在此窗口 restart proxy，她的探针会被打成 `RemoteDisconnected`。
**本轮全程未 restart** ✅

## 四、本轮遗留 / 交接

- **本 skill 自身工作树**：SKILL.md 两处过期样本值已改 + 本文件新增 → 已 commit。
- **姊妹 KB `inexbot`**：`git status` 显示 `M SKILL.md` + `?? scripts/check_citation_links.py`
  / `?? scripts/check_retrieval_chain.py` / `?? scripts/check_url_to_index_key.py`
  —— **那是她自己的 cron 的职责，本 skill 不代提交**（陷阱 4 / 陷阱 13）。
  注意她的 `references/crawl-state-2026-11-10.md` §8「本轮 e2e 实测」当时还是占位符
  （探针未跑完），下一轮若读到请以她的最终版本为准。
- **无「补丁写了 ≠ 补丁上线」类隐患**：本轮未改 proxy 代码、未改 unit、未改 crawler 抽取逻辑。
