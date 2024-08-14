import logging
from PyQt5 import QtGui, QtCore  # Assuming PyQt5 is being used
import os

class AppDialog(QtGui.QWidget):
    """
    Main dialog window for the App
    """
    def __init__(self, action_manager, parent=None):
        super(AppDialog, self).__init__(parent)
        self.ui = self.setup_ui()  # Assuming a method to setup the UI components
        self._dynamic_widgets = []
        self._entity_presets = {}
        self._task_manager = QtGui.QWidget(self)  # Initialize task manager as per your implementation
        self._app = sgtk.platform.current_bundle()  # Assuming the Shotgun Toolkit app bundle
        self._set_logger()
        self._preview_create_folders_action = QtGui.QAction("Preview Create Folders", self.ui.publish_view)
        self._preview_create_folders_action.triggered.connect(lambda: self._on_publish_folder_action("preview"))

        self._create_folders_action = QtGui.QAction("Create Folders", self.ui.publish_view)
        self._create_folders_action.triggered.connect(lambda: self._on_publish_folder_action("create"))

        self._unregister_folders_action = QtGui.QAction("Unregister Folders", self.ui.publish_view)
        self._unregister_folders_action.triggered.connect(lambda: self._on_publish_folder_action("unregister"))

    def _set_logger(self):
        # Create custom log handler and add it to the ShotGrid logger
        sg_log_handler = ShotGridLogHandler(self.ui.log_window)
        sg_log_handler.setFormatter(logging.Formatter('%(message)s'))

        # Attach the custom handler to the relevant loggers
        logger = logging.getLogger(__name__)
        logger.addHandler(sg_log_handler)
        logger.setLevel(logging.DEBUG)

        sgtk_logger = logging.getLogger("sgtk")
        sgtk_logger.addHandler(sg_log_handler)
        sgtk_logger.setLevel(logging.DEBUG)

    def _on_publish_folder_action(self, action):
        selected_indexes = self.ui.publish_view.selectionModel().selectedIndexes()
        for model_index in selected_indexes:
            proxy_model = model_index.model()
            source_index = proxy_model.mapToSource(model_index)
            item = source_index.model().itemFromIndex(source_index)

            is_folder = item.data(SgLatestPublishModel.IS_FOLDER_ROLE)
            if is_folder:
                sg_item = shotgun_model.get_sg_data(model_index)
                if not sg_item:
                    msg = "\n <span style='color:#2C93E2'>Unable to get item data</span> \n"
                    self._add_log(msg, 2)
                    continue
                entity_type = sg_item.get('type', None)
                entity_id = sg_item.get('id', None)
                if entity_type and entity_id:
                    # logger.debug("action is: {}".format(action))
                    if action in ["preview"]:
                        msg = "\n <span style='color:#2C93E2'>Generating a preview of the folders, please stand by...</span> \n"
                        self._add_log(msg, 2)
                        self._preview_filesystem_structure(entity_type, entity_id, verbose_mode=True)
                    elif action in ["create"]:
                        msg = "\n <span style='color:#2C93E2'>Creating folders, please stand by...</span> \n"
                        self._add_log(msg, 2)
                        paths_not_on_disk = self._preview_filesystem_structure(entity_type, entity_id, verbose_mode=False)
                        self._create_filesystem_structure_for_folder(entity_type, entity_id, paths_not_on_disk)
                    elif action in ["unregister"]:
                        msg = "\n <span style='color:#2C93E2'>Unregistering folders, please stand by...</span> \n"
                        self._add_log(msg, 2)
                        self._unregister_folders(entity_type, entity_id)
                else:
                    msg = "\n <span style='color:#CC3333'>No entities specified!</span> \n"
                    self._add_log(msg, 2)

    def _preview_filesystem_structure(self, entity_type, entity_id, verbose_mode=True):
        paths = []
        paths_not_on_disk = []
        try:
            paths.extend(
                self._app.sgtk.preview_filesystem_structure(entity_type, entity_id)
            )

        except Exception as e:
            # other errors are not expected and probably bugs - here it's useful with a callstack.
            msg = "\n <span style='color:#CC3333'>Error when previewing folders!, {}</span> \n".format(e)
            self._add_log(msg, 2)

        else:
            # success! report back to user
            if len(paths) == 0:
                msg = "\n <span style='color:#2C93E2'>*No folders would be generated on disk for this item!*</span> \n"
                self._add_log(msg, 2)

            else:
                for path in paths:
                    path.replace(r"\_", r"\\_")
                    if not os.path.exists(path):
                        paths_not_on_disk.append(path)
                self._add_log("", 3)

                if paths_not_on_disk:
                    if verbose_mode:
                        if len(paths_not_on_disk) == 1:
                            msg = "\n <span style='color:#2C93E2'>The following {} folder is not currently present on the disk and will be created:</span> \n".format(len(paths_not_on_disk))
                        else:
                            msg = "\n <span style='color:#2C93E2'>The following {} folders are not currently present on the disk and will be created:</span> \n".format(len(paths_not_on_disk))
                        self._add_log(msg, 2)
                        for path in paths_not_on_disk:
                            self._add_log(path, 3)
                        self._add_log("", 3)
                if paths and not paths_not_on_disk:
                    if verbose_mode:
                        msg = "\n <span style='color:#2C93E2'>All folders are currently present on the disk and will not be created!</span> \n"
                        self._add_log(msg, 2)

            return paths_not_on_disk

    def _add_log(self, message, level):
        # Assuming this method appends the log to the UI log window
        self.ui.log_window.append(message)

class ShotGridLogHandler(logging.Handler):
    def __init__(self, log_window):
        super().__init__()
        self.log_window = log_window
        self.log_queue = []
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.flush)
        self.timer.start(100)  # Update log window every 100ms

    def emit(self, record):
        msg = self.format(record)
        color = self.get_color(record.levelno)
        formatted_msg = f'<span style="color: {color};">{msg}</span><br>'
        self.log_queue.append(formatted_msg)

    def flush(self):
        if self.log_queue:
            self.log_window.append(''.join(self.log_queue))
            self.log_queue = []
            self.log_window.verticalScrollBar().setValue(self.log_window.verticalScrollBar().maximum())
            QtCore.QCoreApplication.processEvents()

    def get_color(self, levelno):
        if levelno == logging.DEBUG:
            return '#A9A9A9'  # Dark Grey
        elif levelno == logging.INFO:
            return '#D3D3D3'  # Light Grey
        elif levelno == logging.WARNING:
            return '#FFD700'  # Dark Yellow
        elif levelno == logging.ERROR:
            return '#B22222'  # Dark Red
        elif levelno == logging.CRITICAL:
            return '#FF8C00'  # Dark Orange
        return '#A9A9A9'  # Dark Grey
