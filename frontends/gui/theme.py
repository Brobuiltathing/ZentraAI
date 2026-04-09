DARK_THEME = """
QMainWindow { background-color: #141418; }
QWidget#central { background-color: #141418; }
QFrame#sidebar { background-color: #1b1b22; border-right: 1px solid #28282f; }
QLabel#logo_label { color: #e8dcc8; font-size: 15px; font-weight: 700; font-family: "JetBrains Mono", "Cascadia Code", "Consolas", monospace; padding: 22px 20px 2px 20px; letter-spacing: 5px; }
QLabel#version_label { color: #56565e; font-size: 9px; font-family: "JetBrains Mono", "Consolas", monospace; padding: 0px 20px 20px 20px; letter-spacing: 1px; }
QFrame#sidebar_separator { background-color: #28282f; max-height: 1px; margin: 4px 16px; }
QPushButton#sidebar_btn { background-color: transparent; color: #6b6b78; border: none; border-left: 2px solid transparent; border-radius: 0px; padding: 11px 20px; font-size: 12px; font-family: "JetBrains Mono", "Consolas", monospace; text-align: left; letter-spacing: 1px; }
QPushButton#sidebar_btn:hover { background-color: #22222a; color: #a0a0b0; border-left: 2px solid #3a3a44; }
QPushButton#sidebar_btn:checked { background-color: #1f1f28; color: #e4a853; border-left: 2px solid #e4a853; font-weight: 600; }
QLabel#sidebar_section { color: #3a3a44; font-size: 9px; font-family: "JetBrains Mono", "Consolas", monospace; font-weight: 700; letter-spacing: 2px; padding: 16px 20px 6px 20px; }
QFrame#chat_area, QWidget#chat_area { background-color: #141418; border: none; }
QScrollArea#chat_scroll { background-color: #141418; border: none; }
QScrollBar:vertical { background: transparent; width: 5px; border: none; margin: 4px 1px; }
QScrollBar::handle:vertical { background: #2e2e38; border-radius: 2px; min-height: 40px; }
QScrollBar::handle:vertical:hover { background: #e4a853; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; height: 0; }
QWidget#message_user { background-color: #1e1e28; border-radius: 2px; border-left: 3px solid #e4a853; padding: 14px 20px; margin: 6px 80px 6px 140px; }
QWidget#message_bot { background-color: #19191f; border-radius: 2px; border-left: 3px solid #2e2e38; padding: 14px 20px; margin: 6px 140px 6px 80px; }
QLabel#message_text_user { color: #d4d0c8; font-size: 13px; font-family: "JetBrains Mono", "Consolas", monospace; background: transparent; }
QLabel#message_text_bot { color: #b0b0bc; font-size: 13px; font-family: "JetBrains Mono", "Consolas", monospace; background: transparent; }
QLabel#message_role_user { color: #e4a853; font-size: 9px; font-family: "JetBrains Mono", "Consolas", monospace; font-weight: 700; letter-spacing: 2px; background: transparent; padding-bottom: 6px; }
QLabel#message_role_bot { color: #4a4a58; font-size: 9px; font-family: "JetBrains Mono", "Consolas", monospace; font-weight: 700; letter-spacing: 2px; background: transparent; padding-bottom: 6px; }
QLabel#message_time { color: #333340; font-size: 9px; font-family: "JetBrains Mono", "Consolas", monospace; background: transparent; padding-top: 6px; }
QFrame#input_frame { background-color: #1b1b22; border: 1px solid #28282f; border-radius: 0px; margin: 0px 80px 20px 80px; }
QTextEdit#input_box { background-color: transparent; color: #d4d0c8; border: none; font-size: 13px; font-family: "JetBrains Mono", "Consolas", monospace; padding: 14px 18px; selection-background-color: #e4a853; selection-color: #141418; }
QPushButton#send_btn { background-color: #e4a853; color: #141418; border: none; border-radius: 0px; padding: 10px 24px; font-size: 11px; font-weight: 700; font-family: "JetBrains Mono", "Consolas", monospace; margin: 6px 6px 6px 0px; letter-spacing: 2px; min-width: 70px; }
QPushButton#send_btn:hover { background-color: #f0b860; }
QPushButton#send_btn:pressed { background-color: #cc9440; }
QPushButton#send_btn:disabled { background-color: #28282f; color: #3a3a44; }
QLabel#status_bar { color: #4a4a58; font-size: 10px; font-family: "JetBrains Mono", "Consolas", monospace; padding: 2px 4px; background: transparent; }
QLabel#status_dot_online { color: #6cc070; font-size: 14px; }
QLabel#status_dot_offline { color: #c45050; font-size: 14px; }
QFrame#status_frame { background-color: #19191f; border-top: 1px solid #28282f; }
QFrame#settings_panel { background-color: #141418; }
QScrollArea#settings_scroll { background-color: #141418; border: none; }
QLabel#settings_heading { color: #e8dcc8; font-size: 15px; font-weight: 700; font-family: "JetBrains Mono", "Consolas", monospace; letter-spacing: 3px; padding: 28px 32px 6px 32px; }
QLabel#settings_section { color: #e4a853; font-size: 9px; font-weight: 700; font-family: "JetBrains Mono", "Consolas", monospace; letter-spacing: 2px; padding: 20px 32px 8px 32px; }
QLabel#settings_label { color: #6b6b78; font-size: 11px; font-family: "JetBrains Mono", "Consolas", monospace; padding: 6px 32px 2px 32px; }
QLineEdit#settings_input { background-color: #1b1b22; color: #d4d0c8; border: 1px solid #28282f; border-radius: 0px; padding: 10px 14px; font-size: 12px; font-family: "JetBrains Mono", "Consolas", monospace; margin: 2px 32px; }
QLineEdit#settings_input:focus { border: 1px solid #e4a853; }
QPushButton#settings_save_btn { background-color: #e4a853; color: #141418; border: none; border-radius: 0px; padding: 11px 32px; font-size: 11px; font-weight: 700; font-family: "JetBrains Mono", "Consolas", monospace; letter-spacing: 2px; margin: 16px 32px; }
QPushButton#settings_save_btn:hover { background-color: #f0b860; }
QPushButton#danger_btn { background-color: transparent; color: #c45050; border: 1px solid #2a2028; border-radius: 0px; padding: 10px 32px; font-size: 11px; font-family: "JetBrains Mono", "Consolas", monospace; letter-spacing: 1px; margin: 3px 32px; }
QPushButton#danger_btn:hover { background-color: #1e1418; border-color: #c45050; }
QLabel#typing_label { color: #e4a853; font-size: 11px; font-family: "JetBrains Mono", "Consolas", monospace; padding: 6px 96px; background: transparent; letter-spacing: 1px; }
QLabel#welcome_title { color: #e8dcc8; font-size: 20px; font-weight: 700; font-family: "JetBrains Mono", "Consolas", monospace; letter-spacing: 4px; background: transparent; }
QLabel#welcome_sub { color: #3a3a44; font-size: 11px; font-family: "JetBrains Mono", "Consolas", monospace; letter-spacing: 1px; background: transparent; padding-top: 8px; }
QPushButton#quick_btn { background-color: #1b1b22; color: #6b6b78; border: 1px solid #28282f; border-radius: 0px; padding: 10px 18px; font-size: 11px; font-family: "JetBrains Mono", "Consolas", monospace; }
QPushButton#quick_btn:hover { background-color: #22222a; color: #e4a853; border-color: #e4a853; }
"""
