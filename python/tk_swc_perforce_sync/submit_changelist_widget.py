import os
from sgtk.platform.qt import QtCore, QtGui
from tank.platform.qt5 import QtWidgets
import datetime
from tank_vendor import shotgun_api3
import sgtk
logger = sgtk.platform.get_logger(__name__)

class SubmitChangelistWidget(QtWidgets.QDialog):
    """
    Widget to submit and edit a changelist
    """

    def __init__(self, parent=None, myp4=None, chane_item=None, file_dict=None):
        super(SubmitChangelistWidget, self).__init__(parent)

        # Setup the UI
        self.setObjectName('submit_changelist_widget')
        self.setMinimumSize(1000, 618)
        self.setWindowTitle('Submit Changelist')
        self.parent = parent
        self.p4 = myp4
        self.change_sg_item = chane_item
        self.submit_widget_dict = file_dict

        # Main Layout
        self.main_layout = QtWidgets.QVBoxLayout()

        # Top Layout
        self.top_layout = QtWidgets.QGridLayout()
        self.top_layout.setHorizontalSpacing(5)  # Adjust horizontal spacing
        self.top_layout.setVerticalSpacing(5)  # Adjust vertical spacing
        self.main_layout.addLayout(self.top_layout)

        # Changelist Info (Static Labels)
        self.changelist_label = QtWidgets.QLabel('Changelist:')
        self.changelist_value = QtWidgets.QLabel('')

        self.date_label = QtWidgets.QLabel('Date:')
        self.date_value = QtWidgets.QLabel('')

        self.workspace_label = QtWidgets.QLabel('Workspace:')
        self.workspace_value = QtWidgets.QLabel('')

        self.user_label = QtWidgets.QLabel('User:')
        self.user_value = QtWidgets.QLabel('')

        self.top_layout.addWidget(self.changelist_label, 0, 0, QtCore.Qt.AlignRight)
        self.top_layout.addWidget(self.changelist_value, 0, 1, QtCore.Qt.AlignLeft)
        self.top_layout.addWidget(self.date_label, 1, 0, QtCore.Qt.AlignRight)
        self.top_layout.addWidget(self.date_value, 1, 1, QtCore.Qt.AlignLeft)
        self.top_layout.addWidget(self.workspace_label, 0, 2, QtCore.Qt.AlignRight)
        self.top_layout.addWidget(self.workspace_value, 0, 3, QtCore.Qt.AlignLeft)
        self.top_layout.addWidget(self.user_label, 1, 2, QtCore.Qt.AlignRight)
        self.top_layout.addWidget(self.user_value, 1, 3, QtCore.Qt.AlignLeft)

        # Adjust column stretch to make the pairs closer
        self.top_layout.setColumnStretch(0, 0)
        self.top_layout.setColumnStretch(1, 1)
        self.top_layout.setColumnStretch(2, 0)
        self.top_layout.setColumnStretch(3, 1)

        # Spacer to create a one-line space between "Date:" and "Description:"
        self.spacer_label = QtWidgets.QLabel('')
        self.main_layout.addWidget(self.spacer_label)

        # Changelist Description
        self.changelist_desc_label = QtWidgets.QLabel('Description:')
        self.changelist_description = QtWidgets.QTextEdit()
        self.changelist_description.setPlaceholderText("Enter changelist description here...")
        self.changelist_description.setFixedHeight(100)  # Make description area height about half
        self.changelist_description.textChanged.connect(self.update_buttons_state)

        self.main_layout.addWidget(self.changelist_desc_label)
        self.main_layout.addWidget(self.changelist_description)

        # File Table
        self.files_label = QtWidgets.QLabel('Files to Submit:')
        self.files_table_widget = QtWidgets.QTableWidget(0, 6)  # Adjusted for 6 columns (including checkbox)
        self.files_table_widget.setHorizontalHeaderLabels(
            ['', 'File', 'In Folder', 'Resolve Status', 'Type', 'Pending Action'])


        # Adjust column resizing to fit content and stretch
        header = self.files_table_widget.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)  # Checkbox column
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)  # File column
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)  # In Folder column
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)  # Resolve Status column
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)  # Type column
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.Stretch)  # Pending Action column

        self.main_layout.addWidget(self.files_label)
        self.main_layout.addWidget(self.files_table_widget)

        # Buttons
        self.select_all_button = QtWidgets.QPushButton('Select All')
        self.select_all_button.setFixedWidth(100)
        self.select_all_button.setFixedHeight(22.5)
        self.select_all_button.clicked.connect(self.select_all)

        self.select_none_button = QtWidgets.QPushButton('Select None')
        self.select_none_button.setFixedWidth(100)
        self.select_none_button.setFixedHeight(22.5)
        self.select_none_button.clicked.connect(self.select_none)

        self.submit_button = QtWidgets.QPushButton('Submit')
        self.submit_button.setToolTip('Submit the selected files in the changelist')
        self.submit_button.setFixedWidth(100)
        self.submit_button.setFixedHeight(22.5)
        self.submit_button.clicked.connect(self.submit_changelist)

        self.save_button = QtWidgets.QPushButton('Save')
        self.save_button.setToolTip('Save the changelist description')
        self.save_button.setFixedWidth(100)
        self.save_button.setFixedHeight(22.5)
        self.save_button.clicked.connect(self.save_changelist)

        self.cancel_button = QtWidgets.QPushButton('Cancel')
        self.cancel_button.setToolTip('Cancel the operation')
        self.cancel_button.setFixedWidth(100)
        self.cancel_button.setFixedHeight(22.5)
        self.cancel_button.clicked.connect(self.cancel_action)

        # Button Layout
        self.button_layout = QtWidgets.QHBoxLayout()
        self.button_layout.addWidget(self.select_all_button)
        self.button_layout.addWidget(self.select_none_button)
        self.button_layout.addStretch()  # Add stretch to push buttons to the right
        self.button_layout.addWidget(self.submit_button)
        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.cancel_button)

        self.main_layout.addLayout(self.button_layout)

        self.setLayout(self.main_layout)

        self.update_buttons_state()
        self.populate_file_table()


    def populate_file_table(self):
        """
        Populate the table widget with the files to submit.
        """
        #self.files_table_widget.setRowCount(0)  # Clear existing rows


        description = self.change_sg_item.get("description", "")
        user = self.change_sg_item.get("p4_user", "")
        head_time = self.change_sg_item.get("headTime", "")
        change_time = self.change_sg_item.get("time", "")
        # logger.debug(f"head_time:{head_time}, change_time:{change_time}")
        date_time = self._fix_timestamp(head_time)
        # logger.debug(f"date_time:{date_time}")
        change = self.change_sg_item.get("change", "")
        workspace = self.change_sg_item.get("client", "")
        self.changelist_description.setText(description)
        self.user_value.setText(user)

        self.changelist_value.setText(str(change))
        self.date_value.setText(date_time)
        self.workspace_value.setText(workspace)

        description_length = 0
        has_files = False
        if description:
            description_length = len(description)
        if self.submit_widget_dict:
            has_files = len(self.submit_widget_dict.values()) > 0

        self.submit_button.setEnabled(description_length >= 5 and has_files)
        self.save_button.setEnabled(description_length >= 5)

        row_position = 0
        for key, file_info in self.submit_widget_dict.items():
            # logger.debug(">>>>>>>>>>> file_info:{}".format(file_info))

            self.files_table_widget.insertRow(row_position)

            # Create checkbox item
            checkbox_item = QtWidgets.QTableWidgetItem()
            checkbox_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            checkbox_item.setCheckState(QtCore.Qt.Checked)
            self.files_table_widget.setItem(row_position, 0, checkbox_item)

            self.files_table_widget.setItem(row_position, 1, QtWidgets.QTableWidgetItem(file_info["file"]))
            self.files_table_widget.setItem(row_position, 2, QtWidgets.QTableWidgetItem(file_info["folder"]))
            self.files_table_widget.setItem(row_position, 3, QtWidgets.QTableWidgetItem(file_info["resolve_status"]))
            self.files_table_widget.setItem(row_position, 4, QtWidgets.QTableWidgetItem(file_info["type"]))
            self.files_table_widget.setItem(row_position, 5, QtWidgets.QTableWidgetItem(file_info["pending_action"]))

            row_position += 1

        # Update the button states based on the initial description and file selection
        #self.update_buttons_state()

    def _fix_timestamp(self, unix_timestamp):
        """
        Convert created_at unix time stamp in sg_data to shotgun time stamp.

        :param sg_data: Standard Shotgun entity dictionary with keys type, id and name.
        """
        try:
            unix_timestamp = int(unix_timestamp)
            sg_timestamp = datetime.datetime.fromtimestamp(
                unix_timestamp, shotgun_api3.sg_timezone.LocalTimezone()
            )
            # sg_timestamp = sg_timestamp.strftime('%Y-%m-%d %H:%M:%S')
            sg_timestamp =str(sg_timestamp.strftime('%Y-%m-%d %H:%M:%S'))
            #sg_timestamp = str(sg_timestamp)
        except Exception as e:
            # logger.debug("Failed to convert timestamp: %s" % e)
            sg_timestamp = ""
        return sg_timestamp

    def update_buttons_state(self):
        """
        Enable or disable the submit and save buttons based on the description length and file selection.
        """
        description_length = len(self.changelist_description.toPlainText())
        has_files = any(self.files_table_widget.item(row, 0).checkState() == QtCore.Qt.Checked for row in
                        range(self.files_table_widget.rowCount()))

        self.submit_button.setEnabled(description_length >= 5 and has_files)
        self.save_button.setEnabled(description_length >= 5)

    def select_all(self):
        """
        Select all files by checking all checkboxes in the table.
        """
        for row in range(self.files_table_widget.rowCount()):
            self.files_table_widget.item(row, 0).setCheckState(QtCore.Qt.Checked)
        self.update_buttons_state()

    def select_none(self):
        """
        Deselect all files by unchecking all checkboxes in the table.
        """
        for row in range(self.files_table_widget.rowCount()):
            self.files_table_widget.item(row, 0).setCheckState(QtCore.Qt.Unchecked)
        self.update_buttons_state()

    def submit_changelist(self):
        """
        Handle the submit action
        """
        file_info_deleted = []
        file_info_other = []
        description = self.changelist_description.toPlainText()
        selected_files = []
        if not description:
            QtWidgets.QMessageBox.warning(self, "Warning", "Changelist description cannot be empty.")
            return

        for row in range(self.files_table_widget.rowCount()):
            if self.files_table_widget.item(row, 0).checkState() == QtCore.Qt.Checked:
                file_info = {
                    "file": self.files_table_widget.item(row, 1).text(),
                    "folder": self.files_table_widget.item(row, 2).text(),
                }
                selected_files.append(file_info)



        if not selected_files:
            QtWidgets.QMessageBox.warning(self, "Warning", "No files selected for submission.")
            return

        # Here you would add the logic to submit the changelist with the selected files and description
        logger.debug(f"Submitting changelist with description: {description}")
        logger.debug("Files to be submitted:")
        for file_info in selected_files:
            file_name = file_info.get("file", None)
            folder = file_info.get("folder", None)
            if file_name and folder:
                key = (file_name, folder)
                if key in self.submit_widget_dict:
                    full_file_info = self.submit_widget_dict[key]
                    if "sg_item" in full_file_info:
                        full_file_info["sg_item"]["description"] = description
                    #full_file_info["description"] = description
                    if full_file_info:
                        action = full_file_info.get("pending_action", None)
                        if action == "delete":
                            file_info_deleted.append(full_file_info)
                        else:
                            file_info_other.append(full_file_info)
                else:
                    logger.warning(f"File info not found for {key}")

        if file_info_deleted:
            logger.debug(">>>>>>>>>>> Submitting files for deletion:{}".format(file_info_deleted))
            self.parent.on_submit_deleted_files(self.change_sg_item, file_info_deleted)
        if file_info_other:
            logger.debug(">>>>>>>>>>> Submitting other files:{}".format(file_info_other))
            self.parent.on_submit_other_files(self.change_sg_item, file_info_other)
        if not file_info_deleted and not file_info_other:
            logger.debug(">>>>>>>>>>> No files to submit")
        if file_info_deleted or file_info_other:
            msg = "\n <span style='color:#2C93E2'>Updating the Pending view ...</span> \n"
            self.parent._add_log(msg, 2)
            # Update the Pending view
            self.parent._populate_pending_widget()
            # logger.debug(">>>>>>>>>>> Updating the publish view as well")
            self.parent._on_treeview_item_selected()

        # Close the dialog after submission
        self.accept()

    def _get_submit_changelist_widget_data(self):
        """
        Retrieve data from the submit changelist widget
        """
        if self._pending_view_widget is not None and self._pending_view_widget.selectionModel() is not None:
            selected_indexes = self._pending_view_widget.selectionModel().selectedRows()
            return selected_indexes
        else:
            logger.error("Pending view widget or its selection model is already deleted.")
            return []

    def cancel_action(self):
        """
        Handle the cancel action
        """
        # self.reject()
        self.close()

    def save_changelist(self):
        """
        Handle the save action
        """
        description = self.changelist_description.toPlainText()
        change = self.changelist_value.text()
        logger.debug(f"Saving changelist with description: {description} and change: {change}")

        if not description:
            QtWidgets.QMessageBox.warning(self, "Warning", "Changelist description cannot be empty.")
            return

        # Save the changelist description using Perforce client
        try:
            changelist_spec = self.p4.fetch_change(change)
            changelist_spec['Description'] = description
            self.p4.save_change(changelist_spec)
            logger.debug(f"Changelist {change} saved with description: {description}")
            msg = "\n <span style='color:#2C93E2'>Updating the Pending view ...</span> \n"
            self.parent._add_log(msg, 2)
            # Update the Pending view
            # self.parent.update_pending_view()
            self.parent._populate_pending_widget()
        except Exception as e:
            logger.error(f"Failed to save changelist {change}: {e}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save changelist: {e}")
            return

        # Close the dialog after saving
        self.accept()
