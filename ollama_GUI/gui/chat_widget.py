from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QSizePolicy, QPushButton,
)
from PySide6.QtCore import Qt, QTimer, Signal
from datetime import datetime


class MessageBubble(QFrame):
    def __init__(self, text: str, is_user: bool, parent=None):
        super().__init__(parent)
        self.setObjectName("message_user" if is_user else "message_bot")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        role_label = QLabel("YOU" if is_user else "ZENTRA")
        role_label.setObjectName("message_role_user" if is_user else "message_role_bot")
        layout.addWidget(role_label)

        text_label = QLabel(text)
        text_label.setObjectName("message_text_user" if is_user else "message_text_bot")
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(text_label)

        time_label = QLabel(datetime.now().strftime("%H:%M"))
        time_label.setObjectName("message_time")
        time_label.setAlignment(Qt.AlignRight)
        layout.addWidget(time_label)


class WelcomeScreen(QWidget):
    quick_action = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(80, 0, 80, 40)
        layout.setSpacing(0)
        layout.addStretch(3)

        title = QLabel("ZENTRA")
        title.setObjectName("welcome_title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        sub = QLabel("local ai assistant  //  type anything to begin")
        sub.setObjectName("welcome_sub")
        sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub)

        layout.addSpacing(40)

        grid = QHBoxLayout()
        grid.setSpacing(8)
        grid.addStretch()

        quick_actions = [
            ("system stats", "show system stats"),
            ("open chrome", "open chrome"),
            ("today's calendar", "show my calendar for today"),
            ("check emails", "summarise my unread emails"),
        ]

        for label, command in quick_actions:
            btn = QPushButton(label)
            btn.setObjectName("quick_btn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, c=command: self.quick_action.emit(c))
            grid.addWidget(btn)

        grid.addStretch()
        layout.addLayout(grid)

        layout.addStretch(2)


class ChatWidget(QWidget):
    quick_action = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chat_area")
        self._has_messages = False

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self.welcome = WelcomeScreen()
        self.welcome.quick_action.connect(self.quick_action.emit)
        self._layout.addWidget(self.welcome)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("chat_scroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVisible(False)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("chat_area")
        self.messages_layout = QVBoxLayout(self.scroll_content)
        self.messages_layout.setContentsMargins(0, 16, 0, 16)
        self.messages_layout.setSpacing(10)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.scroll_content)
        self._layout.addWidget(self.scroll_area)

        self.typing_label = QLabel("")
        self.typing_label.setObjectName("typing_label")
        self.typing_label.setVisible(False)
        self._layout.addWidget(self.typing_label)

    def add_message(self, text: str, is_user: bool):
        if not self._has_messages:
            self.welcome.setVisible(False)
            self.scroll_area.setVisible(True)
            self._has_messages = True

        bubble = MessageBubble(text, is_user)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def set_typing(self, visible: bool):
        if visible:
            self.typing_label.setText("_ zentra is thinking ...")
            self.typing_label.setVisible(True)
        else:
            self.typing_label.setVisible(False)

    def clear_messages(self):
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._has_messages = False
        self.scroll_area.setVisible(False)
        self.welcome.setVisible(True)

    def _scroll_to_bottom(self):
        sb = self.scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())
