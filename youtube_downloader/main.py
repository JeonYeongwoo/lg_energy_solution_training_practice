"""한국어 YouTube 다운로더. Python 3.10 이상."""
import re
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yt_dlp
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QAbstractItemView, QHeaderView,
)


def single_video_url(value):
    """재생목록 파라미터를 제거하고 단일 영상 주소만 허용한다."""
    parsed = urlparse(value.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("http", "https") or host not in (
        "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com",
        "youtu.be", "www.youtu.be",
    ):
        raise ValueError("올바른 유튜브 영상 링크를 입력해 주세요.")
    if host.endswith("youtu.be"):
        video_id = parsed.path.strip("/").split("/")[0]
    elif parsed.path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [""])[0]
    else:
        match = re.fullmatch(r"/(?:shorts|live|embed)/([\w-]+)/?", parsed.path)
        video_id = match.group(1) if match else ""
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("단일 영상을 특정할 수 없습니다. 영상의 공유 링크를 입력해 주세요.")
    return "https://www.youtube.com/watch?v=" + video_id


def human_size(size):
    if not size:
        return "알 수 없음"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024


def duration_text(seconds):
    if seconds is None:
        return "알 수 없음"
    seconds = max(0, int(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"


def format_kind(fmt):
    video = fmt.get("vcodec", "none") != "none"
    audio = fmt.get("acodec", "none") != "none"
    return "영상+음원" if video and audio else "영상 전용" if video else "음원 전용"


def friendly_error(error):
    message = re.sub(r"\x1b\[[0-9;]*m", "", str(error))
    lower = message.lower()
    if any(word in lower for word in ("private", "sign in", "login", "age", "members", "403", "restricted")):
        return "인증이 필요하거나 접근이 제한된 영상입니다. 이 앱은 접근 제한을 우회하지 않습니다."
    if any(word in lower for word in ("unavailable", "removed", "not available", "404")):
        return "삭제되었거나 현재 접근할 수 없는 영상입니다."
    if any(word in lower for word in ("timed out", "connection", "network", "resolve", "unable to download webpage")):
        return "네트워크 연결을 확인한 뒤 다시 시도해 주세요.\n" + message[:500]
    if isinstance(error, OSError):
        return "저장 폴더의 권한, 남은 공간과 파일 사용 여부를 확인해 주세요.\n" + message[:500]
    return "작업을 완료하지 못했습니다. 링크와 네트워크를 확인해 주세요.\n" + message[:700]


class QuietLogger:
    def debug(self, message):
        pass

    def warning(self, message):
        pass

    def error(self, message):
        pass


class Worker(QThread):
    analyzed = pyqtSignal(dict)
    progress = pyqtSignal(int, str)
    completed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, url, folder=None, fmt=None):
        super().__init__()
        self.url, self.folder, self.fmt = url, folder, fmt

    def download_hook(self, data):
        if data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            downloaded = data.get("downloaded_bytes", 0)
            percent = min(100, int(downloaded * 100 / total)) if total else -1
            speed = human_size(data.get("speed")) + "/초" if data.get("speed") else "계산 중"
            eta = duration_text(data.get("eta")) if data.get("eta") is not None else "계산 중"
            name = Path(data.get("filename", "")).name
            self.progress.emit(percent, f"다운로드 중: {name}\n속도: {speed} · 남은 시간: {eta}")
        elif data.get("status") == "finished":
            self.progress.emit(-1, "파일 다운로드 종료 · 후처리 또는 다음 파일 준비 중…")

    def postprocess_hook(self, data):
        self.progress.emit(-1, "후처리·병합 중…" if data.get("status") != "finished" else "후처리 결과 확인 중…")

    def run(self):
        try:
            options = {"noplaylist": True, "quiet": True, "no_warnings": True,
                       "logger": QuietLogger(), "socket_timeout": 30, "retries": 3}
            if self.fmt is None:
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(self.url, download=False)
                if not info or info.get("_type") in ("playlist", "multi_video"):
                    raise ValueError("단일 영상을 특정할 수 없습니다. 영상 공유 링크를 사용해 주세요.")
                if info.get("is_live"):
                    raise ValueError("진행 중인 실시간 방송은 지원하지 않습니다. 방송 종료 후 다시 시도해 주세요.")
                self.analyzed.emit(info)
                return
            folder = Path(self.folder)
            if not folder.is_dir():
                raise OSError("선택한 폴더가 존재하지 않습니다.")
            with tempfile.TemporaryFile(dir=str(folder)):
                pass
            video_only = format_kind(self.fmt) == "영상 전용"
            needs_ffmpeg = video_only or self.fmt.get("protocol") == "m3u8" or self.fmt.get("ext") == "m3u8"
            if needs_ffmpeg and not shutil.which("ffmpeg"):
                raise ValueError("이 포맷에는 FFmpeg가 필요합니다. FFmpeg를 설치하고 PATH에 추가한 뒤 앱을 다시 실행해 주세요. README의 설치 안내를 확인하세요.")
            selected = self.fmt["format_id"]
            if video_only:
                selected += "+bestaudio"
            options.update({"format": selected, "outtmpl": str(folder / "%(title).180B [%(id)s].%(ext)s"),
                            "windowsfilenames": True, "progress_hooks": [self.download_hook],
                            "postprocessor_hooks": [self.postprocess_hook]})
            if video_only:
                options["merge_output_format"] = "mkv"
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.extract_info(self.url, download=True)
            self.completed.emit(str(folder))
        except Exception as error:
            self.failed.emit(str(error) if isinstance(error, ValueError) else friendly_error(error))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🐱 냥튜브 · 유튜브 다운로더")
        self.resize(940, 780)
        self.setMinimumSize(780, 680)
        self.setStyleSheet("""
            QWidget { font-family: 'Malgun Gothic', 'Segoe UI Emoji';
                font-size: 13px; color: #574752; }
            QMainWindow, QWidget#canvas { background: #fff9f3; }
            QLabel { background: transparent; }
            QLabel#title { font-size: 28px; font-weight: bold; color: #69485b; }
            QLabel#subtitle { color: #987989; font-size: 13px; }
            QLabel#section { font-weight: bold; color: #795569; }
            QLabel#details { background: #fff0f4; border: 1px solid #f1dbe3;
                border-radius: 14px; padding: 14px; }
            QLabel#notice { color: #937780; font-size: 12px; padding: 5px; }
            QLabel#status { color: #856476; padding: 4px; }
            QLineEdit { background: #ffffff; border: 1px solid #ead8df;
                border-radius: 12px; padding: 11px 14px; selection-background-color: #f3b6ca; }
            QLineEdit:focus { border: 2px solid #e99bb6; }
            QLineEdit:read-only { background: #fff5f7; color: #8a7480; }
            QPushButton { background: #fce7ee; border: 1px solid #efcbd8;
                border-radius: 12px; padding: 11px 20px; font-weight: bold; }
            QPushButton:hover { background: #f8d4e0; border-color: #eaa7bf; }
            QPushButton:pressed { background: #efb8cd; }
            QPushButton#download { background: #df88a8; color: white;
                border: 1px solid #df88a8; font-size: 15px; padding: 14px; }
            QPushButton#download:hover { background: #d57497; }
            QPushButton:disabled, QPushButton#download:disabled {
                background: #eee5e8; color: #b6a7ae; border-color: #e5dce0; }
            QTableWidget { background: #ffffff; alternate-background-color: #fff7fa;
                border: 1px solid #eddae2; border-radius: 12px;
                gridline-color: #f5e7ed; selection-background-color: #f9d8e5;
                selection-color: #69485b; padding: 5px; outline: none; }
            QHeaderView::section { background: #fcebf1; color: #805e70;
                border: none; border-bottom: 1px solid #eddae2; padding: 10px 6px;
                font-weight: bold; }
            QTableWidget::item { padding: 7px; border: none; }
            QProgressBar { background: #f1e5e9; border: none; border-radius: 9px;
                text-align: center; color: #69485b; min-height: 18px; }
            QProgressBar::chunk { background: #e9a3bc; border-radius: 9px; }
            QScrollBar:vertical { background: #fff5f8; width: 12px; margin: 0; }
            QScrollBar::handle:vertical { background: #ebc5d3; border-radius: 6px;
                min-height: 28px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        self.worker = None
        self.formats = []
        self.analyzed_url = None
        container = QWidget()
        container.setObjectName("canvas")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 22)
        layout.setSpacing(12)
        title = QLabel("🐱 냥튜브")
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel("마음에 드는 영상을 차곡차곡 모아보라냥 🐾")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        link_label = QLabel("🐾 01. 유튜브 영상 링크")
        link_label.setObjectName("section")
        layout.addWidget(link_label)
        self.url = QLineEdit()
        self.url.setPlaceholderText("https://www.youtube.com/watch?v=…")
        layout.addWidget(self.url)
        folder_label = QLabel("📁 저장할 폴더")
        folder_label.setObjectName("section")
        layout.addWidget(folder_label)
        row = QHBoxLayout()
        self.folder = QLineEdit(str(Path.home() / "Downloads"))
        self.folder.setReadOnly(True)
        self.choose = QPushButton("📁 폴더 선택")
        row.addWidget(self.folder)
        row.addWidget(self.choose)
        layout.addLayout(row)
        self.analyze = QPushButton("😺 영상 분석하기")
        layout.addWidget(self.analyze)
        self.details = QLabel("😸 링크를 넣고 영상 분석하기를 눌러주세요. 고양이가 기다리고 있어요!")
        self.details.setObjectName("details")
        self.details.setWordWrap(True)
        layout.addWidget(self.details)
        format_label = QLabel("🐾 02. 원하는 포맷을 골라주세요")
        format_label.setObjectName("section")
        layout.addWidget(format_label)
        self.table = QTableWidget(0, 5)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setMinimumHeight(150)
        self.table.setHorizontalHeaderLabels(["포맷 ID", "종류", "확장자", "해상도 / 음원 비트레이트", "파일 크기"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table, 1)
        self.notice = QLabel("영상 전용 선택 시 음원을 함께 다운로드하여 MKV로 병합합니다(FFmpeg 필요).\n음원 전용은 원래 포맷으로 저장하며 MP3로 변환하지 않습니다.")
        self.notice.setObjectName("notice")
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)
        self.download = QPushButton("🐾 내 폴더에 다운로드")
        self.download.setObjectName("download")
        self.download.setEnabled(False)
        layout.addWidget(self.download)
        self.bar = QProgressBar()
        self.bar.setValue(0)
        layout.addWidget(self.bar)
        self.status = QLabel("🐱 준비 완료 · 영상을 모아볼까요?")
        self.status.setObjectName("status")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.setCentralWidget(container)
        self.choose.clicked.connect(self.choose_folder)
        self.analyze.clicked.connect(self.start_analysis)
        self.download.clicked.connect(self.start_download)
        self.url.textChanged.connect(self.reset_analysis)
        self.table.itemSelectionChanged.connect(self.update_buttons)

    def busy(self):
        return self.worker is not None

    def update_buttons(self):
        busy = self.busy()
        for widget in (self.url, self.choose, self.analyze, self.table):
            widget.setEnabled(not busy)
        self.download.setEnabled(not busy and self.analyzed_url is not None and self.table.currentRow() >= 0)

    def reset_analysis(self):
        self.analyzed_url = None
        self.formats = []
        self.table.setRowCount(0)
        self.details.setText("😸 링크를 넣고 영상 분석하기를 눌러주세요. 고양이가 기다리고 있어요!")
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.status.setText("🐱 준비 완료 · 영상을 모아볼까요?")
        self.update_buttons()

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "다운로드 폴더 선택", self.folder.text())
        if folder:
            self.folder.setText(folder)

    def launch(self, worker):
        self.worker = worker
        worker.analyzed.connect(self.show_analysis)
        worker.progress.connect(self.show_progress)
        worker.completed.connect(self.show_completed)
        worker.failed.connect(self.show_error)
        worker.finished.connect(self.worker_finished)
        self.update_buttons()
        worker.start()

    def start_analysis(self):
        if self.busy():
            return
        try:
            url = single_video_url(self.url.text())
        except ValueError as error:
            self.show_error(str(error))
            return
        self.reset_analysis()
        self.status.setText("🐱 영상 정보와 포맷을 살펴보는 중…")
        self.bar.setRange(0, 0)
        self.launch(Worker(url))

    def show_analysis(self, info):
        self.analyzed_url = self.worker.url
        self.details.setText(f"제목: {info.get('title', '제목 없음')}\n길이: {duration_text(info.get('duration'))}")
        self.formats = [fmt for fmt in info.get("formats", [])
                        if fmt.get("format_id") and not fmt.get("has_drm")
                        and (fmt.get("vcodec", "none") != "none" or fmt.get("acodec", "none") != "none")]
        self.table.setRowCount(len(self.formats))
        for row, fmt in enumerate(self.formats):
            quality = fmt.get("resolution") or (f"{fmt['height']}p" if fmt.get("height") else "알 수 없음")
            if format_kind(fmt) == "음원 전용":
                quality = f"{fmt['abr']:.0f} kbps" if fmt.get("abr") else "비트레이트 알 수 없음"
            size = "정확: " + human_size(fmt["filesize"]) if fmt.get("filesize") else "예상: " + human_size(fmt["filesize_approx"]) if fmt.get("filesize_approx") else "알 수 없음"
            for column, value in enumerate((fmt["format_id"], format_kind(fmt), fmt.get("ext", "알 수 없음"), quality, size)):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, column, item)
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.status.setText("😺 분석 완료 · 원하는 포맷을 선택해 주세요." if self.formats else "다운로드 가능한 포맷이 없습니다.")

    def start_download(self):
        row = self.table.currentRow()
        if self.busy() or row < 0 or not self.analyzed_url:
            return
        self.bar.setRange(0, 0)
        self.status.setText("🐾 다운로드 준비 중…")
        self.launch(Worker(self.analyzed_url, self.folder.text(), dict(self.formats[row])))

    def show_progress(self, percent, message):
        self.bar.setRange(0, 0 if percent < 0 else 100)
        if percent >= 0:
            self.bar.setValue(percent)
        self.status.setText(message)

    def show_completed(self, folder):
        self.bar.setRange(0, 100)
        self.bar.setValue(100)
        self.status.setText("😻 다운로드 및 후처리 완료! · 저장 폴더: " + folder)

    def show_error(self, message):
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.status.setText("😿 작업을 완료하지 못했어요. 안내를 확인해 주세요.")
        QMessageBox.warning(self, "작업 안내", message)

    def worker_finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.update_buttons()

    def closeEvent(self, event):
        if self.busy():
            QMessageBox.information(self, "작업 진행 중", "작업이 끝난 뒤 앱을 종료해 주세요.")
            event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
