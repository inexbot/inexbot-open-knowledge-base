# SDK 下载位置与 open.inexbot.com SPA 抓取技巧

整理"RTL-22.07 / RTL-24.03 SDK 在哪下载"类问题的工作流，及 open.inexbot.com
作为 VitePress SPA 站点的抓坑经验。

---

## 1. SDK 实际下载位置

**官方文档首页**："相关下载"页 — `https://open.inexbot.com/zh/12.相关下载`
（其他语种：`/en/12.Downloads`、`/kr/12.관련-다운로드`）

**当前状态（2026-08-13）**：所有 SDK 包统一托管在百度网盘：
`https://pan.baidu.com/s/1p8xEYpZ0ng37OlJla395DQ?pwd=8888`  提取码 `8888`

网盘目录：

| 目录 | 内容 |
|---|---|
| `C++/` | C++ SDK 各平台/编译器版本 |
| `C#/` | C# SDK 各 .NET 版本 |
| `Python/` | Python SDK 各版本 |
| `Firmware/` | 控制器固件升级包 |
| `Tools/` | 开发工具和文档 |

**重要**：网盘外没有直接的 HTTPS 下载链接。官方"相关下载"页面 HTML
内容都是 SPA 壳子，需要从 GitHub 源仓库拿原文（见第 3 节）。

### 选型核对清单

用户问"RTL-XX.YY 的 SDK 怎么下载"时，必须先帮他确认：

1. 控制器型号（在示教器"系统信息"查看，C2201 / C1201 / C2200 等）
2. 固件版本（是否在 RTL-22.07 / RTL-24.03 兼容矩阵内）
3. 开发语言：C++ / C# / Python
4. 平台架构：Windows x64 / Linux x64 / Linux ARM64
5. C++ 还要确认 MSVC vs MinGW（MinGW 库与 MSVC 库**绝对不能混用**）

**常见选错坑**：

- 把 RTL-22.07 SDK 用在 RTL-24.03 控制器（或反向） — 协议命令字不兼容
- Python SDK 把 Linux 的 `_nrc_host.so` 用到 Windows 上 — 立即 ImportError
- C++ MinGW 包链接了 MSVC 编译的 `nrc_host.dll` — 链接/运行时双重炸

---

## 2. 知识库的局限 — 不要在 KB 里找下载链接

`~/.hermes/kb/inexbot-open/md/` 下**所有**接口说明、环境搭建、API 示例页的
正文都会出现"SDK 包：从下载页获取"、"请前往相关下载 → 控制器 SDK 中下载"
这类表述，但**没有给出具体 URL**。这是因为 200+ 篇文档都假设读者会点页
顶导航进入"12.相关下载"页。

Proxy 注入的是这些描述的摘要，所以自动回答也只会说"去下载页"——
**永远需要再走一步获取实际下载链接**。

需要主动做的：

1. `retrieve.py` 命中后看是否有 URL 字段指向"12.相关下载"
2. 没有就直接抓取 GitHub 源（见第 3 节）
3. 不要尝试 `curl https://open.inexbot.com/zh/12.相关下载` 拿正文 — 见下

---

## 3. open.inexbot.com 是 VitePress SPA — 直接 curl 拿不到正文

`open.inexbot.com` 全站用 VitePress 构建，HTML 文档本身是空壳，页面内容
由 JS 在浏览器运行时渲染。直接 `curl` 拿到的 HTML 里：

- `<body>` 内只有一个 `<div id="app"></div>`
- 真正内容在 `<script>window.__VP_HASH_MAP__=...</script>` 里作为 JSON 嵌入

### 抓取方法对比

| 方法 | 拿到正文？ | 备注 |
|---|---|---|
| `curl https://open.inexbot.com/zh/12.相关下载` | ❌ 空 HTML 壳 | 内容在 JS 里 |
| `curl .../assets/zh_12.相关下载.md.HASH.lean.js` | ⚠️ 仅前端模块壳 | 内容数据是 `"[]"`（被压缩） |
| `curl ...raw.githubusercontent.com/inexbot/inexbot-sdk/main/docs/zh/12.相关下载.md` | ✅ 完整原文 | **首选** |
| `curl .../api.github.com/repos/inexbot/inexbot-sdk/contents/` | ✅ 目录树 | 找具体路径用 |
| 启动浏览器渲染（Playwright 等） | ✅ 但慢 | 杀鸡用牛刀 |

