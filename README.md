# Infinite Audiobooks

Infinite Audiobooks is a personal listening library for books you already have as PDFs. Upload a book, ask a bot to read part of it, and open the playback link on your phone. When you come back, pick up where you left off.

## How it should work

1. **Add a book.** Upload a PDF with selectable text to your private library, choose Chinese or English for narration, and mark the book you're currently reading.
2. **Ask for a passage.** Message the bot with a PDF page range, such as “Read pages 42–48.” If the PDF has usable chapter bookmarks, you can ask for a chapter by number.
3. **Listen on your phone.** The bot acknowledges the request and sends a private HTTPS link when the audio is ready. Sign in once and play it in your mobile browser, at home or on mobile data.
4. **Pick up where you left off.** Open the original link or find the passage in your library. Playback resumes from your saved position. You can replay or delete saved passages from the book's page.

## The first version

The plan is to support one personal account and one messaging channel. A cloud server will keep the PDFs, generated audio, and listening progress. Only the text of the requested passage will be sent to MiniMax Speech 2.8 Turbo for narration. If the same passage has already been generated with the same voice and model, the bot will reuse the saved audio and return the original link.
