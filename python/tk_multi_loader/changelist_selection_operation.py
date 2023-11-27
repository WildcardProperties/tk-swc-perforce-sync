""" Load shots UI """

# python
import os

# Qt
from sgtk.platform.qt import QtCore, QtGui
from tank.platform.qt5 import QtWidgets

from .changelists_selection_widget import ChangelistSelectionWidget
from .perform_actions import PerformActions
from .perforce_change import create_change

import sgtk
logger = sgtk.platform.get_logger(__name__)
# Loader
loader = None


class ChangelistSelection(QtWidgets.QDialog):
    """
    Shot Loader using Shot Select Widget
    """

    WINDOW_TITLE = 'Changelist Selection'

    def __init__(self,  p4, selected_actions, parent):

        super(ChangelistSelection, self).__init__(parent)
        
        self.p4 = p4
        #self.sg_item = sg_item
        #self.new_sg_item = self.sg_item
        #self.action = action
        self.selected_actions = selected_actions
        self.parent = parent
        self.change = None

        # Variables
        self.changelists_widget = ChangelistSelectionWidget()
        self.changelists_lst = self.changelists_widget.changelists_lst
        self.changelists_description = self.changelists_widget.changelists_description

        # Setup window
        self.setWindowTitle(self.WINDOW_TITLE)

        # Make connections
        self.changelists_lst.itemClicked.connect(self.populate_changelists_description)

        # Populate UI
        self.populate_changelists_lst()
        # self.populate_changelists_description()

        # Main Layout
        self.main_layout = QtWidgets.QVBoxLayout()

        self.main_layout.addWidget(self.changelists_widget)
        self.setLayout(self.main_layout)
        self.changelists_widget.ok_button.clicked.connect(self.set_changelist)
        self.changelists_widget.new_button.clicked.connect(self.create_new_changelist)
        #self.changelists_widget.cancel_button.clicked.connect(self.close_widget)

    def populate_changelists_lst(self):

        self.changelists_lst.clear()

        # Add the "default" changelist
        self.changelists_lst.addItem("default")

        client = self.p4.fetch_client()
        workspace = client.get("Client", None)
        # Get the pending changelists
        if workspace:
            change_lists = self.p4.run_changes("-l", "-s", "pending", "-c", workspace)
            # logger.debug("<<<<<<<  change_lists: {}".format(change_lists))

            # Get the pending changelists
            for change_list in change_lists:
                change = change_list.get("change", None)
                desc = change_list.get('desc', None)
                item_str = "{} {}".format(change, desc)
                self.changelists_lst.addItem(item_str)


    def populate_changelists_description(self, item):
        """
        populate the changelist description
        :return:
        """
        self.changelists_description.clear()
        try:
            change_str = item.text()
            change_str = change_str.split(' ')
            self.change = change_str[0]
            desc = ' '.join(change_str[1:])

            if self.change:
                self.changelists_description.setText(desc)
        except Exception as e:
            logger.debug("Error populating changelist description: {}".format(e))


    def create_new_changelist(self):
        """
        Create a new changelist
        :return:
        """
        try:
            description = self.changelists_widget.changelists_description.text()
            description = description.strip()
            # Create a new changelist using the current workspace and description desc
            change = create_change(self.p4, description)
            logger.debug(">>>> new changelist: {}".format(change))
            # Add the new changelist to the list
            self.changelists_lst.addItem("{} {}".format(change, description))
            self.changelists_lst.setCurrentRow(self.changelists_lst.count() - 1)
            # Select the new changelist

            self.change = str(change)
            if self.change:
                self.set_changelist()


        except Exception as e:
            logger.debug("Error creating new changelist: {}".format(e))

    def close_widget(self):
        self.close()

    def set_changelist(self):
        """
        Set the changelist
        :return:
        """
        try:
            performed_actions = []
            change = self.change
            desc = self.changelists_description.text()
            if change:
                for sg_item, action in self.selected_actions:
                    # check if the filepath lead to a valid shotgrid entity
                    if not self.is_file_valid_in_shotgrid(sg_item):
                        continue
                    perform_actions = PerformActions(self.p4, sg_item, action, change, desc)
                    performed_actions.append(sg_item)
                    self.new_sg_item = perform_actions.run()
                # If we have performed actions, update the pending widget and refresh the publish data
                if performed_actions and len(performed_actions) > 0:
                    self.parent._populate_pending_widget()
                    self.parent.refresh_publish_data()

        except Exception as e:
            logger.debug("Error setting changelist: {}".format(e))
        self.close()

    def is_file_valid_in_shotgrid(self, sg_item):
        """
        Check if the filepath lead to a valid shotgrid entity
        :param sg_item:
        :return:
        """
        if not sg_item:
            return False

        if "path" in sg_item:
            local_path = sg_item["path"].get("local_path", None)
            if local_path:
                if not os.path.exists(local_path):
                    msg = "File does not exist: {}".format(local_path)
                    self.send_error_message(msg)
                    return False

                if "entity" in sg_item:
                    entity = sg_item.get("entity", None)
                    if entity:
                        msg = "File is valid: {}".format(local_path)
                        self.send_success_message(msg)
                        return True

                else:
                    sg = sgtk.platform.current_bundle()
                    current_relative_path = self.convert_to_relative_path(local_path)
                    logger.debug(">>>>> current_relative_path: {}".format(current_relative_path))
                    file_name = os.path.basename(local_path)  # Extracting file name from the path
                    logger.debug(">>>>> file_name: {}".format(file_name))
                    local_path = local_path.replace("\\", "/")  # Replacing backslash with forward slash

                    # Modify your query to search by the file name
                    filter_query = [['name', 'is', file_name]]
                    published_files = sg.shotgun.find("PublishedFile", filter_query, ["path", "entity"])
                    # logger.debug(">>>>> published_files: {}".format(published_files))

                    for published_file in published_files:
                        # logger.debug(">>>>> published_file: {}".format(published_file))
                        if "path" in published_file:
                            path = published_file["path"]
                            entity = None
                            if "relative_path" in path:
                                query_relative_path = path.get("relative_path", None)
                                logger.debug(">>>>> query_relative_path: {}".format(query_relative_path))
                                if query_relative_path == current_relative_path:
                                    entity = published_file.get("entity", None)
                            elif "local_path" in path:
                                query_local_path = path.get("local_path", None)
                                query_local_path = query_local_path.replace("\\", "/")
                                logger.debug(">>>>> query_local_path: {}".format(query_local_path))
                                if query_local_path == local_path:
                                    entity = published_file.get("entity", None)

                            if entity:
                                msg = "Successfully retrieved the associated ShotGrid entity for the file located at {}".format(local_path)
                                self.send_success_message(msg)
                                return True

                    msg = "Failed to retrieve the associated Shotgrid entity for the file located at {}".format(local_path)
                    self.send_error_message(msg)
                    return False
        return False

    def convert_to_relative_path(self, absolute_path):
        # Split the path on ":/" and take the second part, if it exists
        parts = absolute_path.split(":/", 1)
        relative_path = parts[1] if len(parts) > 1 else absolute_path

        return relative_path

    def is_file_valid_in_shotgrid_old(self, sg_item):
        """
        Check if the filepath lead to a valid shotgrid entity
        :param sg_item:
        :return:
        """
        if not sg_item:
            return False

        if "path" in sg_item:
            local_path = sg_item["path"].get("local_path", None)
            if local_path:
                if not os.path.exists(local_path):
                    msg = "File does not exist: {}".format(local_path)
                    self.send_error_message(msg)
                    return False

                if "entity" in sg_item:
                    entity = sg_item.get("entity", None)
                    if entity:
                        msg = "File is valid: {}".format(local_path)
                        self.send_success_message(msg)
                        return True
                # get tk
                tk = sgtk.sgtk_from_path(local_path)
                if not tk:
                    msg = "Unable to get tk from file: {}".format(local_path)
                    self.send_error_message(msg)
                    return False
                # get entity from path
                entity = tk.get_entity_from_path(local_path)
                if not entity:
                    entity = tk.shotgun.find_one("PublishedFile", [["path", "is", local_path]], ["entity"])
                    if not entity:
                        msg = "Unable to get entity for file: {}".format(local_path)
                        self.send_error_message(msg)
                        return False
                if entity:
                    msg = "Entity is found for file: {}".format(local_path)
                    self.send_success_message(msg)
                    return True
        return False

    def send_error_message(self, text):
        """
        Send error message
        :param text:
        :return:
        """
        # msg = "\n <span style='color:#FF0000'>{}:</span> \n".format(text)
        msg = "\n <span style='color:#CC3333'>{}:</span> \n".format(text)
        self.parent._add_log(msg, 2)

    def send_success_message(self, text):
        """
        Send error message
        :param text:
        :return:
        """
        msg = "\n <span style='color:#2C93E2'>{}:</span> \n".format(text)
        self.parent._add_log(msg, 2)


    def get_sg_item(self):
        if not self.new_sg_item:
            return self.sg_item

def run(p4=None, selected_actions=None, parent=None):
    """
    Main function for the application
    """
    global loader
    app = QtWidgets.QApplication.instance()

    
    # if loader is None:
    loader = ChangelistSelection(p4=p4, selected_actions=selected_actions , parent=parent)

    loader.show()


if __name__ == '__main__':
    """
    Runs application
    """
    run()


