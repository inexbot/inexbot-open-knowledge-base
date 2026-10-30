# 2026-10-29 爬取状态：799/558 连续第十次持平 + 三修 + systemd env 缺陷

## 爬取本体：完全稳态

| 项目 | 结果 |
|---|---|
| 爬取页数 | **799 / 799**（0 失败） |
| 耗时 | **3:20**（稳态带 3:00–3:20 内） |
| index.json | 2,453,407 bytes → 与 10-28 **逐字节相同** |
| verdict | `IDENTICAL`（`check_crawl_state.py`） |
| 网络请求 | **0**（日志 `✓` 行 = 0；`raw/` 最新 mtime = 2026-10-23） |
| locale 拆分 | zh=443 / en=178 / kr=178 |
| `.tmp` 残留 | 无（原子写正常） |
| 姊妹 KB | 558（11:04:45 写完，同窗口） |

上游**零变化**，连续第 10 次持平。

## 本 cycle 的主要成果：修掉 3 个此前从未记录的缺陷

全部属于**本地抽取 / 部署配置**，与上游无关。
详细分析见 `references/index-hygiene-and-systemd-env-bugs.md`。

### ① 标题含 U+200B 零宽字符 —— 764 个条目

姊妹 KB `inexbot` 的 `crawler.py` 早已有 `clean_text()`，本 KB 一直漏着。

- 根因：VitePress 的 `<h1>` 里 header-anchor 的内容就是 U+200B，
  `h1.get_text(strip=True)` 把它一起取了出来 → `'C++ 上位机开发\u200b'`
- 检索影响有限（jieba 把 U+200B 单独切成 1 字符 token，被 `len(w)>=2` 过滤），
  但影响展示和精确短语匹配（`query_lower in title`）
- **踩坑**：字面 U+200B 写进源码被**静默吞掉** → 字符集必须用 `chr(0x200B)` 构造

### ② 空标题 39 条 / 完全无内容条目 34 条

- 这 34 条是**上游的空目录页**：`raw/` 有 263KB 整站壳，但
  `div.vp-doc` 的 textlen = 0、`og:title` 也**不存在**
- → **正文补不了，只能补标题**（否则丢掉 proxy 的短语命中 +20 和标题 token +3）
- 修复：移植姊妹 KB 的 `og:title → URL 末段 → description` 兜底链
- 实测这 39 页有 `og:title` 的只有 **0 个** → 全部靠 URL 末段生效

### ③ systemd `Environment=` 块语法错误 → 4 个环境变量被静默忽略

- `Environment=` 后跟缩进续行，systemd **不认** → 4 个变量全被丢弃
- 症状：journal 反复出现 `Unknown key name 'PROXY_PORT' in section 'Service', ignoring.`
- 修复：每行一个 `Environment="K=V"`
- `HERMES_API_KEY` 必须写**代码默认值** `hermes-website-search`
  （`/etc` 里那个 `hermes...arch` 是被截断的占位符，原块被忽略所以线上一直用默认值）

## 离线重建与内容完整性验证

```bash
python3 scripts/regenerate_from_cache.py --check   # rewritten=799 unchanged=0
python3 scripts/regenerate_from_cache.py             # 写盘
python3 scripts/regenerate_from_cache.py --check   # rewritten=0 unchanged=799 ✅
```

index.json：2,453,407 → **2,450,869 bytes**（-2,538）。

**内容完整性核对（关键，不能只看 rewritten=0）**：

- 全量 799 页未截断 `content_md` 比对：774 条一致，25 条不同
- 25 条差异**全部是空白差异**（`\n \n` → `\n\n`，行尾 rstrip 所致）
- **分词级 token 丢失数 = 0** ✅
- ⚠️ `content_snippet` 长度变化是 **800 字窗口边界移动**的假象，不是内容丢失

## 验证结果

| 检查 | 结果 |
|---|---|
| `check_proxy_health.py` | ✅ open=799 / inexbot=558 / loaded=True |
| `check_retrieval_chain.py` | ✅ 静默降级(==800)=**0**、异常=False；4 条 <200 均为姊妹 KB 上游占位报警页 |
| index 可达 md 解析 | ✅ 799/799，miss=0 |
| 幻影 token（`cppset_...`/`star_servo_...`） | ✅ index 可达数 = 0 |
| systemd unit | ✅ `systemd-analyze verify` 对本单元零告警 |

## 遗留待办（本轮工具额度用尽，未完成）

1. **⚠️ proxy 尚未用新单元重启** —— 单元已 `daemon-reload` 且
   `systemctl show -p Environment` 已能正确显示 4 个变量，
   但**运行中的 PID 1761173 仍是旧环境**。下一轮需：
   `sudo -n systemctl restart hermes-skill-proxy` → 再跑 `check_proxy_health.py`
   （勿与 curl 串在同一条命令里）。当前 proxy 检索功能正常，**不重启也不影响用户**。
2. **⚠️ 改动未提交** —— `crawler.py`（clean_text + 标题兜底）留在工作区未 commit；
   `hermes-skill-proxy.service` 模板已改未 commit；`references/.index-snapshot.json` 已被重建脚本刷新（M 状态）。
3. `SKILL.md` 已在本次 skill 更新中补记三修结论。
4. `md/` 仍有 1,855 文件 vs 799 索引条目（1,677 带 locale 前缀 + **178 个旧版无前缀死缓存**）
   —— 按 skill 记录属无害死缓存，proxy 只按 index path 定位，不影响检索，未清理。

## 流程层面的观察

- 姊妹 KB cron 与本 skill cron **完全同窗口**（11:00），本 skill 3:20 完成 → 稳态带内。
- 启动前 `pgrep -af "crawler.py"` 确认无姊妹 KB 并发 → 排期**不需要错开**。
- `execute_code` 沙盒 inline `os.kill` + `time.sleep` 循环等待长任务：一次调用等完，
  比 `wait_pid.py` 更省一次 spawn 延迟（沙盒 `time` 需显式 `import time`）。
