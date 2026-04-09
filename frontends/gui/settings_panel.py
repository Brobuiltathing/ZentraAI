import os
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QSpacerItem, QSizePolicy,
)
from PySide6.QtCore import Signal, Qt

import zentra.config as config


class SettingsPanel(QWidget):
    settings_saved = Signal()
    memory_cleared = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settings_panel")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setObjectName("settings_scroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        content = QWidget()
        content.setObjectName("settings_panel")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 32)
        layout.setSpacing(0)
        scroll.setWidget(content)

        heading = QLabel("SETTINGS")
        heading.setObjectName("settings_heading")
        layout.addWidget(heading)

        self._add_section(layout, "MODEL")
        self.input_endpoint = self._add_field(layout, "Endpoint", config.OLLAMA_ENDPOINT)
        self.input_model = self._add_field(layout, "Chat Model", config.OLLAMA_MODEL)
        self.input_vision = self._add_field(layout, "Vision Model", config.OLLAMA_VISION_MODEL)

        self._add_section(layout, "FILES")
        self.input_base = self._add_field(layout, "Base Folder", config.BASE_FOLDER)

        self._add_section(layout, "BEHAVIOUR")
        self.input_depth = self._add_field(layout, "Memory Depth", str(config.MEMORY_DEPTH))
        self.input_timeout = self._add_field(layout, "Run Timeout (s)", str(config.RUN_TIMEOUT_SECONDS))

        layout.addSpacing(12)
        save_btn = QPushButton("SAVE")
        save_btn.setObjectName("settings_save_btn")
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

        self._add_section(layout, "DANGER ZONE")
        for text, slot in [("Clear Conversation Memory", self._clear_memory), ("Clear Seen Emails Cache", self._clear_emails)]:
            btn = QPushButton(text)
            btn.setObjectName("danger_btn")
            btn.clicked.connect(slot)
            layout.addWidget(btn)

        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.status_label = QLabel("")
        self.status_label.setObjectName("settings_label")
        self.status_label.setStyleSheet("color: #6cc070; padding-top: 12px;")
        layout.addWidget(self.status_label)

    def _add_section(self, layout, title):
        lbl = QLabel(title)
        lbl.setObjectName("settings_section")
        layout.addWidget(lbl)

    def _add_field(self, layout, label_text, default_value):
        lbl = QLabel(label_text)
        lbl.setObjectName("settings_label")
        layout.addWidget(lbl)
        inp = QLineEdit(default_value)
        inp.setObjectName("settings_input")
        layout.addWidget(inp)
        return inp

    def _save(self):
        config.OLLAMA_ENDPOINT = self.input_endpoint.text().strip()
        config.OLLAMA_MODEL = self.input_model.text().strip()
        config.OLLAMA_VISION_MODEL = self.input_vision.text().strip()
        config.BASE_FOLDER = self.input_base.text().strip()
        try: config.MEMORY_DEPTH = int(self.input_depth.text().strip())
        except ValueError: pass
        try: config.RUN_TIMEOUT_SECONDS = int(self.input_timeout.text().strip())
        except ValueError: pass
        Path(config.BASE_FOLDER).mkdir(parents=True, exist_ok=True)
        self.status_label.setText("saved.")
        self.settings_saved.emit()

    def _clear_memory(self):
        self.memory_cleared.emit()
        self.status_label.setText("memory cleared.")

    def _clear_emails(self):
        try:
            if os.path.exists(config.SEEN_EMAILS_FILE):
                os.remove(config.SEEN_EMAILS_FILE)
            self.status_label.setText("email cache cleared.")
        except Exception as exc:
            self.status_label.setText(f"error: {exc}")
