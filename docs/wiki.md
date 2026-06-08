# Codex Go Wiki

扩展文档。新手安装与日常使用请看 [README](../README.md)。

## 目录

- [运行环境要求](#运行环境要求)
- [架构与数据流](#架构与数据流)
- [工作原理](#工作原理简述)
- [当前限制](#当前限制)
- [界面语言与 CDP](#界面语言与-cdp)
- [排障](#排障)
- [公网访问（frp）](#公网访问frp)
- [手动启动](#手动启动)
- [项目结构](#项目结构)
- [API 接口](#api-接口)
- [环境变量](#环境变量)
- [修改原则](#修改原则)
- [CDP 调试](#cdp-调试)
- [开发检查](#开发检查)
- [安全边界](#安全边界)

## 运行环境要求

### 操作系统

- **macOS only**。依赖 `open`、`osascript`、`lsof` 等系统工具管理 Codex Desktop，不支持 Linux / Windows。
- 需要能正常打开 **Codex Desktop 图形界面**（无桌面会话的环境无法运行）。

### 必需软件

| 组件 | 要求 | 说明 |
| --- | --- | --- |
| Codex Desktop | 已安装并可登录 | 默认 `/Applications/Codex.app`；可用 `SOURCE_APP` 覆盖 |
| Python | 3.11+ | 由 `uv` 管理；见 `pyproject.toml` |
| uv | 最新稳定版 | [安装说明](https://docs.astral.sh/uv/getting-started/installation/) |
| 本仓库 | 已克隆 | 启动脚本与 `public/` 需在同一目录 |

Homebrew 安装（README 快速路径）：

```bash
brew install uv git
```

可选：本机也装一份 Python（`uv sync` 也会自动拉取 3.11+）：

```bash
brew install python@3.12
```

Codex Desktop 不能通过 Homebrew 安装。`curl`、`lsof`、`open` 等随 macOS 自带。

### 端口

| 端口 | 服务 | 绑定 | 说明 |
| --- | --- | --- | --- |
| `39443` | Codex CDP | localhost | 启动脚本注入；**不要暴露公网** |
| `8080` | Python bridge | 0.0.0.0 | 手机访问入口 |

检查：`./launch-codex-go.sh status`

### 文件与权限

- `~/.codex/` — 读取 Codex 会话（JSONL）
- `~/.codex-go/` — Codex Go 本地状态
- `~/Library/Application Support/Codex Go/CDP Worker/` — token、pid、日志

手机连不上时，检查 **系统设置 → 网络 → 防火墙** 是否拦截 `8080`。

### 手机端

- 现代移动浏览器；PWA 可选
- 局域网：手机与 Mac 同一 Wi‑Fi
- 访问 URL 必须带 `?token=...`（局域网内自用即可）

## 架构与数据流

Codex Go 由三部分组成：

```text
手机浏览器
  |
  | HTTP + token
  v
Mac 上的 Python FastAPI bridge
  |                       |
  | CDP DOM 控制          | 本地文件读取
  v                       v
Codex Desktop          ~/.codex/sessions/*.jsonl
```

发送链路：

1. 手机网页把消息发送到 `POST /send`。
2. Python bridge 校验 token 和请求内容。
3. Python bridge 连接 Codex Desktop 的 CDP 端口。
4. 它在 Codex 页面中选择目标线程、聚焦输入框、插入文本并点击发送。
5. Codex Desktop 正常处理任务，并把会话事件写入 `~/.codex`。

读取链路：

1. 手机网页轮询 `/codex/status`、`/codex/history`、`/codex/threads` 等接口。
2. Python bridge 读取 Codex 的 JSONL 会话文件和 `session_index.jsonl`。
3. 它把原始事件转换成手机端需要的线程列表、聊天历史、运行步骤、上下文用量、最终回复和权限请求。

关键点：**发送靠 CDP 控制 Codex GUI，读取靠本地会话文件**。Codex Go 不使用官方远程 API，也不会把会话同步到自己的云端。

## 工作原理（简述）

手机浏览器通过 HTTP + token 访问本机 Python bridge。发送消息时，bridge 经 CDP 控制 Codex Desktop 的输入框和按钮；读取线程、历史和状态时，bridge 直接解析 `~/.codex` 下的 JSONL 文件。

## 当前限制

- Codex Desktop 必须在启动时带上 CDP 参数；已经运行的 Electron/Chromium 进程不能后注入 CDP。
- 如果 Codex Desktop 的 DOM、菜单文字、快捷键行为或 JSONL 事件格式变化，相关功能可能需要调整。
- 这个项目按个人本机工具设计。能访问它的人，基本等于能远程操作你的本机 Codex Desktop。

## 界面语言与 CDP

Codex Go 通过 CDP 在 Codex Desktop 页面里**找按钮、点菜单、填输入框**。`codex_go/cdp/dom.py` 里用按钮文字、`aria-label`、正则表达式识别这些控件。

当前规则以**中文界面为主**，部分地方也写了英文关键词（例如 `Stop`、`allow`、`queued`）。若你的 Codex Desktop 是英文或其他语言，可能出现：

- 能打开页面，但发送、停止、权限、模型切换等操作失败
- 终端或手机端报错里出现「找不到发送按钮」「找不到权限按钮」等

**推荐做法：用 AI 协助改 CDP，而不是改 Codex 语言设置。**

1. 确认 `./launch-codex-go.sh status` 里 CDP 已就绪。
2. 在 Codex Desktop 里复现失败操作，记下手机端或 `codex-go-python.err.log` 里的报错原文。
3. 打开 `codex_go/cdp/dom.py`，把**你的 Codex 界面语言**、**哪一步失败**、**报错原文**一起发给 AI（Cursor、Codex 等均可），请它补全或调整对应函数里的文字/正则匹配。
4. 若 AI 需要你提供界面文字：在 Codex 里对失败按钮使用「检查」或 Accessibility 工具查看 `aria-label` / 可见文本，贴给 AI。
5. 改完后执行 `./launch-codex-go.sh restart`，再测发送、停止、权限；若动过发送逻辑，跑 `python3 tests/test_composer_send_guard.py`。

主要入口在 `dom.py` 里这些表达式（搜索函数名即可定位）：

| 功能 | 相关逻辑 |
| --- | --- |
| 发送 / 停止 | `click_send_expression`、`stop_response_expression` |
| 排队消息 | `pending_sends_expression`、`pending_send_action_expression` |
| 权限弹窗 | `permission_action_expression` |
| 模型 / 推理 | `switch_model_expression`、`switch_reasoning_expression` |

改 CDP 时的仓库约束见 [AGENTS.md](../AGENTS.md)。DOM 层排查顺序见下文「CDP 调试」。

## 排障

查看状态：

```bash
./launch-codex-go.sh status
```

查看日志：

```bash
ls -la "$HOME/Library/Application Support/Codex Go/CDP Worker"
```

常见问题：

- `CDP status: not ready`：完全退出 Codex，然后运行 `./launch-codex-go.sh restart`。
- `Python bridge port 8080 is already occupied`：停止占用端口的进程，或设置 `PYTHON_PORT` 使用其他端口。
- 手机打不开局域网地址：确认手机和 Mac 在同一网络下，并检查 macOS 防火墙是否允许 Python bridge 接入。
- token 错误：使用启动脚本打印的完整 URL，确保包含 `?token=...`。

CDP 与 DOM 层面的开发排查见下文「CDP 调试」。

## 公网访问（frp）

默认局域网模式更安全。公网访问意味着互联网上能到达隧道的人，都有机会访问一个可以控制你本机 Codex Desktop、读取本机会话日志的服务。**链接里的 token 等同遥控权限，切勿分享给他人或发到公开场合。**

如果一定要公网使用，请遵守这些原则：

1. 只暴露 Python bridge 端口，默认是 `8080`。
2. 不要暴露 Codex CDP 端口 `39443`。
3. Codex Go 的 token 必须保密。
4. 尽量使用 HTTPS。
5. 推荐在 frp 层加 HTTP Basic Auth，或在前面再加一层带认证的反向代理。

[frp](https://github.com/fatedier/frp) 可以把 NAT 后面的本地服务暴露到公网。新版 frp 推荐使用 TOML/YAML/JSON 配置。

下面提供 **TCP 隧道**（配置简单）和 **HTTP 隧道 + 域名**（适合长期使用）两种方式。

### TCP 隧道

TCP 模式配置简单，适合快速验证。它没有 frp HTTP Basic Auth 这一层保护，只剩 Codex Go token，攻击面更大。

公网服务器上的 `frps.toml`：

```toml
bindPort = 7000

[auth]
method = "token"
token = "replace-with-a-long-random-frp-token"
```

Mac 上的 `frpc.toml`：

```toml
serverAddr = "your-public-server-ip-or-domain"
serverPort = 7000

[auth]
method = "token"
token = "replace-with-the-same-long-random-frp-token"

[[proxies]]
name = "codex-go-tcp"
type = "tcp"
localIP = "127.0.0.1"
localPort = 8080
remotePort = 18080
```

访问地址：

```text
http://your-public-server-ip:18080/?token=<Codex Go token>
```

### HTTP 隧道 + 域名

在公网服务器上运行 `frps`：

```toml
bindPort = 7000
vhostHTTPPort = 8080

[auth]
method = "token"
token = "replace-with-a-long-random-frp-token"
```

启动：

```bash
./frps -c ./frps.toml
```

把域名（例如 `codex-go.example.com`）解析到公网服务器，然后在 Mac 上运行 `frpc`：

```toml
serverAddr = "your-public-server-ip-or-domain"
serverPort = 7000

[auth]
method = "token"
token = "replace-with-the-same-long-random-frp-token"

[[proxies]]
name = "codex-go"
type = "http"
localIP = "127.0.0.1"
localPort = 8080
customDomains = ["codex-go.example.com"]

# frp 层的额外保护，在 Codex Go token 校验之前生效。
httpUser = "replace-user"
httpPassword = "replace-password"
```

访问地址：

```text
http://codex-go.example.com:8080/?token=<Codex Go token>
```

如果在公网服务器上用 nginx、Caddy 或其他反向代理给 frp 前面加 HTTPS，可以把公网 HTTPS 域名转发到 `vhostHTTPPort`。

### frp 安全检查清单

- frp 的 `[auth].token` 使用足够长的随机字符串。
- HTTP 隧道模式下启用 `httpUser` 和 `httpPassword`。
- Codex Go 的 `CODEX_GO_TOKEN` 使用足够长的随机字符串；启动脚本会把它保存在 `codex-go-token` 文件里。
- 不要在截图、日志或聊天里泄露带 token 的完整 URL。
- 不要转发 `39443`，那是本机 Codex CDP 端口。
- 可以用服务器防火墙限制只有你的固定 IP 能访问 `vhostHTTPPort` 或 `remotePort`。

## 手动启动

推荐使用 `./launch-codex-go.sh`。只有在你已确认 Codex Desktop 正在 `39443` 端口以 CDP 模式运行时，才建议手动启动后端：

```bash
CODEX_GO_TOKEN="$(uuidgen | tr '[:upper:]' '[:lower:]')" uv run codex-go-server
```

然后打开终端打印的手机访问地址。

## 项目结构

```text
codex_go/                  Python + FastAPI 后端
  config.py                环境变量、路径、端口、token、limit
  main.py                  uvicorn 入口
  api/                     FastAPI 路由、静态文件、鉴权
  cdp/                     CDP target、WebSocket、DOM 操作
  codex/                   JSONL 会话读取与解析
  services/                业务编排（发送、权限、线程等）
  state/                   Codex Go 本地状态
public/                    手机端控制台
launch-codex-go.sh         启动 Codex CDP 与 Python bridge
tests/                     单元测试
```

模块边界：

- `api` 只处理 HTTP 输入输出、鉴权和 response shape。
- `services` 组合 CDP、JSONL parser 和 state。
- `cdp` 只处理 Codex Desktop 的 CDP target、WebSocket 和 DOM 操作。
- `codex` 只读取并解析本机 Codex 文件，不依赖 FastAPI，也不操作 CDP。
- `config.py` 是唯一读取环境变量的模块。

## API 接口

所有 API 都需要访问 token。token 可以放在 query、Cookie 或 `x-codex-go-token` 请求头里。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/` | 返回手机网页 |
| `GET` | `/codex/health` | 检查 Python bridge 是否存活 |
| `GET` | `/codex/cdp-health` | 检查 Codex CDP 是否可连接 |
| `GET` | `/codex/config` | 返回应用配置、静态模型目录和局域网访问地址（不打开 Codex 模型菜单） |
| `POST` | `/send` | 发送消息到 Codex |
| `GET` | `/codex/threads` | 读取 Codex 线程列表 |
| `GET` | `/codex/history` | 读取指定线程的本机历史记录 |
| `GET` | `/codex/status` | 读取当前或最近一次 Codex 回复状态 |
| `GET` | `/codex/gui-status` | 通过 CDP 读取 Codex 当前可见 GUI 状态 |
| `POST` | `/codex/select` | 切换到指定 Codex 线程 |
| `POST` | `/codex/new-thread` | 创建新线程 |
| `POST` | `/codex/thread-action` | 归档、置顶、取消置顶或重命名线程 |
| `GET` | `/codex/pending-sends` | 读取 Codex 排队消息 |
| `POST` | `/codex/pending-send-action` | 处理 Codex 排队消息 |
| `POST` | `/codex/permission-action` | 处理 Codex 权限请求 |
| `GET` | `/codex/model-options` | 通过 CDP 读取 Codex 当前可用模型列表（仅在手端打开模型菜单时使用） |
| `POST` | `/codex/model-switch` | 通过 Codex UI 切换模型 |
| `POST` | `/codex/reasoning-mode` | 通过 Codex UI 切换推理模式 |
| `POST` | `/codex/stop` | 停止当前 Codex 回复 |

改 `codex_go/` 时同时考虑 `public/js/app.js` 依赖的 API 字段。

## 环境变量

### 启动脚本

```bash
SOURCE_APP=/Applications/Codex.app
CDP_PORT=39443
PYTHON_PORT=8080
PYTHON_HOST=0.0.0.0
SUPPORT_DIR="$HOME/Library/Application Support/Codex Go/CDP Worker"
UV_BIN=uv
```

### Python bridge

环境变量以 `CODEX_GO_` 为前缀，或在 `config.py` 中映射：

```bash
PORT=8080
HOST=0.0.0.0
CODEX_GO_TOKEN=<访问令牌>
CODEX_GO_CDP_HOST=localhost
CODEX_GO_CDP_PORT=39443
CODEX_GO_STATE_DIR="$HOME/.codex-go"
CODEX_GO_CODEX_HOME="$HOME/.codex"
CODEX_GO_PUBLIC_DIR="$PWD/public"
```

### 重要路径

启动脚本状态目录：

```text
~/Library/Application Support/Codex Go/CDP Worker/
```

常见文件：

- `codex-go-token`：本地访问 token
- `codex-go-python.pid`：Python bridge pid
- `codex-go-python.out.log` / `codex-go-python.err.log`：Python bridge 日志
- `main-codex-cdp.out.log` / `main-codex-cdp.err.log`：Codex CDP 启动日志

Codex 会话读取路径：

```text
~/.codex/session_index.jsonl
~/.codex/sessions/**/*.jsonl
```

## 修改原则

- 后端配置只放在 `codex_go/config.py`，其他模块接收 `Settings`。
- API route 只处理 HTTP 输入输出；复杂逻辑放到 `services/`、`cdp/` 或 `codex/`。
- 改 `public/` 时注意自动刷新、历史恢复、GUI 状态同步不能触发发送。
- 当前发送主链路是 CDP DOM 控制，不是剪贴板自动化。
- 修改发送链路后必须跑 `tests/test_composer_send_guard.py`，防止刷新或程序化事件误提交编辑框内容。
- 公网/frp 场景只暴露 Python bridge 端口，不能暴露 Codex CDP 端口。

面向 Codex/agent 的完整约束见 [AGENTS.md](../AGENTS.md)。

## CDP 调试

先确认 Codex 和 Python bridge 都被启动脚本管住：

```bash
./launch-codex-go.sh status
```

检查 CDP target：

```bash
curl -fsS http://127.0.0.1:39443/json/list
```

可用的 Codex target 通常满足：

- `type` 是 `page`
- `url` 以 `app://-/index.html` 开头
- 存在 `webSocketDebuggerUrl`

检查 Python bridge 暴露的 CDP 健康接口：

```bash
TOKEN="$(tr -d '\r\n' < "$HOME/Library/Application Support/Codex Go/CDP Worker/codex-go-token")"
curl -fsS "http://127.0.0.1:8080/codex/cdp-health?token=$TOKEN"
```

如果 CDP 不可用，按这个顺序排查：

1. `./launch-codex-go.sh status` 查看 `39443` 和 `8080` 的监听进程。
2. 如果 Codex 已经运行但没有 CDP，执行 `./launch-codex-go.sh restart`。
3. 查看 `main-codex-cdp.err.log` 是否有 Chromium/Electron 启动错误。
4. 查看 `/json/list` 是否有 `app://-/index.html` target；没有 target 时，优先修启动。
5. 查看 `codex-go-python.err.log` 是否是 Python 依赖、token 或端口占用问题。

如果 CDP 已连接但功能失败，按这个顺序排查：

1. 先调用 `/codex/cdp-health`，确认后端能列出 CDP target。
2. 再调用相关只读接口，例如 `/codex/gui-status`、`/codex/status`、`/codex/threads`。
3. 确认失败发生在读取 JSONL、切线程、聚焦 composer、插入文本、点击发送、权限按钮、模型菜单或推理菜单哪一层。
4. 只在确认 target 正常后再调整 `codex_go/cdp/dom.py` 里的 DOM selector / CDP evaluate 逻辑。

## 开发检查

```bash
python3 -m compileall codex_go
python3 tests/test_permission_status.py
python3 tests/test_composer_send_guard.py
bash -n launch-codex-go.sh
```

如果依赖已通过 uv 安装：

```bash
uv run python -m compileall codex_go
uv run python tests/test_permission_status.py
uv run codex-go-server
```

## 安全边界

能访问 Python bridge 的人，可以读取本机 Codex 会话摘要，并通过 Codex Desktop 执行发送、停止、切换线程、切换模型、处理权限等操作。token 泄露应视为远程控制入口泄露。

不要把 `39443` 暴露到公网。frp 或反向代理只应转发 Python bridge 端口，默认是 `8080`，并应叠加 HTTPS、强 token 和代理层认证。
