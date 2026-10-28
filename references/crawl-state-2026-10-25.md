# Crawl state — 2026-10-25（799/558，连续第六次持平，字节级一致）

## 结果摘要

| 项目 | 值 |
|---|---|
| inexbot-open docs | **799**（连续第 6 次持平：10-18 / 10-19 / 10-21 / 10-22 / 10-23* / 10-25） |
| index.json 字节 | **2,453,054 bytes**（与 10-23、10-24 **逐字节相同**） |
| locale 拆分 | en=178, kr=178, zh=443（三 locale 全非零） |
| md/ 文件 | 1855 total（1677 locale-prefixed + 178 stale bare） |
| inexbot（姊妹 KB） | **558**（持平；姊妹 crawler 11:00 同窗口并发，11:03 完成） |
| crawler 耗时 | **3:09**（有姊妹 KB 并发，仍落在 3:00–3:20 稳态带内） |
| 抓取成功 | **799 / 799**，失败 0（发现 799 页，843 hash） |
| check_crawl_state verdict | **IDENTICAL**（与 10-24 字节级一致，真稳态） |
| proxy | **未 restart**（`ActiveEnterTimestamp` = Sat 2026-10-24 11:21:42 CST） |
| 检索链路 | `check_retrieval_chain.py` → 静默降级 0，异常 False，exit 0 |

\* 10-23 那次 docs 数持平但字节 +4,154（非零变化，上游 API 改名），见
`crawl-state-2026-10-23.md`。所以「持平且字节相同」的纯稳态 cycle 是 10-18/19/21/22 + 10-25，
中间夹着 10-23/24 两次**内容变更**（10-24 是 proxy 侧修复，当天又爬到同一份改名后内容）。

**净结论：自 2026-10-23 上游 API 改名那次内容变更后，index.json 已连续 3 天逐字节未变
（10-23 / 10-24 / 10-25），2,453,054 bytes 确立为当前基线字节数。**

## 关键验证：10-23 的「改名盲区」修复确实生效（本次重点复查项）

10-23 那次上游把 API `star_servo_point_position_motion_control()` 改名为
`servo_point_position_motion_control()`，因增量爬虫只认 URL 变化，en/kr 缓存没失效，
导致三语种自相矛盾。当天做了精准失效 5 条 index 条目 / 10 个缓存文件。

本次（10-25）复查，用 proxy 自己的 `_md_slug_candidates()` 判定
「**index 可达**」的 md 是否仍含已删除的旧 API 名：

```
=== index-reachable md files still containing 'star_servo_point_position_motion_control': 0 ===
=== index entries whose TITLE mentions old API: 0 ===
=== new API name present in index-reachable md, by locale ===
  {'zh': 4, 'en': 3, 'kr': 3}
```

**结论：0 个 index 可达页面还暴露已删除的 API；新 API 名三个 locale 都在。修复保持有效。**

### 新发现：`md/` 里那 13 个含 `star_servo` 的文件是**不可达的死缓存**，不是污染

`grep` 全文扫 `md/` 会命中 13 个文件含 `star_servo`，看起来像「修复没做干净」，
但逐个核对 slug 是否在 index 里后发现**全部不在 index**：

```
star_servo md files NOT reachable from index: 13
  06.上位机-01.C++-03.接口示例-02.进阶应用-02.使用 star_servo_....md   ← 裸名（无 locale 前缀）
  en-04.Host-Computer-01.C++-03.API-Examples-02.Advanced.md
  en-06.Host-Computer-01.C++-03.API-Examples-02.Advanced-02.Servo-Control-Motion.md
  en-06.Host-Computer-01.C++-03.API-Examples-02.Advanced.md
  kr-04... / kr-06...（同上）
  zh-04...（3 个，含 03.示例 与 02.接口示例 两套并存）
  zh-06...（2 个）
```

**成因**：上游把目录 `06.上位机` 改成了 `04.上位机`（不只是 API 名，连 URL 前缀都变了）。
当前 index 里的 live 路径是 `/zh/04.上位机/...`、`/en/04.Host-Computer/...`、
`/kr/04.호스트-컴퓨터/...`；`06.*` 是改名前的旧 URL 结构，`04.*` 里的 `03.示例` 与
`02.接口示例` 是上游长期共存的**两个并存的侧栏分组**（不是新旧关系）。

**处置：不需要任何动作。** 这些是增量爬虫留下的死缓存，proxy 检索不到
（`read_full_content()` 只按 index path 定位 md），`check_retrieval_chain.py` 也证实
无异常。留着无副作用。

> ⚠️ **给未来的自己**：判定「改名修复是否失效」时，**必须区分
> 「index 可达」和「md 目录里存在」**。直接 `grep md/` 会得到假阳性
> —— 死缓存永远存在，只有 index 可达的文件才影响用户回答。
> 正确探针见 `scripts/` 外的临时脚本思路：用 `_md_slug_candidates()` 逐条 index path 反查。

