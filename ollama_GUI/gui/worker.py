import asyncio
import traceback

from PySide6.QtCore import QThread, Signal

from engine import process_message


class WorkerThread(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, message: str, parent=None):
        super().__init__(parent)
        self.message = message

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(process_message(self.message))
            loop.close()
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(f"{exc}\n{traceback.format_exc()}")
