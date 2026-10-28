# 2026-08-28 爬取验证

**结论**：与 2026-08-25 完全一致，零变化。

## 数据

| 指标 | 2026-08-25 基线 | 2026-08-28 实测 | 差值 |
|------|-----------------|-----------------|------|
| inexbot-open docs | 721 | 721 | 0 |
| inexbot docs | 547 | 547 | 0 |
| 爬取耗时 | (≈2:46 上次) | 2:41 | -5s |
| 失败页面 | 0 | 0 | 0 |

无新增文档，无 locale 异常，无 loaded=false。

## 工具坑（这次踩到的）

### Hermes `terminal(wait, timeout=…)` 静默 clamp 到 60s

不管传 `timeout=300` 还是 `timeout=600`，实际最长等 60s 就返回 `status="timeout"`。长任务需要：

- 用 `process(poll, session_id, timeout=600)` 而不是 `wait`——`poll` 会尊重请求的 timeout
- 或者分段轮询：先 `wait`（拿中途输出），再 `poll`（续等）

### 后台启动后第一帧 `exit_code=0` 不可信

`terminal(background=true)` 返回 `{"exit_code": 0, ...}` 表示**启动成功**，不代表**进程完成**。要看真实状态必须再 `process(poll)` 一次。第一次看到 exit_code=0 会以为是已完成、其实进程刚 fork 出去。

### systemd restart race window 比想象宽

SKILL.md 之前写 `sleep 5` 够用。**2026-08-28 实测**：`sleep 5` 仍 Connection refused，`sleep 8` 才稳定通过。窗口宽度跟机器当时负载相关，是个脆弱区间。

**稳定对策（按优先级）**：
1. 直接跑 `scripts/check_proxy_health.py`——脚本内部有 retry，跨窗口最稳
2. 分两条独立 terminal 命令：`sudo systemctl restart hermes-skill-proxy`，再 `sleep 8 && curl .../health`。不要 `&&` 链在一起

## 本次执行序列

1. `terminal(background=true, command="python3 .../crawler.py")` → 后台启动 PID 1229146
2. 第一次 `process(poll, timeout=300)` → running, 2s uptime
3. `process(wait, timeout=420)` → 被 clamp 到 60s 返回 timeout（误解：以为进程挂了）
4. 多次 `process(poll, timeout=600)` 轮询 → 161s 时 exited, exit_code=0, 721/721
5. `terminal(command="sudo systemctl restart hermes-skill-proxy")` → 立即返回 exit_code=0（systemd 发命令成功）
6. `terminal(command="python3 .../check_proxy_health.py")` → 立即 Connection refused（restart race）
7. `terminal(command="sleep 8 && python3 .../check_proxy_health.py")` → OK, both baselines met

## 下次 cron 建议

- 爬取 + 重启 + 健康检查的完整链路如果想省一次轮询，直接 chain `sudo systemctl restart hermes-skill-proxy && sleep 8 && python3 .../check_proxy_health.py`——`check_proxy_health.py` 内部重试能 cover 掉 8s 之外的窗口，比裸 `curl /health` 稳得多。
- 不要用 `process(wait, timeout=N>60)`——浪费一次调用还以为是 timeout 失败。