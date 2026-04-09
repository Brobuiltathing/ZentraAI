import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase

from zentra.config import (
    OLLAMA_ENDPOINT, OLLAMA_MODEL, OLLAMA_VISION_MODEL,
    BASE_FOLDER, SCREENSHOT_FOLDER,
    PSUTIL_AVAILABLE, PYAUTOGUI_AVAILABLE, GOOGLE_AVAILABLE,
    APP_NAME, APP_VERSION,
)
from zentra.logger import log


def main():
    log.info("=" * 60)
    log.info(f"  {APP_NAME} v{APP_VERSION} -- GUI")
    log.info(f"  Ollama      : {OLLAMA_ENDPOINT}  model={OLLAMA_MODEL}")
    log.info(f"  Vision      : {OLLAMA_VISION_MODEL}")
    log.info(f"  psutil      : {'yes' if PSUTIL_AVAILABLE else 'no'}")
    log.info(f"  pyautogui   : {'yes' if PYAUTOGUI_AVAILABLE else 'no'}")
    log.info(f"  google      : {'yes' if GOOGLE_AVAILABLE else 'no'}")
    log.info("=" * 60)

    from frontends.gui.theme import DARK_THEME
    from frontends.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setStyleSheet(DARK_THEME)

    preferred_fonts = ["JetBrains Mono", "Cascadia Code", "Fira Code", "Consolas"]
    chosen = "Consolas"
    available = QFontDatabase.families()
    for pf in preferred_fonts:
        if pf in available:
            chosen = pf
            break

    font = QFont(chosen, 10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