## 4 个「短正文」条目复查：上游本来就是占位页，非读取失败

`check_retrieval_chain.py` 报 4 条 `< 200`：

| 标题 | md 实际大小 | 所属 KB |
|---|---|---|
| 0x0008 - IPM过温报警 | 112 B | inexbot（姊妹） |
| 0x000B - IPM模块故障 | 109 B | inexbot（姊妹） |
| 0x0050 - 风扇故障报警（未实现） | 157 B | inexbot（姊妹） |
| 0x0051 - IPM故障（过流或过温） | 139 B | inexbot（姊妹） |

用 proxy 的 `_md_slug_candidates()` 反查（姊妹 KB 的 index path 是 **URL-encoded**，
直接用 `slugify()` 拼路径会得到 `-1` 的假阴性，必须走 proxy 自己的候选逻辑），
4 条都能定位到真实 md 文件，且文件本身就是 109–157 B —— **上游占位页，无正文可读**，
不是 slug 契约断裂。

> ⚠️ 排查短正文时，先用 `_md_slug_candidates()` 定位，再看 md 实际字节数，
> 别用自己写的 `slugify()` 拼路径 —— 姊妹 KB 的 path 带 `%E4%B8%AD` 之类百分号编码，
> 编码不匹配会让「文件不存在」看起来像「正文为空」。

## proxy 状态：不需要 restart

- 爬前 `check_proxy_health.py` → 已显示 `inexbot-open docs=799 loaded=True`、
  `inexbot docs=558 loaded=True`（**爬前即新值**）。
- 爬后 `/health` 仍为 `{"inexbot":{"docs":558},"inexbot-open":{"docs":799}}`。
- `systemctl show -p ActiveEnterTimestamp` → `Sat 2026-10-24 11:21:42 CST`，
  早于本次爬取（11:01–11:04），说明 5h 自动重载窗口内已自行吃下新索引。
- 按 SKILL.md 判据 1「爬前已是新值 → 爬后必然也是，**不需要 restart**」。
  **本次未做无谓 restart**，避免引入 systemd 启动窗口竞态。

另外确认 10-24 的 slug 契约修复仍在运行实例里：
`_md_slug_candidates` 在第 190 行、`import hashlib` 第 25 行、`unquote` 第 29 行，
文件 mtime 10-24 11:10:37 < 服务启动 10-24 11:21:42 → 运行中的进程加载的就是修复后代码。

## 本 cycle 无新坑

全部按 SKILL.md 既定流程走完，未踩新坑：

1. **policy 拦 wrapper shell** → 照 2026-10-18 起的标准姿势，`write_file` 写
   `/tmp/run_open_crawl_20261025.sh` 再 `terminal(background=true)` 调脚本文件。
2. **并发抢 CPU 不严重** → 姊妹 KB crawler 11:00 同时在跑（pid 1725377），
   本 KB 仍 **3:09** 完成，落在 3:00–3:20 稳态带内，印证「并发影响仅 5–10%，
   不必错开两个 KB 的调度」。
3. **`process(log)` 对重定向输出的后台任务返回空** → 直接 `tail -25 /tmp/open-crawl-20261025.log`。
4. **inline `os.kill` 等待** → `execute_code` 沙盒内循环 `os.kill(pid, 0)` + `time.sleep(15)`，
   3:05 捕获到退出，零 `process(poll)` 浪费。
5. **同名脚本互相覆盖** → 本次用带日期后缀的 `/tmp/run_open_crawl_20261025.sh`，
   与姊妹 KB 的脚本名不冲突，无 sibling-subagent 覆盖警告。

## 上游仓库状态

- `inexbot-open-knowledge-base`：HEAD = origin/main = `2d7b8d7`（fix: convert relative
  image URLs to absolute in crawler），无本地改动，**无需 pull**。
- `hermes-skill-proxy`：HEAD = origin/main = `c7c8fab`，但工作区有
  **未提交改动**（`hermes-skill-proxy.py` +67/-7）—— 即 10-24 的 slug 契约修复。
  **不要 `git checkout`/reset 掉它**，那是尚未推 upstream 的本地修复，且运行实例正在使用。
  姊妹 KB 的 cron 也会改这个文件，两边同时改存在互相覆盖风险（10-24 已记录）。

## 历史序列（inexbot-open）

534 (07-18) → 552 (07-26) → 636 (07-31) → 715 (08-21) → 721 (08-25 起连续 7 次)
→ 795 (09-29, +74 zh) → 797 (10-01, +2) → 799 (10-10, +2)
→ 799 (10-18 / 10-19 / 10-21 / 10-22 连续 4 次持平，字节逐字节相同)
→ 799 (10-23, 字节 +4,154，**上游 API 改名**，非零变化)
→ 799 (10-24, 2,453,054 bytes，proxy 侧修复同日落地)
→ **799 (10-25, 2,453,054 bytes，与 10-23/24 逐字节相同，内容变更后连续 3 天零变化)**

姊妹 KB inexbot：558 (10-22 起持平)
