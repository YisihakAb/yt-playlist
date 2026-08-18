"""
YouTube Playlist Downloader
----------------------------
A lightweight desktop app (Tkinter + yt-dlp) to download all videos
from a YouTube playlist at a chosen quality.

Build to .exe with PyInstaller (see build.bat / README.md).
"""

import os
import sys
import threading
import queue
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


APP_TITLE = "YouTube Playlist Downloader"
DEFAULT_OUTPUT = os.path.join(os.path.expanduser("~"), "Downloads", "YT_Playlist")

QUALITY_OPTIONS = {
    "Best available (video+audio)": "bestvideo+bestaudio/best",
    "2160p (4K)":                    "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
    "1440p (2K)":                    "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
    "1080p (Full HD)":               "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p (HD)":                     "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p":                          "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p":                          "bestvideo[height<=360]+bestaudio/best[height<=360]",
    "Audio only (MP3)":              "bestaudio/best",
}


class DownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("720x560")
        self.minsize(640, 480)
        self.configure(bg="#1e1e2e")

        self.output_dir = tk.StringVar(value=DEFAULT_OUTPUT)
        self.playlist_url = tk.StringVar()
        self.quality_label = tk.StringVar(value=list(QUALITY_OPTIONS.keys())[3])  # 1080p default
        self.status_text = tk.StringVar(value="Idle")
        self.overall_progress = tk.DoubleVar(value=0)

        self.entries = []          # list of dicts: {id, title, checked(BooleanVar)}
        self.log_queue = queue.Queue()
        self.download_thread = None
        self.cancel_flag = threading.Event()

        self._build_style()
        self._build_ui()
        self.after(150, self._poll_log_queue)

        if yt_dlp is None:
            messagebox.showerror(
                "Missing dependency",
                "yt-dlp is not installed.\n\nInstall it with:\n    pip install yt-dlp"
            )

    # ---------- UI construction ----------

    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        bg = "#1e1e2e"
        panel = "#282838"
        fg = "#e6e6f0"
        accent = "#7c5cff"

        style.configure("TFrame", background=bg)
        style.configure("Panel.TFrame", background=panel)
        style.configure("TLabel", background=bg, foreground=fg, font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=bg, foreground=fg, font=("Segoe UI", 16, "bold"))
        style.configure("Sub.TLabel", background=bg, foreground="#9a9ab0", font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        style.configure("Accent.TButton", background=accent, foreground="white")
        style.map("Accent.TButton", background=[("active", "#6a4be0")])
        style.configure("TEntry", padding=6)
        style.configure("TCombobox", padding=6)
        style.configure("Horizontal.TProgressbar", background=accent, troughcolor=panel)

    def _build_ui(self):
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="YouTube Playlist Downloader", style="Header.TLabel").pack(anchor="w")
        ttk.Label(root, text="Paste a playlist URL, fetch its videos, pick a quality, and download.",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 12))

        # URL row
        url_row = ttk.Frame(root)
        url_row.pack(fill="x", pady=4)
        ttk.Label(url_row, text="Playlist URL:").pack(side="left")
        url_entry = ttk.Entry(url_row, textvariable=self.playlist_url)
        url_entry.pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(url_row, text="Fetch Playlist", command=self._fetch_playlist).pack(side="left")

        # Quality + output row
        opts_row = ttk.Frame(root)
        opts_row.pack(fill="x", pady=8)
        ttk.Label(opts_row, text="Quality:").pack(side="left")
        quality_box = ttk.Combobox(opts_row, textvariable=self.quality_label,
                                    values=list(QUALITY_OPTIONS.keys()), state="readonly", width=28)
        quality_box.pack(side="left", padx=(8, 20))

        ttk.Label(opts_row, text="Save to:").pack(side="left")
        out_entry = ttk.Entry(opts_row, textvariable=self.output_dir)
        out_entry.pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(opts_row, text="Browse", command=self._browse_output).pack(side="left")

        # Video list
        list_frame = ttk.Frame(root, style="Panel.TFrame")
        list_frame.pack(fill="both", expand=True, pady=8)

        list_header = ttk.Frame(list_frame, style="Panel.TFrame")
        list_header.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Button(list_header, text="Select All", command=lambda: self._toggle_all(True)).pack(side="left")
        ttk.Button(list_header, text="Select None", command=lambda: self._toggle_all(False)).pack(side="left", padx=6)
        self.count_label = ttk.Label(list_header, text="0 videos", background="#282838")
        self.count_label.pack(side="right")

        canvas = tk.Canvas(list_frame, bg="#282838", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.list_inner = ttk.Frame(canvas, style="Panel.TFrame")

        self.list_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.list_inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scrollbar.pack(side="right", fill="y", pady=8)

        # Progress + status
        prog_frame = ttk.Frame(root)
        prog_frame.pack(fill="x", pady=(4, 8))
        self.progress_bar = ttk.Progressbar(prog_frame, variable=self.overall_progress,
                                             maximum=100, style="Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x")
        ttk.Label(prog_frame, textvariable=self.status_text, style="Sub.TLabel").pack(anchor="w", pady=(4, 0))

        # Action buttons
        action_row = ttk.Frame(root)
        action_row.pack(fill="x")
        self.download_btn = ttk.Button(action_row, text="Download Selected",
                                        style="Accent.TButton", command=self._start_download)
        self.download_btn.pack(side="left")
        self.cancel_btn = ttk.Button(action_row, text="Cancel", command=self._cancel_download, state="disabled")
        self.cancel_btn.pack(side="left", padx=8)

    # ---------- Playlist fetching ----------

    def _browse_output(self):
        path = filedialog.askdirectory(initialdir=self.output_dir.get() or os.getcwd())
        if path:
            self.output_dir.set(path)

    def _fetch_playlist(self):
        url = self.playlist_url.get().strip()
        if not url:
            messagebox.showwarning(APP_TITLE, "Please paste a playlist URL first.")
            return
        if yt_dlp is None:
            messagebox.showerror(APP_TITLE, "yt-dlp is not installed.")
            return

        self.status_text.set("Fetching playlist info...")
        threading.Thread(target=self._fetch_playlist_worker, args=(url,), daemon=True).start()

    def _fetch_playlist_worker(self, url):
        ydl_opts = {"quiet": True, "extract_flat": True, "skip_download": True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            self.log_queue.put(("error", f"Failed to fetch playlist: {e}"))
            return

        entries = info.get("entries") or [info]
        self.log_queue.put(("entries", entries))

    def _populate_entries(self, entries):
        for child in self.list_inner.winfo_children():
            child.destroy()
        self.entries = []

        for e in entries:
            if not e:
                continue
            var = tk.BooleanVar(value=True)
            title = e.get("title") or e.get("id") or "Untitled"
            video_id = e.get("id") or e.get("url")
            row = ttk.Checkbutton(self.list_inner, text=title, variable=var, style="TCheckbutton")
            row.pack(anchor="w", padx=8, pady=2, fill="x")
            self.entries.append({"id": video_id, "title": title, "var": var})

        self.count_label.config(text=f"{len(self.entries)} videos")
        self.status_text.set(f"Loaded {len(self.entries)} videos. Ready to download.")

    def _toggle_all(self, value):
        for e in self.entries:
            e["var"].set(value)

    # ---------- Downloading ----------

    def _start_download(self):
        if yt_dlp is None:
            messagebox.showerror(APP_TITLE, "yt-dlp is not installed.")
            return
        selected = [e for e in self.entries if e["var"].get()]
        if not selected:
            messagebox.showwarning(APP_TITLE, "Select at least one video to download.")
            return

        os.makedirs(self.output_dir.get(), exist_ok=True)
        self.cancel_flag.clear()
        self.download_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.overall_progress.set(0)

        self.download_thread = threading.Thread(
            target=self._download_worker, args=(selected,), daemon=True
        )
        self.download_thread.start()

    def _download_worker(self, selected):
        total = len(selected)
        fmt = QUALITY_OPTIONS[self.quality_label.get()]
        is_audio_only = "Audio only" in self.quality_label.get()

        for i, item in enumerate(selected, start=1):
            if self.cancel_flag.is_set():
                self.log_queue.put(("status", "Cancelled."))
                break

            self.log_queue.put(("status", f"Downloading {i}/{total}: {item['title']}"))

            def hook(d, idx=i, tot=total):
                if d.get("status") == "downloading":
                    pct = d.get("_percent_str", "0%").strip()
                    self.log_queue.put(("status", f"({idx}/{tot}) {item['title']} - {pct}"))
                elif d.get("status") == "finished":
                    self.log_queue.put(("progress", (idx - 1) / total * 100 + (1 / total) * 90))

            ydl_opts = {
                "format": fmt,
                "outtmpl": os.path.join(self.output_dir.get(), "%(playlist_index)s - %(title)s.%(ext)s"),
                "merge_output_format": "mp4",
                "progress_hooks": [hook],
                "quiet": True,
                "noprogress": True,
                "ignoreerrors": True,
            }
            if is_audio_only:
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]

            video_url = f"https://www.youtube.com/watch?v={item['id']}" if len(item['id']) == 11 else item['id']

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])
            except Exception as e:
                self.log_queue.put(("status", f"Error on '{item['title']}': {e}"))

            self.log_queue.put(("progress", i / total * 100))

        self.log_queue.put(("done", None))

    def _cancel_download(self):
        self.cancel_flag.set()
        self.status_text.set("Cancelling after current video...")

    # ---------- Log queue polling (keeps UI thread-safe) ----------

    def _poll_log_queue(self):
        try:
            while True:
                kind, payload = self.log_queue.get_nowait()
                if kind == "entries":
                    self._populate_entries(payload)
                elif kind == "status":
                    self.status_text.set(payload)
                elif kind == "progress":
                    self.overall_progress.set(min(payload, 100))
                elif kind == "error":
                    self.status_text.set(payload)
                    messagebox.showerror(APP_TITLE, payload)
                elif kind == "done":
                    self.status_text.set("Download complete.")
                    self.overall_progress.set(100)
                    self.download_btn.config(state="normal")
                    self.cancel_btn.config(state="disabled")
        except queue.Empty:
            pass
        self.after(150, self._poll_log_queue)


if __name__ == "__main__":
    app = DownloaderApp()
    app.mainloop()
