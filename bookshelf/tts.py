import json
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from imageio_ffmpeg import get_ffmpeg_exe
from pypdf import PdfReader


ENDPOINTS = {
    "cn": "https://api.minimax.cn/v1/t2a_v2",
    "global": "https://api.minimax.io/v1/t2a_v2",
}
VOICES = {
    "zh": ("Chinese", "male-qn-qingse"),
    "en": ("English", "English_expressive_narrator"),
}
BOUNDARIES = re.compile(r"\n+|[。！？；]|[.!?;](?=\s)|\s+")


class GenerationError(Exception):
    pass


def chunks(text, limit=3000):
    while len(text) > limit:
        window = text[:limit]
        matches = list(BOUNDARIES.finditer(window, limit // 2))
        cut = matches[-1].end() if matches else limit
        yield text[:cut].strip()
        text = text[cut:].lstrip()
    if text:
        yield text


def request_audio(text, lang, region, key):
    language, voice = VOICES[lang]
    request = Request(
        ENDPOINTS[region],
        data=json.dumps({
            "model": "speech-2.8-turbo",
            "text": text,
            "stream": False,
            "output_format": "hex",
            "language_boost": language,
            "voice_setting": {"voice_id": voice, "speed": 1},
            "audio_setting": {"format": "mp3", "sample_rate": 32000, "bitrate": 128000, "channel": 1},
        }, ensure_ascii=False).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            data = json.load(response)
        code = data["base_resp"]["status_code"]
        if code != 0:
            hint = "，请检查 API 余额和密钥" if str(code) in {"1004", "1008", "2049"} else ""
            raise GenerationError(f"MiniMax 拒绝请求（{code}）{hint}。")
        audio = bytes.fromhex(data["data"]["audio"])
        if not audio:
            raise ValueError("empty audio")
        return audio
    except HTTPError as exc:
        raise GenerationError(f"MiniMax 返回 HTTP {exc.code}。请检查 API 设置后重试。") from None
    except (URLError, TimeoutError):
        raise GenerationError("连接 MiniMax 失败或超时，请稍后重试。") from None
    except (KeyError, TypeError, ValueError):
        raise GenerationError("MiniMax 没有返回有效音频。") from None


def generate(pdf, first, last, lang, output, *, region, key):
    with pdf.open("rb") as source:
        reader = PdfReader(source)
        texts = [reader.pages[index].extract_text().strip() for index in range(first - 1, last)]
    text = "\n\n".join(filter(None, texts))
    if not text:
        raise GenerationError("所选页没有可提取的文字。请换一个范围或使用有文字层的 PDF。")

    parts = list(chunks(text))
    ffmpeg = get_ffmpeg_exe() if len(parts) > 1 else None
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        folder = Path(temp)
        result = folder / "result.mp3"
        if ffmpeg is None:
            result.write_bytes(request_audio(parts[0], lang, region, key))
        else:
            filenames = []
            for index, part in enumerate(parts):
                name = f"part-{index}.mp3"
                (folder / name).write_bytes(request_audio(part, lang, region, key))
                filenames.append(name)
            (folder / "parts.txt").write_text("".join(f"file '{name}'\n" for name in filenames), encoding="ascii")
            process = subprocess.run(
                [ffmpeg, "-nostdin", "-v", "error", "-xerror", "-f", "concat", "-safe", "1",
                 "-i", "parts.txt", "-c:a", "copy", "result.mp3"],
                cwd=folder, capture_output=True, timeout=120,
            )
            if process.returncode or not result.is_file() or not result.stat().st_size:
                raise GenerationError("合并音频失败，请重试。")
        result.replace(output)
