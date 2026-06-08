# Codex Go

> Control Codex Desktop on your Mac from a phone browser — translate this doc with AI; for a non-Chinese Codex UI, have AI update `codex_go/cdp/dom.py` too.

用手机浏览器，遥控 Mac 上的 Codex Desktop。

你在手机上发消息、切换线程、看历史和运行进度、处理权限、停止回复；Codex 仍在 Mac 本机跑任务。Codex Go 不是云端聊天，也不会代替 Codex 去调模型——它只是把 Codex Desktop 的控制台「搬」到手机浏览器里。

**用法前提：** 手机和 Mac 连同一个 Wi‑Fi。外网/龙虾用法见后文frp。

## 截图

- 等个有缘人帮我补充

## 准备

开始前确认这些都有：


| 项目            | 说明                                         |
| ------------- | ------------------------------------------ |
| Mac           | 仅支持 macOS，需要能正常打开 Codex 窗口                 |
| Codex Desktop | 已安装并登录(或已中转)，一般在 `/Applications/Codex.app` |
| Homebrew      | [brew.sh](https://brew.sh)，用来安装下面的工具       |
| 手机            | Safari、Chrome 等；与 Mac **同一 Wi‑Fi**         |


还需要把本项目克隆到 Mac 上（下面「安装」会用到 `git`）。

## 安装

**1. 安装工具**

```bash
brew install uv git
```

`uv` 用来安装 Python 依赖并启动后台；`git` 用来下载本项目。

**2. 下载项目**

```bash
git clone https://github.com/piz-ewing/Codex-Go.git
cd Codex-Go
```

**3. 安装依赖**

```bash
uv sync
```

第一次可能要等它自动下载 Python，完成后即可启动。

## 启动

在项目目录执行：

```bash
./launch-codex-go.sh
```

脚本会做这些事：

1. 检查 Codex 是否已处于可被遥控的状态；若没有，会**重启 Codex**（第一次很常见）。
2. 启动本机后台（默认端口 `8080`）。
3. 在终端打印**手机访问地址**。

示例：

```text
http://192.168.1.10:8080/?token=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Mobile URL: http://localhost:8080/?token=...
```

把带局域网 IP 的那一行**整段复制**到手机浏览器（必须包含 `?token=...`）。

token 和运行日志保存在：

```text
~/Library/Application Support/Codex Go/CDP Worker/
```

以后若要查状态或排错，可先运行 `./launch-codex-go.sh status`。

## 在手机上使用

1. 确认手机和 Mac 是**同一个 Wi‑Fi**（不要一个连 5G、一个连访客网络）。
2. 打开刚才复制的完整地址。
3. 页面加载后即可像用 Codex 一样选线程、发消息、看回复进度。
4. 可选：浏览器里「添加到主屏幕」，下次从桌面图标进入。

**局域网内**只要 URL 有效即可自用；同一 Wi‑Fi 下的其他人若也能访问你的 Mac，理论上也能打开该地址。

若打不开：先在 Mac 上 `./launch-codex-go.sh status`，并检查系统防火墙是否拦了 `8080`。

## 常用命令

在项目目录执行：


| 命令                             | 作用                              |
| ------------------------------ | ------------------------------- |
| `./launch-codex-go.sh`         | 启动（默认）                          |
| `./launch-codex-go.sh status`  | 查看 Codex、后台、端口是否正常              |
| `./launch-codex-go.sh stop`    | 停止后台和 Codex                     |
| `./launch-codex-go.sh restart` | 重启后台；Codex 已在跑时通常**不会**关掉 Codex |


## 常见问题

**终端没有打印带 IP 的地址？**
运行 `./launch-codex-go.sh status`。若 CDP 或后台未就绪，执行 `./launch-codex-go.sh restart` 后再看终端输出。

**手机提示无法连接？**
核对同一 Wi‑Fi、URL 是否完整（含 token）、Mac 防火墙是否放行 `8080`。

**401 / token 错误？**
不要用旧书签或截断的链接。重新 `./launch-codex-go.sh`，用终端**新打印**的完整 URL。

**提示 8080 端口被占用？**
先 `./launch-codex-go.sh stop`；仍冲突可换端口，例如 `PYTHON_PORT=9090 ./launch-codex-go.sh`。

**停止后如何再开？**
在项目目录再执行 `./launch-codex-go.sh` 即可。

**Codex 界面不是中文，部分按钮点不了？**
遥控依赖识别 Codex 窗口里的按钮文字。界面语言不匹配时，需要改 `codex_go/cdp/dom.py` 里的匹配规则；可把你的语言和报错现象交给 AI，让它协助改 CDP 脚本。步骤见 wiki「界面语言与 CDP」。

## 外网访问

**默认只建议在同一个 Wi‑Fi 下用。** 家里局域网够用即可，不必暴露到互联网。

若必须从外网访问：**链接里的 token 等同遥控权限**。任何拿到完整 URL 的人都可能操控你 Mac 上的 Codex，切勿分享给他人或发到群聊、论坛。frp 配置与安全事项见下方「文档」中的 wiki。

## 文档


| 文档                           | 内容                                        |
| ---------------------------- | ----------------------------------------- |
| [docs/wiki.md](docs/wiki.md) | 环境要求、工作原理、完整排障、界面语言与 CDP、修改端口、公网 frp、开发说明 |
| [AGENTS.md](AGENTS.md)       | 给贡献者与 AI 的仓库约定                            |

## 参考与感谢

- [Codex Mini](https://github.com/CoimgRain/Codex-Mini)（[CoimgRain/Codex-Mini](https://github.com/CoimgRain/Codex-Mini)）为本项目的思路与交互提供了灵感。
- [Codex++](https://github.com/b-nnett/codex-plusplus)（[b-nnett/codex-plusplus](https://github.com/b-nnett/codex-plusplus)）在 CDP 与 Codex Desktop 扩展方面提供了参考。

