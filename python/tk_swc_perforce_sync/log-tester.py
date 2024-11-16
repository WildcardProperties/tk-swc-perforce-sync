import sys
import logging
from PyQt5 import QtWidgets, QtCore
sys.path.append("C:/Program Files/Shotgun/Resources/Desktop/Python/bundle_cache/app_store/tk-core/v0.20.14/python")
import sgtk


class LogWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.log_window = QTextBrowser()
        self.log_window.verticalScrollBar().setValue(self.log_window.verticalScrollBar().maximum())
        self.log_window.setMinimumHeight(187)
        self.log_window.setMaximumHeight(187)
        self.log_window.setMinimumWidth(630)
        self.horizontalLayout_8 = QHBoxLayout(self)
        self.horizontalLayout_8.addWidget(self.log_window)

    def _add_log(self, msg, flag):
        if flag <= 2:
            msg = "\n{}\n".format(msg)
        else:
            msg = "{}".format(msg)
        self.log_window.append(msg)
        if flag < 4:
            print(msg)  # Use logger.debug(msg) if a logger is configured
        self.log_window.verticalScrollBar().setValue(self.log_window.verticalScrollBar().maximum())
        QCoreApplication.processEvents()

    def add_shotgrid_log(self, log_msg, flag):
        self._add_log(log_msg, flag)


class ShotGridLogHandler(logging.Handler):
    def __init__(self, log_window):
        super().__init__()
        self.log_window = log_window

    def emit(self, record):
        msg = self.format(record)
        self.log_window.add_shotgrid_log(msg, record.levelno)


def main():
    app = QApplication(sys.argv)
    main_window = LogWindow()
    main_window.show()

    # Set up ShotGrid logger
    logger = sgtk.platform.get_logger(__name__)

    # Create custom log handler and add it to the ShotGrid logger
    sg_log_handler = ShotGridLogHandler(main_window)
    sg_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(sg_log_handler)
    logger.setLevel(logging.DEBUG)

    # Simulate some log messages
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
