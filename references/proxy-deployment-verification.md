# proxy 部署验证：怎么证明「补丁真的上线了」

> 2026-11-05 现场总结。姊妹 KB `inexbot-knowledge-base` 有同一主题的内容，
> 两边可以互相参照。

## 一、问题的本质：三个「在」互不蕴含

排查「proxy 的配置/代码改动有没有生效」时，有**三个独立的「在」**：

| # | 「在」是什么意思 | 怎么验 | 失败时的症状 |
|---|---|---|---|
| ① | **文件在磁盘上** | `grep` unit 文件 / `git log` | — |
| ② | **systemd 知道它** | `daemon-reload` 后 `systemctl show -p Environment` | 改了 unit 但没 reload → systemd 仍用旧 unit |
| ③ | **线上进程带着它** | `/proc/<pid>/environ` | **静默失效**（最危险） |

**最常见的错误认知**：以为 ① 成立就等于 ③ 成立。

## 二、2026-11-05 的现场：③ 缺位滞留了 4 天

| 项 | 值 |
|---|---|
| unit 文件 mtime | **2026-11-04 11:36:49**（`/etc` 与 repo 模板**两份都改对了**） |
| 线上进程启动时间 | **2026-10-31 11:36:48**（PID 1792095） |
| 进程比补丁早 | **4 天** |
| 实际效果 | proxy 一直用旧的 **300s** 上游 timeout → 用户查长手册**随机 502** |
| 表层检查 | `/health` 绿灯、检索链路 PASS、引用链接 200 —— **全部照常** |

→ 只有**真正打一次完整请求**（e2e 探针）才暴露。

**根因**：unit 改了 ≠ 进程重启了。systemd 只在**进程启动时**读取 unit 的 `Environment=`。

**修复**：`daemon-reload` → `restart` → 验证新 PID 的 environ。

## 三、判据：看 `/proc/<pid>/environ`，不看 unit 文件

```bash
# 最小验证（hash-only，避免泄露 key 明文）
python3 scripts/check_proxy_env.py --units
```

手写版（等价）：

```python
import hashlib, subprocess
from pathlib import Path

pid = subprocess.check_output(["pgrep", "-f", "hermes-skill-proxy.py"]).decode().split()[0]
env = dict(
    k.decode().split("=", 1)
    for k in Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
    if b"=" in k
)
for name in ("PROXY_PORT", "HERMES_URL", "HERMES_API_KEY", "SKILL_NAME", "HERMES_TIMEOUT"):
    v = env.get(name)
    print(f"  {name}: " + ("ABSENT" if v is None
          else f"len={len(v)} sha12={hashlib.sha256(v.encode()).hexdigest()[:12]}"))
```

## 四、⚠️ 一定要用 sha 摘要，不要看裸字符串

**Hermes 的输出脱敏**会把密钥渲染成带省略号的形式：

| 你 `cat` 看到的 | 真实长度 | 真实 sha12 |
|---|---|---|
| `hermes...rch` | **12**（假象） | — |
| `hermes...arch` | **13**（假象） | — |
| 实际部署版 unit | **21** | `23760f4462da` |
| 线上 environ | **21** | `23760f4462da` |
| 代码默认值 `hermes-website-search` | **21** | `23760f4462da` |

→ **三者完全一致，没有截断污染。**
2026-10-29 曾因为 `grep` 看到 `hermes...arch`（len=13）就断定「部署版被截断污染了」，
险些用一个错误的 key 去转发 gateway。**这是脱敏，不是截断。**

> 📌 这是姊妹 KB `shared-proxy-service-pitfalls.md` §陷阱 9 的同一件事，
> 本 skill 从姊妹那边同步时明确要求「判读一律用 sha 摘要」。

## 五、restart 的最佳时机

**选「crawler 在跑、但没有任何 probe 在飞」的窗口。**

```bash
ps -eo pid,etime,cmd | grep -E "[c]heck_e2e|[c]heck_retrieval" | head
# 没有输出 = 安全的 restart 窗口
```

