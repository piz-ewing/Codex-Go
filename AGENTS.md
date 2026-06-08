# AGENTS.md

给进入本仓库的 Codex / agent 使用。改代码或文档前先读本文。

## 项目是什么

Codex Go 是一个**独立的**、非官方工具：用手机浏览器遥控本机 **Codex Desktop**。任务仍在 Mac 上执行；Python bridge 负责鉴权、读会话、同步状态，并通过 CDP 操作 Codex GUI。

核心目录：

| 路径 | 职责 |
| --- | --- |
| `codex_go/` | Python + FastAPI 后端：token、静态资源、`~/.codex` JSONL、线程/历史/状态/权限、CDP 控制、本地状态 |
| `public/` | 手机控制台：线程列表、历史、运行状态、权限、模型/推理切换、发送/停止、主题与移动端键盘 |
| `launch-codex-go.sh` | 启动 / 停止 / 检查 Codex CDP 与 Python bridge（默认 `start`） |
| `docs/wiki.md` | 原理、排障、端口、公网、API、CDP；入门见 `README.md` |

## 常用命令

```bash
./launch-codex-go.sh          # 启动
./launch-codex-go.sh status   # 状态
./launch-codex-go.sh stop     # 停止
./launch-codex-go.sh restart  # 重启
```

改完 `codex_go/` 后至少跑：

```bash
python3 -m compileall codex_go
python3 tests/test_permission_status.py
python3 tests/test_composer_send_guard.py
bash -n launch-codex-go.sh
```

已用 uv 安装依赖时：

```bash
uv run python -m compileall codex_go
uv run python tests/test_permission_status.py
uv run codex-go-server
```

## 重要路径

启动脚本状态目录（默认）：

```text
~/Library/Application Support/Codex Go/CDP Worker/
```

常见文件：

- `codex-go-token` — 本地访问 token
- `codex-go-python.pid` — Python bridge 进程
- `codex-go-python.out.log` / `codex-go-python.err.log` — bridge 日志
- `main-codex-cdp.out.log` / `main-codex-cdp.err.log` — Codex CDP 启动日志

Codex 会话数据：

```text
~/.codex/session_index.jsonl
~/.codex/sessions/**/*.jsonl
```

Codex Go 本地状态默认在 `~/.codex-go/`（可通过 `Settings` / 环境变量覆盖，见 `codex_go/config.py`）。

## 修改原则

- 配置集中在 `codex_go/config.py`；其他模块通过 `Settings` 接收配置。
- API route 只做 HTTP 入出；业务放在 `services/`、`cdp/`、`codex/`。
- 改后端 API 字段时同步检查 `public/js/app.js` 的消费方。
- 改 `public/` 时：自动刷新、历史恢复、GUI 状态同步**不得**误触发发送。
- 发送链路是 **CDP DOM 控制**，不是剪贴板自动化。非中文 Codex 界面需改 `codex_go/cdp/dom.py`，见 wiki「界面语言与 CDP」。
- 改 attachments 或发送逻辑时同步看 `codex_go/services/attachments.py` 与 `tests/test_composer_send_guard.py`。
- 主题样式放在 `public/css/themes/*.css`；布局与共用组件在 `public/css/app.css`。
- 公网 / frp 文档必须写清：**只暴露 Python bridge 端口（默认 8080）**，禁止把 CDP 端口 `39443` 暴露到公网。
- 不要提交生成物（如 `*.egg-info/`、`__pycache__/`、`.venv/`）。
- 保持品牌与命名一致：**Codex Go**；不要引入已废弃的旧 env、cookie、header 或文件名。

## CDP 调试

先确认进程与端口：

```bash
./launch-codex-go.sh status
curl -fsS http://127.0.0.1:39443/json/list
```

可用 Codex target 通常满足：

- `type` 为 `page`
- `url` 以 `app://-/index.html` 开头
- 存在 `webSocketDebuggerUrl`

Bridge 健康检查：

```bash
TOKEN="$(tr -d '\r\n' < "$HOME/Library/Application Support/Codex Go/CDP Worker/codex-go-token")"
curl -fsS "http://127.0.0.1:8080/codex/cdp-health?token=$TOKEN"
```

**CDP 不可用**时按序排查：

1. `./launch-codex-go.sh status` — `39443` 与 `8080` 是否在监听。
2. Codex 已开但无 CDP → `./launch-codex-go.sh restart`。
3. `main-codex-cdp.err.log` — Electron/Chromium 启动错误。
4. `/json/list` 无 `app://-/index.html` target → 先修 Codex CDP 启动。
5. `codex-go-python.err.log` — 依赖、token、端口占用。

**CDP 已连但功能失败**时按序排查：

1. `/codex/cdp-health` 能否列出 target。
2. 只读接口：`/codex/gui-status`、`/codex/status`、`/codex/threads`。
3. 定位失败层：JSONL 读取、切线程、composer 聚焦、插文本、发送、权限、模型/推理菜单。
4. 确认 target 正常后再改 `codex_go/cdp/dom.py` 的 selector / evaluate。
5. 动过发送链路必须跑 `tests/test_composer_send_guard.py`。

## 安全边界

持有 Python bridge token 的人可读取本机 Codex 会话摘要，并通过 Desktop 执行发送、停止、切线程、切模型、处理权限等操作。**token 泄露等于遥控入口泄露。**

- 不要把 `39443` 暴露到公网。
- frp / 反向代理只转发 bridge 端口（默认 `8080`），并叠加 HTTPS、强 token 与代理认证。
