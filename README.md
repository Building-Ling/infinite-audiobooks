# 无限有声书 · Infinite Audiobooks

无限有声书是一个个人听书库。上传 PDF 后，你可以让聊天机器人朗读指定片段，点开链接就能在手机上听。下次回来时，从上次停下的位置继续。

Infinite Audiobooks is a personal listening library for books you already have as PDFs. Upload a book, ask a bot to read part of it, and open the playback link on your phone. When you come back, pick up where you left off.

## 使用方式 · How it should work

1. **添加书籍。** 上传能选中文字的 PDF，选择中文或英文朗读，并将正在读的那本设为当前书。

   **Add a book.** Upload a PDF with selectable text to your private library, choose Chinese or English for narration, and mark the book you're currently reading.

2. **指定片段。** 给机器人发消息，比如「读 PDF 第 42–48 页」。如果 PDF 有可用的章节书签，也可以按章号请求。

   **Ask for a passage.** Message the bot with a PDF page range, such as “Read pages 42–48.” If the PDF has usable chapter bookmarks, you can ask for a chapter by number.

3. **在手机上听。** 机器人确认收到请求，音频就绪后发来需要登录的 HTTPS 播放链接。手机首次登录后，无论用家里 Wi-Fi 还是移动数据，都能在浏览器里播放。

   **Listen on your phone.** The bot acknowledges the request and sends a private HTTPS link when the audio is ready. Sign in once and play it in your mobile browser, at home or on mobile data.

4. **从上次的位置继续听。** 打开原链接，或在书库里找到同一片段，都能从已保存的位置继续。你也可以在书籍页重听或删除已保存的片段。

   **Pick up where you left off.** Open the original link or find the passage in your library. Playback resumes from your saved position. You can replay or delete saved passages from the book's page.

## 第一版设想 · The first version

第一版计划支持一个个人账号和一个聊天渠道。云服务器保存 PDF、生成的音频和听书进度，只把请求片段的文字发给 MiniMax Speech 2.8 Turbo 合成朗读。如果同一片段已用相同的音色和模型生成过，机器人就复用已有音频并返回原链接。

The plan is to support one personal account and one messaging channel. A cloud server will keep the PDFs, generated audio, and listening progress. Only the text of the requested passage will be sent to MiniMax Speech 2.8 Turbo for narration. If the same passage has already been generated with the same voice and model, the bot will reuse the saved audio and return the original link.
