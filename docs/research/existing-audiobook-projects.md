# 无限有声书的现有项目调研

2026-11-21 查阅了项目官方文档、发布记录和源码。结论来自文档和源码，尚未安装或实测这些项目。

## 需求澄清后的结论

用户先上传源 PDF，外出后向机器人发送当前书的片段范围。机器人再启动电脑或服务器的 TTS，只生成指定片段，并返回手机可播放的链接。书名搜索和整本书预生成属于下文最初调研时的假设。

用户试听后认为 MiniMax Speech 2.8 Turbo 的听感可以接受，暂定为第一版默认生成模型。下一步可用其同步 API 生成书稿片段，测试手机流量能否播放返回的音频链接。该接口返回的 URL 有效期为 24 小时，适合临时试听。 [MiniMax 同步语音合成 API](https://platform.minimax.io/docs/api-reference/speech-t2a-http)

OpenReader 可在阅读器里从选定位置朗读，但其公开 REST 接口的 `chapter` 参数只组装该章已有的音频，不会启动新的 TTS。若要让机器人直接生成新片段，一个可验证的方案是先从源 PDF 提取指定范围，再把这段文字独立交给 TTS。Audiobookshelf 仍可用于成品播放，但不负责解析请求和启动合成。 [OpenReader 阅读器](https://docs.openreader.richardr.dev/guide/reading-and-listening/) · [OpenReader 公开 API](https://docs.openreader.richardr.dev/reference/public-api/#audiobooks) · [Audiobookshelf 分享](https://audiobookshelf.org/docs/documentation/libraries/common-content/public-shares/)

## 最接近的两条路线

**自托管 OpenReader 最接近单项目方案。** 它能上传 PDF、使用本地 Kokoro 合成、边生成边播放、缓存朗读音频，并导出 MP3 或 M4B。它还有现成的 MCP 和 REST 接口。如果现有机器人支持 MCP，可直接用 `docs list --search <书名>` 和 `docs view <文档>` 找到文档并回复其 `webUrl`，接入后有望省去自写机器人适配器。REST 的搜索按文件名做不区分大小写的子串匹配，文件名需要能对应书名。手机打开 `webUrl` 会进入阅读器，可从那里听读。访问受账户权限约束，`webDownloadUrl` 则用于下载音频。仅安装 Windows 桌面版时，服务只监听本机回环地址，桌面库不会与 iPhone 应用共享。跨设备使用应选自托管服务，托管型 MCP 客户端还需要可访问的公网 HTTPS 地址。官方桌面文档所列的内置本地 Kokoro 语音未列普通话，若朗读中文，应验证所部署版本的语音列表，或配置支持普通话的 TTS 后端。 [项目功能](https://github.com/richardr1126/openreader#-features) · [REST API](https://docs.openreader.richardr.dev/reference/public-api/#documents) · [MCP 接入](https://docs.openreader.richardr.dev/reference/mcp/) · [桌面版](https://docs.openreader.richardr.dev/desktop-app/)

**ebook2audiobook + Audiobookshelf 最贴近独立播放链接和专用有声书库。** ebook2audiobook 支持在 Windows 上用 Gradio 上传或用 CLI 批量处理 PDF，通过本地 TTS 生成 MP3 或 M4B。仓库列出 CPU 和多种 GPU 路径，也列出针对图片页的 OCR，实际效果需用自己的源 PDF 验证。官方发布已加入 Audiobookshelf 上传。当前源码在无界面转换完成后可以上传，具体参数以安装版本为准，入库成功可用书库搜索验证。ebook2audiobook 的 `--share` 参数公开的是 Gradio 转换界面。 [转换功能及 CLI](https://github.com/DrewThomasson/ebook2audiobook#basic-usage) · [Audiobookshelf 上传发布记录](https://github.com/DrewThomasson/ebook2audiobook/releases/tag/v26.7.27) · [转换及上传源码](https://github.com/DrewThomasson/ebook2audiobook/blob/main/lib/core.py)

Audiobookshelf 提供网页播放器、按账号同步进度及安卓与 iOS 客户端。给已登录的自己发链接时，机器人可通过书库搜索 API 取到条目 ID，回复对应书籍页 `/item/<id>`，在手机上点播放。需要免登录时，Audiobookshelf 已提供可设置有效期的逐书 `/share/<slug>` 播放链接。分享可以在管理界面创建，当前源码也提供了管理员创建接口。任何能访问服务器且拿到此链接的人都可播放，分享播放进度只保存在客户端，且直接播放依赖手机浏览器支持文件编码。外出时，手机需要能访问自托管服务器，Audiobookshelf 文档给出的方式包括 VPN 和反向代理。 [播放器与进度](https://audiobookshelf.org/docs/documentation/introduction/) · [书库搜索 API](https://api.audiobookshelf.org/#search-a-library) · [书籍页源码](https://github.com/advplyr/audiobookshelf/blob/master/client/pages/item/_id/index.vue) · [逐书分享文档](https://audiobookshelf.org/docs/documentation/libraries/common-content/public-shares/) · [创建分享的源码](https://raw.githubusercontent.com/advplyr/audiobookshelf/master/server/controllers/ShareController.js) · [远程访问](https://audiobookshelf.org/docs/faq/server/#why-do-i-need-to-set-up-my-own-remote-access)

## 其他可复用项目

| 项目 | 能复用的部分 | 与目标的差距 |
| --- | --- | --- |
| AudioBookForge | 自托管上传、生成带章节的 M4B、手机浏览器跟读和进度。官方提供常开书库服务器与 Windows GPU 电脑分开部署、生成后自动发布的方案。 | PDF 需要文字层，内置样例音色为美式和英式英语。所查说明未见按书名回复播放链接的机器人。 [项目和部署文档](https://github.com/kmmarin/AudioBookForge#features) |
| Abogen | Windows 图形界面，用本地 Kokoro 把 PDF 生成朗读音频，可用 CPU 或 NVIDIA GPU，文档列有普通话依赖。 | 适合作为转换器候选，手机播放器与机器人需另接。 [项目文档](https://github.com/denizsafak/abogen#readme) |
| Bookshelf-Traveller | 可自托管的 Audiobookshelf Discord 机器人，`/search-book` 按书名搜索并支持自动补全。 | 文档说明的播放走 Discord 语音频道，未查到它回复能在手机浏览器直接播放的书籍链接。 [命令文档](https://github.com/donkevlar/Bookshelf-Traveller#readme) |

## 首轮验证

如果手机登录后在阅读器里点播放就够用，先试自托管 OpenReader 加现有 MCP 助手。若需要免登录逐书播放链接，或希望有独立书库和跨设备续听，先试 ebook2audiobook 加 Audiobookshelf。固定使用某个聊天平台时，再看平台上的现有机器人能否调用 MCP 或通过 API 返回链接。

用一本有文字层的常见源 PDF 走通上传、电脑本地生成、按书名查找和手机播放。若已有扫描版 PDF、中文书或外出用手机的需求，再分别验证 OCR、普通话朗读，以及手机切换到移动数据后链接能否打开。这样可以先确认整条链路，再决定机器人是否需要额外接入。