理由：姊妹 KB 的 cron 与本 skill **同在 11:00** 跑，两边都会 restart 同一个 proxy。
在对方探针飞行途中 restart，会把它的请求打成 `RemoteDisconnected`——
那**不是检索崩了**（判读表：500 才是崩），但会污染双方的故障统计。

2026-11-05 实际时序：

| 时刻 | 事件 |
|---|---|
| 11:00 | 两个 KB 的 crawler 几乎同时启动 |
| 11:01 | 本 skill 的 crawler 开始（无任何 probe 在飞） |
| **11:02:57** | **本 skill restart proxy**（PID 1792095 → 1844673）✅ 安全窗口 |
| 11:04:47 | 本 skill 的 crawler 完成（799/799） |
| 11:07 | 姊妹 KB 启动它自己的 e2e 探针 —— **未被本轮 restart 打断** |
| 11:14 | 姊妹 KB 提交 `abb129c`（纯注释，无行为变化） |

## 六、restart 之后的验证顺序

```bash
sudo -n systemctl daemon-reload
sudo -n systemctl restart hermes-skill-proxy.service
sleep 8                                              # 启动窗口 ~几百ms-8s（随负载变）
python3 $SK/scripts/check_proxy_health.py             # 内部带 retry
python3 $SK/scripts/check_proxy_env.py --units        # 确认新环境变量到位
```

⚠️ **不要只跑一次健康检查就判定失败** —— restart 后第一次跑
`check_proxy_health.py` 仍可能拿到 `[Errno 111] Connection refused`（2026-10-30 实测）。
必须带重试。

⚠️ **不要把 restart 和 curl 链在同一条 `&&` 里**（见 SKILL.md「同一条命令里会假性失败」）。

## 七、三层 timeout 的当前状态（2026-11-05 起）

| 层 | 位置 | 值 |
|---|---|---|
| ① provider read timeout | `agent/anthropic_adapter.py:549` `_read_timeout` | 900s |
| ② gateway agent timeout | `~/.hermes/config.yaml` `agent.gateway_timeout` | 1800s |
| ③ **proxy 上游 read timeout** | `hermes-skill-proxy.py:47` `HERMES_TIMEOUT` | **1800s** ✅ 已对齐 |

**改动 ③ 要同时改三处**（缺一则线上不一致）：

1. `/etc/systemd/system/hermes-skill-proxy.service`（部署版）
2. `/home/ecs-user/hermes-skill-proxy/hermes-skill-proxy.service`（repo 模板，`setup.sh` 会渲染它）
3. `scripts/check_proxy_env.py` 的 `EXPECTED` 字典（本 skill 的守卫）

然后 `daemon-reload` + `restart` + 跑 `check_proxy_env.py --units` 验证。

> ⚠️ **改大 proxy 上游 timeout 后，客户端 timeout 也必须跟着放大**：
> `check_e2e_request.py` 的默认 client timeout 已从 360 改成 **1860**
> （必须 > proxy 上游 1800s，否则长尾请求被客户端先掐断 → 拿到 `000`/exit 28，
> 而**不是**真实的 502 —— 会被误判成故障）。
> **姊妹 KB 那份脚本的默认值可能还是 360**，建议它同步。

## 八、并发 commit 的良性竞态

本 skill 与姊妹 KB 会在**同一分钟**向 `hermes-skill-proxy` repo 提交。

- 2026-11-05：本 skill 提交 `846b3de`（unit 加 `HERMES_TIMEOUT=1800`），
  姊妹 KB 随后提交 `abb129c`（纯注释）→ **HEAD 变成 `abb129c`，但 `846b3de` 仍在历史里**。
- 判读：`git log --oneline -5` 确认自己的 commit **还在**即可，
  **HEAD 不等于自己的 commit 是正常的**（姊妹叠在上面）。
- 看到别人的 commit 叠在自己上面，务必 `git show <sha> --stat` 看它**改了什么**——
  若是纯注释 → 行为中性，无需处理；若是改了同一处 → 需要复核。