### 推荐流程（用户问 SDK 下载时）

```bash
# 1. 拿目录树，找相关下载页路径
curl -L --max-time 30 -s \
  'https://api.github.com/repos/inexbot/inexbot-sdk/git/trees/main?recursive=1' \
  -o /tmp/tree.json
# 过滤 "12." 或 "download" 或 "sdk" 的条目

# 2. 直接拉中文相关下载页原文（路径已知）
curl -L --max-time 20 -s \
  'https://raw.githubusercontent.com/inexbot/inexbot-sdk/main/docs/zh/12.相关下载.md'
#  → 包含百度网盘链接 + 兼容矩阵 + 各 SDK 选型表

# 3. （可选）英文版路径不同：docs/en/12.Downloads.md
#    韩文版：docs/kr/12.관련-다운로드.md
```

### GitHub 仓库结构（截至 2026-08-13）

`https://github.com/inexbot/inexbot-sdk` — 开放平台文档源仓库。

```
docs/
├── en/.../12.Downloads.md        (英文版相关下载)
├── kr/.../12.관련-다운로드.md      (韩文版相关下载)
└── zh/.../12.相关下载.md          (中文版相关下载)  ← 这就是源
```

注意路径里有 `docs/zh/` 还是 `docs/zh-CN/`：本仓库用的是 `docs/zh/`（不带 CN）。
如果以后迁仓库路径变了，跑 `git/trees?recursive=1` 重新核对。

---

## 4. 兼容矩阵速查

`docs/zh/12.相关下载.md` 内嵌的兼容矩阵（节选）：

| 控制器型号 | RTL 版本 | 端口 | C++ SDK | C# SDK | Python SDK | JSON 协议 |
|---|---|---|---|---|---|---|
| 待研发确认 | RTL-22.07 | 6000 / 7000 | 待研发确认 | 待研发确认 | 待研发确认 | [RTL-22.07 文档](./05.JSON-协议/01.RTL-22.07/index.md) |
| 待研发确认 | RTL-24.03 | 5000 / 7000 | 待研发确认 | 待研发确认 | 待研发确认 | [RTL-24.03 文档](./05.JSON-协议/02.RTL-24.03/index.md) |

版本选择建议：

- **RTL-22.07** — 早期稳定版本，保有量大。仅重大 bug 修复，不再合入新功能
- **RTL-24.03** — 当前主流出货版本。bug 修复 + 关键功能合入
- 无法确认控制器型号或 RTL 版本时，去示教器"系统信息"查看

---

## 5. 给用户的回复模板

用户问"RTL-22.07 SDK 在哪下载"时，可以这样答：

```
RTL-22.07 协议对应的 SDK 在纳博特开放平台"相关下载"页：
https://open.inexbot.com/zh/12.相关下载

下载包统一托管在百度网盘：
https://pan.baidu.com/s/1p8xEYpZ0ng37OlJla395DQ?pwd=8888
提取码：8888

下载前先确认：
1. 控制器型号（在示教器"系统信息"看，如 C1201/C2201/C2200）
2. 固件 RTL 版本（必须与控制器一致，否则命令字不兼容）
3. SDK 类型（C++/C#/Python）
4. 平台架构（Windows x64/Linux x64/Linux ARM64）
5. C++ 还要确认 MSVC 还是 MinGW，两套库不能混用

注意：RTL-22.07 属旧版稳定协议，新项目建议 RTL-24.03；但旧控制器维护
项目必须选 RTL-22.07 SDK，不能直接换 RTL-24.03 的库。
```

如果用户是维护 C1201 这类老控制器，强调"**必须**与控制器固件版本匹配"。

---

## 6. 兜底：直接联系纳博特

如果下载页信息不全、网盘链接失效或找不到对应版本：

- 邮件：sales@inexbot.com
- 邮件中**必须**写清楚：控制器型号、RTL 版本、所需 SDK 语言/平台
- 不要让用户瞎试 — 版本不匹配的 SDK 调用会报各种莫名其妙的运行时错误