# YouTube Playlist Downloader

A lightweight Windows desktop app (Python + Tkinter + yt-dlp) that downloads
every video in a YouTube playlist at a quality you choose.

## Features
- Paste a playlist URL and fetch the full video list
- Check/uncheck individual videos before downloading
- Quality dropdown: 4K down to 360p, plus an "audio only (MP3)" mode
- Progress bar + live status per video
- Dark, modern Tkinter UI (no extra GUI framework needed)
- Cancel mid-download

## 1. Run from source (for testing)

```bash
pip install -r requirements.txt
python main.py
```

You'll also need **ffmpeg** on your PATH (required by yt-dlp to merge
separate video/audio streams and to extract MP3 audio). Get it from
https://ffmpeg.org/download.html and add the `bin` folder to PATH.

## 2. Build the .exe (Windows)

Just run:

```bat
build.bat
```

This installs dependencies and runs PyInstaller with flags tuned to keep
the binary small:

- `--onefile` — single exe, no loose files
- `--windowed` — no console window behind the GUI
- `--exclude-module` for heavy libraries yt-dlp/tkinter never actually use
  (matplotlib, numpy, pandas, PIL, scipy, test/unittest)
- `--strip` — strips debug symbols
- `--optimize 2` — Python bytecode optimization

The finished exe lands in `dist\YouTubePlaylistDownloader.exe`.

### Shrinking it further with UPX (optional but recommended)

1. Download UPX: https://github.com/upx/upx/releases
2. Unzip it anywhere, e.g. `C:\upx`
3. Re-run PyInstaller with `--upx-dir "C:\upx"` added to the command in
   `build.bat`

UPX compresses the final binary, typically cutting size by 30–50% with no
effect on how the app runs (aside from a slightly slower first launch).

### Expected size
- Without UPX: roughly 25–35 MB (mostly yt-dlp + Python runtime + Tkinter)
- With UPX: roughly 15–20 MB

This is close to the practical floor for a self-contained Python GUI exe.
If you need it even smaller, the only way is to drop yt-dlp and hand-roll
the YouTube extraction logic yourself, which is not recommended — yt-dlp
is actively maintained against YouTube's frequent changes.

## 3. Notes

- **ffmpeg is not bundled** in the exe by default (it would roughly double
  the size). Ship it alongside the exe in the same folder, or instruct
  users to install it, or place a static `ffmpeg.exe` in the same
  directory as your app — yt-dlp will auto-detect it there too.
- Respect YouTube's Terms of Service and copyright law for any content
  you download. Only download videos you have the rights to save
  (e.g. your own uploads, Creative Commons content, or content you have
  explicit permission to keep offline).
