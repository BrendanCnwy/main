from __future__ import annotations

import re
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import pyttsx3
from PyPDF2 import PdfReader


class PDFReaderTTSApp:
    """Read PDF content aloud with playback controls and a graphical interface."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PDF Reader with Text-to-Speech")
        self.root.geometry("980x720")
        self.root.minsize(860, 620)

        # The speech engine is initialized once and reused for all playback.
        self.engine = pyttsx3.init()
        self.style = ttk.Style()

        # Playback state is stored here so pause, stop, resume, and seeking all
        # work against the same source of truth.
        self.pdf_path: str | None = None
        self.full_text = ""
        self.text_chunks: list[str] = []
        self.current_index = 0
        self.is_speaking = False
        self.is_paused = False
        self.stop_requested = False
        self.seek_requested = False
        self.playback_thread: threading.Thread | None = None
        self.voice_map: dict[str, str] = {}

        # UI-bound state variables.
        self.status_var = tk.StringVar(value="Load a PDF to begin.")
        self.current_file_var = tk.StringVar(value="Current File: None")
        self.page_count_var = tk.StringVar(value="Pages: 0")
        self.position_var = tk.StringVar(value="Position: 0 / 0")
        self.elapsed_var = tk.StringVar(value="Elapsed: 00:00")
        self.remaining_var = tk.StringVar(value="Remaining: 00:00")
        self.voice_var = tk.StringVar()
        self.theme_var = tk.StringVar(value="Light")
        self.rate_var = tk.IntVar(value=170)
        self.volume_var = tk.DoubleVar(value=1.0)
        self.progress_var = tk.DoubleVar(value=1)

        self._build_ui()
        self._load_voices()
        self._apply_theme()

    def _build_ui(self) -> None:
        """Create the full graphical layout for file loading and playback."""
        main = ttk.Frame(self.root, padding=14)
        main.pack(fill="both", expand=True)

        ttk.Label(
            main,
            text="PDF Reader with Text-to-Speech",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="center", pady=(0, 12))

        toolbar = ttk.Frame(main)
        toolbar.pack(fill="x", pady=(0, 10))

        ttk.Button(toolbar, text="Load PDF", command=self.load_pdf).pack(side="left", padx=(0, 8))
        ttk.Button(toolbar, text="Play / Resume", command=self.play_or_resume).pack(side="left", padx=(0, 8))
        ttk.Button(toolbar, text="Pause", command=self.pause_playback).pack(side="left", padx=(0, 8))
        ttk.Button(toolbar, text="Stop", command=self.stop_playback).pack(side="left")

        info_frame = ttk.LabelFrame(main, text="File Information", padding=10)
        info_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(info_frame, textvariable=self.current_file_var).grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(info_frame, textvariable=self.page_count_var).grid(row=0, column=1, sticky="w", padx=(0, 12))
        ttk.Label(info_frame, textvariable=self.position_var).grid(row=0, column=2, sticky="w")

        controls = ttk.LabelFrame(main, text="Playback Options", padding=10)
        controls.pack(fill="x", pady=(0, 10))

        ttk.Label(controls, text="Voice:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
        self.voice_combo = ttk.Combobox(controls, textvariable=self.voice_var, state="readonly", width=28)
        self.voice_combo.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=4)

        ttk.Label(controls, text="Rate:").grid(row=0, column=2, sticky="w", padx=(0, 6), pady=4)
        ttk.Scale(controls, from_=120, to=240, variable=self.rate_var, orient="horizontal").grid(
            row=0, column=3, sticky="ew", padx=(0, 12), pady=4
        )

        ttk.Label(controls, text="Volume:").grid(row=0, column=4, sticky="w", padx=(0, 6), pady=4)
        ttk.Scale(controls, from_=0.2, to=1.0, variable=self.volume_var, orient="horizontal").grid(
            row=0, column=5, sticky="ew", padx=(0, 12), pady=4
        )

        ttk.Label(controls, text="Theme:").grid(row=0, column=6, sticky="w", padx=(0, 6), pady=4)
        theme_combo = ttk.Combobox(
            controls,
            textvariable=self.theme_var,
            values=["Light", "Dark"],
            state="readonly",
            width=10,
        )
        theme_combo.grid(row=0, column=7, sticky="w", pady=4)
        theme_combo.bind("<<ComboboxSelected>>", lambda _event: self._apply_theme())

        for column in (1, 3, 5):
            controls.columnconfigure(column, weight=1)

        progress_frame = ttk.LabelFrame(main, text="Playback Progress", padding=10)
        progress_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(progress_frame, textvariable=self.elapsed_var).pack(anchor="w")
        ttk.Label(progress_frame, textvariable=self.remaining_var).pack(anchor="w", pady=(0, 6))

        self.position_scale = tk.Scale(
            progress_frame,
            from_=1,
            to=1,
            orient="horizontal",
            resolution=1,
            variable=self.progress_var,
            showvalue=False,
            command=self._update_position_preview,
        )
        self.position_scale.pack(fill="x")
        self.position_scale.bind("<ButtonRelease-1>", self._seek_to_position)

        preview_frame = ttk.LabelFrame(main, text="Extracted PDF Text", padding=10)
        preview_frame.pack(fill="both", expand=True)

        self.preview = ScrolledText(preview_frame, wrap="word", font=("Segoe UI", 10), height=18)
        self.preview.pack(fill="both", expand=True)
        self.preview.insert("1.0", "Use the Load PDF button to choose a PDF file for playback.")

        ttk.Label(main, textvariable=self.status_var, foreground="blue").pack(anchor="w", pady=(8, 0))

    def _load_voices(self) -> None:
        """Populate the voice dropdown with all system voices from pyttsx3."""
        voices = self.engine.getProperty("voices")
        voice_names = []

        for voice in voices:
            name = getattr(voice, "name", "Unknown Voice")
            voice_names.append(name)
            self.voice_map[name] = voice.id

        if voice_names:
            self.voice_combo["values"] = voice_names
            self.voice_combo.current(0)
            self.voice_var.set(voice_names[0])

    def _apply_theme(self) -> None:
        """Switch between a light and dark visual theme for the interface."""
        dark_mode = self.theme_var.get() == "Dark"
        bg = "#202124" if dark_mode else "#f5f6fa"
        fg = "#f5f5f5" if dark_mode else "#111111"
        input_bg = "#2d2f34" if dark_mode else "#ffffff"

        self.style.theme_use("clam")
        self.root.configure(bg=bg)
        self.style.configure("TFrame", background=bg)
        self.style.configure("TLabelframe", background=bg, foreground=fg)
        self.style.configure("TLabelframe.Label", background=bg, foreground=fg)
        self.style.configure("TLabel", background=bg, foreground=fg)
        self.style.configure("TButton", padding=6)
        self.style.configure("TCombobox", fieldbackground=input_bg)

        self.preview.configure(bg=input_bg, fg=fg, insertbackground=fg)
        self.position_scale.configure(bg=bg, fg=fg, highlightthickness=0, troughcolor="#7f8c8d")

    def load_pdf(self) -> None:
        """Open a file dialog and load the selected PDF into the reader."""
        file_path = filedialog.askopenfilename(
            title="Select a PDF file",
            filetypes=[("PDF Files", "*.pdf")],
        )
        if not file_path:
            return

        self._stop_engine(reset_position=True)
        self._load_pdf_from_path(file_path)

    def _load_pdf_from_path(self, file_path: str) -> None:
        """Extract readable text from a PDF and prepare it for playback."""
        try:
            reader = PdfReader(file_path)
            extracted_pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n\n".join(page.strip() for page in extracted_pages if page.strip())

            if not text:
                raise ValueError("The selected PDF does not contain readable text.")

            self.pdf_path = file_path
            self.full_text = text
            self.text_chunks = self._chunk_text(text)
            self.current_index = 0

            self.current_file_var.set(f"Current File: {Path(file_path).name}")
            self.page_count_var.set(f"Pages: {len(reader.pages)}")
            self.status_var.set("PDF loaded successfully. Press Play to start reading.")

            self.position_scale.configure(to=max(1, len(self.text_chunks)))
            self.progress_var.set(1)
            self._refresh_preview(text)
            self._refresh_time_labels()
        except Exception as exc:
            messagebox.showerror("PDF Load Error", f"Unable to load the PDF.\n\n{exc}")
            self.status_var.set("Loading failed.")

    def _chunk_text(self, text: str, max_words: int = 28) -> list[str]:
        """Break the extracted PDF text into small chunks for responsive pause/resume."""
        clean_text = re.sub(r"\s+", " ", text).strip()
        if not clean_text:
            return []

        sentences = re.split(r"(?<=[.!?])\s+", clean_text)
        chunks: list[str] = []
        current_chunk: list[str] = []
        current_word_count = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_words = len(sentence.split())
            if current_chunk and current_word_count + sentence_words > max_words:
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_word_count = sentence_words
            else:
                current_chunk.append(sentence)
                current_word_count += sentence_words

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks or [clean_text]

    def _apply_voice_settings(self) -> None:
        """Push the current voice, rate, and volume settings into the engine."""
        self.engine.setProperty("rate", int(self.rate_var.get()))
        self.engine.setProperty("volume", float(self.volume_var.get()))

        selected_voice = self.voice_map.get(self.voice_var.get())
        if selected_voice:
            self.engine.setProperty("voice", selected_voice)

    def play_or_resume(self) -> None:
        """Start playback or resume it from the paused position."""
        if not self.text_chunks:
            messagebox.showwarning("No PDF Loaded", "Please load a PDF file first.")
            return

        if self.is_speaking and not self.is_paused:
            self.status_var.set("Playback is already running.")
            return

        self._apply_voice_settings()

        if self.is_paused:
            self.is_paused = False
            self.status_var.set("Playback resumed.")
            return

        self.stop_requested = False
        self.seek_requested = False
        self.is_speaking = True
        self.is_paused = False
        self.status_var.set("Reading PDF aloud...")

        self.playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
        self.playback_thread.start()

    def _playback_worker(self) -> None:
        """Read the prepared text chunks aloud while honoring pause, stop, and seek."""
        while self.current_index < len(self.text_chunks) and not self.stop_requested:
            while self.is_paused and not self.stop_requested:
                time.sleep(0.1)

            if self.stop_requested:
                break

            current_text = self.text_chunks[self.current_index]
            self.root.after(0, self._refresh_time_labels)
            self.engine.say(current_text)
            self.engine.runAndWait()

            if self.stop_requested:
                break

            if self.is_paused or self.seek_requested:
                self.seek_requested = False
                continue

            self.current_index += 1
            self.root.after(0, self._refresh_time_labels)

        self.is_speaking = False

        if not self.stop_requested and self.current_index >= len(self.text_chunks):
            self.root.after(0, lambda: self.status_var.set("Playback complete."))
            self.current_index = len(self.text_chunks)
            self.root.after(0, self._refresh_time_labels)

    def pause_playback(self) -> None:
        """Pause the active playback and keep the current position for resume."""
        if not self.is_speaking:
            self.status_var.set("Nothing is currently playing.")
            return

        self.is_paused = True
        self.engine.stop()
        self.status_var.set("Playback paused.")

    def stop_playback(self) -> None:
        """Stop playback and reset progress so another file can be loaded."""
        self._stop_engine(reset_position=True)
        self.status_var.set("Playback stopped. You can load another PDF.")

    def _stop_engine(self, reset_position: bool) -> None:
        """Shared stop logic used by both the Stop button and file reloading."""
        self.stop_requested = True
        self.is_paused = False

        try:
            self.engine.stop()
        except Exception:
            pass

        self.is_speaking = False
        self.seek_requested = False

        if reset_position:
            self.current_index = 0
            self.progress_var.set(1)
            self._refresh_time_labels()

        self.stop_requested = False

    def _update_position_preview(self, _value: str) -> None:
        """Refresh the preview label while the user drags the playback slider."""
        if not self.text_chunks:
            self.position_var.set("Position: 0 / 0")
            return

        selected = int(round(self.progress_var.get()))
        self.position_var.set(f"Position: {selected} / {len(self.text_chunks)}")

    def _seek_to_position(self, _event: tk.Event) -> None:
        """Jump forward or backward in the prepared speech chunks."""
        if not self.text_chunks:
            return

        new_position = int(round(self.progress_var.get())) - 1
        new_position = max(0, min(new_position, len(self.text_chunks) - 1))
        self.current_index = new_position
        self.seek_requested = True
        self._refresh_time_labels()

        if self.is_speaking:
            self.engine.stop()
            self.status_var.set("Jumped to a new playback position.")

    def _refresh_preview(self, text: str) -> None:
        """Show extracted PDF text in the scrolling preview area."""
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)

    def _refresh_time_labels(self) -> None:
        """Estimate elapsed and remaining time from chunk position and speech rate."""
        total = len(self.text_chunks)
        shown_position = min(self.current_index + 1, total) if total else 0
        self.position_var.set(f"Position: {shown_position} / {total}")
        self.progress_var.set(shown_position if shown_position else 1)

        if not self.text_chunks:
            self.elapsed_var.set("Elapsed: 00:00")
            self.remaining_var.set("Remaining: 00:00")
            return

        words_per_minute = max(int(self.rate_var.get()), 1)
        elapsed_words = sum(len(chunk.split()) for chunk in self.text_chunks[: self.current_index])
        remaining_words = sum(len(chunk.split()) for chunk in self.text_chunks[self.current_index :])

        self.elapsed_var.set(f"Elapsed: {self._format_seconds(elapsed_words / words_per_minute * 60)}")
        self.remaining_var.set(f"Remaining: {self._format_seconds(remaining_words / words_per_minute * 60)}")

    @staticmethod
    def _format_seconds(seconds: float) -> str:
        """Convert a time value in seconds to a mm:ss display string."""
        total_seconds = max(0, int(seconds))
        minutes, secs = divmod(total_seconds, 60)
        return f"{minutes:02d}:{secs:02d}"


def main() -> None:
    root = tk.Tk()
    PDFReaderTTSApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
