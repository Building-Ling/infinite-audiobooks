# 无限有声书 · Infinite Audiobooks

个人有声书库。上传一本有文字层的 PDF，选中文或英文，再输入要听的页码。服务器用 MiniMax Speech 2.8 Turbo 生成 MP3，保存到自己的书库，并提供可以再次打开的播放链接。

## 当前进度

- 一个个人账号。登录会话默认保留 30 天。
- 上传多本 PDF，按书选择朗读语言，并设置当前书。
- 指定起始页和结束页生成音频。只读一页时可以留空结束页。页码从 PDF 文件第 1 页起算，包含封面。
- 查看排队、生成、可播放和失败状态。失败的片段可以在原页面重试。
- PDF、MP3 和片段记录保存在服务器磁盘。已在阿里云验收网页上传、按页生成和播放，并确认应用重启后原链接仍然可播、原浏览器仍保持登录。

现阶段运行在服务器的回环地址，通过 SSH 隧道访问。跨设备续听、成品复用、正式 HTTPS 部署、Bot 点播和 OCR 见 [第一版任务清单](docs/v1-tasks.md)。

## 快速开始

需要 Python 3.10 或更新版本，以及可以调用语音合成的 MiniMax API Key。下面在项目根目录运行。

**Linux / macOS**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m bookshelf init
.venv/bin/python -m bookshelf serve --local-http
```

**Windows PowerShell**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m bookshelf init
.\.venv\Scripts\python.exe -m bookshelf serve --local-http
```

`init` 只需运行一次。它会提示设置书库密码、选择 MiniMax 区域（`cn` 或 `global`），再在终端输入 API Key。密码和 Key 输入时不回显。 [MiniMax 中国站接口](https://platform.minimax.cn/docs/api-reference/speech-t2a-http) · [MiniMax 国际站接口](https://platform.minimax.io/docs/api-reference/speech-t2a-http)

打开 `http://127.0.0.1:8766/`，用书库密码登录。上传一本能复制正文的 PDF，选语言，再试读一页。

## 在云服务器上使用

如果书库运行在远程 Linux 服务器，保持服务监听 `127.0.0.1:8766`。在自己的电脑运行下列命令，替换 SSH 用户名和服务器地址：

```bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8766:127.0.0.1:8766 user@server.example
```

保持隧道运行，用同一台电脑的浏览器打开 `http://127.0.0.1:8766/`。无需对公网开放端口 8766。`--local-http` 用于回环地址和 SSH 隧道试跑；将来如果接入 HTTPS 反向代理，启动时省略该选项，以启用安全 Cookie。

## 数据与恢复

- 默认数据目录是 `book-data/`，可用 `--data` 改位置。`init` 和 `serve` 要使用同一个数据目录。
- 数据目录包含 SQLite 数据库、源 PDF、MP3 和受限配置文件。配置里有 MiniMax Key 和会话密钥。备份数据目录时，把备份作为私密文件保存。
- 恢复时保留数据目录，重新运行 `serve`，供原播放链接和会话继续使用。应用运行一个进程，并逐个处理生成任务。

[项目范围](docs/v1-scope.md) · [实现任务](docs/v1-tasks.md) · [现有项目调研](docs/research/existing-audiobook-projects.md)
