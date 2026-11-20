# 2026-11-19 爬取快照 — 832 稳态（连续第 2 天持平）

## 一、结论摘要

| 项 | 值 |
|---|---|
| crawl verdict | **IDENTICAL**（与 11-18 逐字节相同） |
| index.json | **832 entries, 2,620,789 bytes**（与 11-18 11:04:56 完全一致） |
| locale 分布 | zh=476 / en=178 / kr=178（与 11-18 相同） |
| 抓取耗时 | 4:42（爬取段 3:15 + 索引段 2:10） |
| 网络抓取次数 | **0**（日志 `✓` 行数 = 0，`raw/` 最新 mtime = 11-18 11:03:13） |
| 判定 | **纯本地重抽取，零网络请求 → 上游零变更** |
| 姊妹 KB inexbot | 560（稳态） |

**832 是 11-18 打破 817 稳态后的新基线**，连续第 2 天持平。
docs 数自 11-18（832）起未再增长；自 10-10（799）→ 11-14（817）→ 11-18（832）后的增长期结束。

## 二、本轮与 11-18 的差异

- **唯一变化**：无。index.json 字节数完全相同（2,620,789 = 2,620,789）。
- `raw/` 最新 mtime = **2026-11-18 11:03:13**（早于本次爬取起点 11-19 11:00:50）
  → 本轮 832 页**全部命中缓存**，**一个页面都没重新抓**。
- md/ 今日新增 = 0 个文件（与 IDENTICAL 判定自洽）。
- 无 `.tmp` 残留（原子写 `save_json()` 正常工作）。

## 三、8 步标准验证序列（全绿）

| # | 检查 | 结果 | 关键数据 |
|---|---|---|---|
| 1 | `check_crawl_state.py` | ✅ exit 0 | IDENTICAL / 832 / 2,620,789 B |
| 2 | `check_index_hygiene.py` | ✅ exit 0 | 零宽 0、空标题 0、幻影 token 可达 0、旧 API 可达 0、空 snippet 34（上游空目录页） |
| 3 | `check_retrieval_chain.py` | ✅ exit 0 | **静默降级(==800) = 0**；短正文 4 条（61–71 B，伺服报警占位页，属上游本来就短） |
| 4 | `check_proxy_health.py` | ✅ exit 0 | open **832** / sister **560**，均 loaded=True |
| 5 | `check_e2e_request.py` | ✅ 见 §四 | **12/12 全 200**，0 次 500/502 |
| 6 | `check_proxy_env.py --units` | ✅ exit 0 | 5 个变量在「线上 environ / /etc 部署版 / repo 模板」三处 sha12 逐项一致；`HERMES_TIMEOUT` sha12=`e49ec846db75` = 1800 ✅ |
| 6b | `check_url_to_index_key.py` | 未跑（本轮无反查脚本新增） | — |
| 7 | `check_proxy_staleness.py` | ✅ exit 0 | 线上 PID 1954151 源码 == HEAD `abb129c` → **NOT stale，无需 restart** |
| 8 | `check_reload_timer.py` | ✅ exit 0 | 重载链存活，定时器线程 tid=2001822（11-19 06:18:47 起，第 5 次 5h 排期），**下次重载 11:18:47**；内存 832 == 磁盘 832 → 已同步 |

**附加守卫**：
- `check_md_reachability.py` ✅ → open **832/832** 可达、sister **560/560** 可达，unresolved = 0
- `check_token_consistency.py` ✅ → 两个 KB 各 **0 处** token 级不一致（PASS）
- `check_shared_pitfalls_structure.py` ✅ → 两份共享文件结构完好（40 / 38 sections）
- `diff_shared_pitfalls.py` → 姊妹 **0 独有行**，本 skill **独有陷阱 39 + 40**（姊妹未回写）→ **本 skill 是严格超集，本轮无需同步**

## 四、e2e 探针

- 日志：**`/tmp/e2e-open-2026-11-19.log`**（带 KB 名后缀，遵守陷阱 40）
- 姊妹 KB 用 `/tmp/e2e-2026-11-19.log` → **两边文件不同，无互相覆盖** ✅
- 结果：**12/12 全 200**，耗时 57.3–355.0s，**0 次 502 / 500 / 000**
  - 最长一次 355.0s（`示教器 操作手册 功能说明`）—— 仍远低于 proxy 上游 1800s / 客户端 1860s
- 连续第 **14 天** 502 计数为 0

## 五、journal 切片（按当前进程启动时间）

proxy PID 1954151，since = 2026-11-14 11:17:36，共 **1,445 行**：

| 计数 | 值 |
|---|---|
| Unknown key | **0** |
| HTTP 500 | **0** |
| HTTP 502 | **0** |
| RELOAD FAILED | **0** |
| Traceback | **0** |
| HTTP 200 | 131 |
| HTTP 404 | 46（**全是外部漏洞扫描器**：Trinity.txt.bak / nacos / phpMyAdmin / weboffice / cwbase / server-info 等，22 个 distinct path，**0 条 KB 流量**） |

全量历史（328,846 行）：500 = 606、502 = 28 —— 均为几十次进程重启前的老账，不计入本轮。

## 六、收尾处置

1. **上一轮（11-18）被 HTTP 429 打断 → 其报告正文的「已提交」结论一律作废**（陷阱 14 / §🔴 2026-11-12）。
   独立核对 `git status`：本地领先 origin/main **2 个 commit**（`b222c3b`、`34aa7f5`）。
2. **已 push 成功**：`b222c3b..34aa7f5  main -> main`（HTTPS + HTTP/1.1 + low-speed 保护，11:00 窗口一次成功）。
   → 工作树与 origin/main 同步，`## main...origin/main`（无 ahead/behind）。
3. **本轮新增文档**：`references/crawl-state-2026-11-19.md`（本文件）+ SKILL.md 最新快照指针更新。
4. **未提交 = 下次 `git pull` 静默回退** → 本轮文档在写报告前 commit + push。

## 七、值得记录的观察

- **SKILL.md 体积**：79,088 字符 / 124,821 字节（2026-11-18 瘦身后从 105,723 降下来）
  → 距 `skill_manage patch` 的 **100,000 字符上限**尚有 **20,912 字符余量**。
  ⚠️ 判活命令用 `python3 -c` 会被 policy 拦 → 用 `wc -c`（字节）或
  `execute_code` 读文件数字符（**字符 ≠ 字节**，中文占 3 字节）。
- **共享文件分叉方向稳定**：本 skill 连续第 2 天是严格超集（陷阱 39/40 尚未被姊妹回写），
  「姊妹独有行 = 0」→ **不 cp、不 merge**，保持现状即可。
- **`check_token_consistency.py` 必须用 `/usr/bin/python3`**：沙盒 `python3` 无 flask → `ModuleNotFoundError`。
  首次误用时 exit 1，改用 `/usr/bin/python3` 后 PASS。**这是脚本环境问题，不是索引不一致。**
