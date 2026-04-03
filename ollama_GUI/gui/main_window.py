import requests
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton, QTextEdit,
    QStackedWidget, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut

import config
from memory import load_memory, clear_memory
from utils.seen_emails import load_seen_emails
from gui.chat_widget import ChatWidget
from gui.settings_panel import SettingsPanel
from gui.worker import WorkerThread


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{config.APP_NAME} v{config.APP_VERSION}")
        self.resize(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        self.setMinimumSize(860, 540)

        self._worker = None
        self._init_backend()
        self._build_ui()
        self._check_ollama_status()

    def _init_backend(self):
        load_memory()
        load_seen_emails()
        Path(config.BASE_FOLDER).mkdir(parents=True, exist_ok=True)
        Path(config.SCREENSHOT_FOLDER).mkdir(parents=True, exist_ok=True)

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        logo = QLabel("ZENTRA")
        logo.setObjectName("logo_label")
        sidebar_layout.addWidget(logo)

        version = QLabel(f"v{config.APP_VERSION} // local ai")
        version.setObjectName("version_label")
        sidebar_layout.addWidget(version)

        sep = QFrame()
        sep.setObjectName("sidebar_separator")
        sep.setFixedHeight(1)
        sidebar_layout.addWidget(sep)

        nav_label = QLabel("NAVIGATE")
        nav_label.setObjectName("sidebar_section")
        sidebar_layout.addWidget(nav_label)

        self.btn_chat = QPushButton("  > chat")
        self.btn_chat.setObjectName("sidebar_btn")
        self.btn_chat.setCheckable(True)
        self.btn_chat.setChecked(True)
        self.btn_chat.clicked.connect(lambda: self._switch_page(0))
        sidebar_layout.addWidget(self.btn_chat)

        self.btn_settings = QPushButton("  > settings")
        self.btn_settings.setObjectName("sidebar_btn")
        self.btn_settings.setCheckable(True)
        self.btn_settings.clicked.connect(lambda: self._switch_page(1))
        sidebar_layout.addWidget(self.btn_settings)

        self._sidebar_buttons = [self.btn_chat, self.btn_settings]

        sidebar_layout.addStretch()

        status_frame = QFrame()
        status_frame.setObjectName("status_frame")
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(20, 10, 20, 10)
        status_layout.setSpacing(6)

        self.status_dot = QLabel("*")
        self.status_dot.setObjectName("status_dot_offline")
        status_layout.addWidget(self.status_dot)

        self.status_text = QLabel("checking...")
        self.status_text.setObjectName("status_bar")
        status_layout.addWidget(self.status_text)
        status_layout.addStretch()

        sidebar_layout.addWidget(status_frame)

        main_layout.addWidget(sidebar)

        self.pages = QStackedWidget()
        main_layout.addWidget(self.pages)

        chat_page = QWidget()
        chat_page.setObjectName("chat_area")
        chat_page_layout = QVBoxLayout(chat_page)
        chat_page_layout.setContentsMargins(0, 0, 0, 0)
        chat_page_layout.setSpacing(0)

        self.chat_widget = ChatWidget()
        self.chat_widget.quick_action.connect(self._handle_quick_action)
        chat_page_layout.addWidget(self.chat_widget)

        input_frame = QFrame()
        input_frame.setObjectName("input_frame")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(0)

        self.input_box = QTextEdit()
        self.input_box.setObjectName("input_box")
        self.input_box.setPlaceholderText("type a command or question ...")
        self.input_box.setFixedHeight(52)
        self.input_box.setAcceptRichText(False)
        input_layout.addWidget(self.input_box)

        self.send_btn = QPushButton("SEND")
        self.send_btn.setObjectName("send_btn")
        self.send_btn.clicked.connect(self._send_message)
        input_layout.addWidget(self.send_btn)

        chat_page_layout.addWidget(input_frame)

        self.pages.addWidget(chat_page)

        self.settings_panel = SettingsPanel()
        self.settings_panel.memory_cleared.connect(self._on_memory_cleared)
        self.pages.addWidget(self.settings_panel)

        enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self.input_box)
        enter_shortcut.activated.connect(self._send_message)

        shift_enter = QShortcut(QKeySequence(Qt.SHIFT | Qt.Key_Return), self.input_box)
        shift_enter.activated.connect(lambda: self.input_box.insertPlainText("\n"))

        self.ollama_timer = QTimer(self)
        self.ollama_timer.timeout.connect(self._check_ollama_status)
        self.ollama_timer.start(30000)

    def _switch_page(self, index: int):
        self.pages.setCurrentIndex(index)
        for i, btn in enumerate(self._sidebar_buttons):
            btn.setChecked(i == index)

    def _handle_quick_action(self, command: str):
        self.input_box.setPlainText(command)
        self._send_message()

    def _send_message(self):
        text = self.input_box.toPlainText().strip()
        if not text or self._worker is not None:
            return

        self.input_box.clear()
        self.chat_widget.add_message(text, is_user=True)
        self.chat_widget.set_typing(True)
        self.send_btn.setEnabled(False)

        self._worker = WorkerThread(text)
        self._worker.finished.connect(self._on_response)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_response(self, response: str):
        self.chat_widget.set_typing(False)
        self.chat_widget.add_message(response, is_user=False)
        self.send_btn.setEnabled(True)
        self._worker = None

    def _on_error(self, error_msg: str):
        self.chat_widget.set_typing(False)
        self.chat_widget.add_message(f"error: {error_msg}", is_user=False)
        self.send_btn.setEnabled(True)
        self._worker = None

    def _on_memory_cleared(self):
        clear_memory()
        self.chat_widget.clear_messages()

    def _check_ollama_status(self):
        try:
            r = requests.get(f"{config.OLLAMA_ENDPOINT}/api/tags", timeout=3)
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                has_model = any(config.OLLAMA_MODEL in m for m in models)
                self.status_dot.setObjectName("status_dot_online")
                if has_model:
                    self.status_text.setText(f"{config.OLLAMA_MODEL}")
                else:
                    self.status_text.setText("model not pulled")
            else:
                self._set_offline()
        except Exception:
            self._set_offline()

        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)

    def _set_offline(self):
        self.status_dot.setObjectName("status_dot_offline")
        self.status_text.setText("ollama offline")
