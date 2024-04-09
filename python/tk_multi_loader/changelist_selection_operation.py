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
        self.change = "default"

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
                    is_valid, entity = self.is_file_valid_in_shotgrid(sg_item)
                    if not is_valid:
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
        # Check if the filepath leads to a valid shotgrid entity
        entity, published_file = self.check_validity_by_published_file(sg_item)
        if not entity:
            entity, published_file = self.check_validity_by_path_parts(sg_item)
        return entity, published_file

    def check_validity_by_published_file(self, sg_item):
        """
        Check if the filepath leads to a valid shotgrid entity
        :param sg_item: Shotgrid item information
        :return: entity and published file info if found, None otherwise
        """
        if not sg_item:
            return None, None

        logger.debug(">>>>> Checking validity by published file: sg_item: {}".format(sg_item))

        if "path" in sg_item:
            local_path = sg_item["path"].get("local_path", None)
            logger.debug(">>>>> Checking validity by published file: local_path: {}".format(local_path))
            if local_path:

                if not os.path.exists(local_path):
                    msg = "File does not exist locally: {}".format(local_path)
                    logger.debug(">>>>> {}".format(msg))
                    # self.send_error_message(msg)
                    # return None, None

                sg = sgtk.platform.current_bundle()
                logger.debug(">>>>> local_path: {}".format(local_path))
                current_relative_path = self.fix_query_path(local_path)
                logger.debug(">>>>>>>>>>>>>> current_relative_path: {}".format(current_relative_path))
                file_name = os.path.basename(local_path)
                logger.debug(">>>>> file_name: {}".format(file_name))
                local_path = local_path.replace("\\", "/")

                # Search by file name
                filter_query = [['path_cache', 'contains', current_relative_path]]
                fields = ["entity", "path_cache", "path", "version_number", "name",
                          "description", "created_at", "created_by", "image",
                          "published_file_type", "task", "task.Task.content", "task.Task.sg_status_list"]

                published_files = sg.shotgun.find("PublishedFile", filter_query, fields,
                                                  order=[{'field_name': 'version_number', 'direction': 'desc'}])

                for published_file in published_files:
                    logger.debug(">>>>> published_file: ")
                    for k, v in published_file.items():
                        logger.debug(">>>>> {} : {}".format(k, v))
                    if "path" in published_file and "local_path" in published_file["path"]:
                        query_local_path = published_file["path"]["local_path"].replace("\\", "/")
                        if query_local_path.endswith(current_relative_path):
                            entity = published_file.get("entity", None)
                            if entity:
                                return entity, published_file

                msg = "Failed to retrieve the associated Shotgrid entity for the file located at {}".format(local_path)
                logger.debug(">>>>> {}".format(msg))

        return None, None


    def fix_query_path(self, current_relative_path):
        # Normalize the current relative path to ensure consistent path separators
        normalized_path = os.path.normpath(current_relative_path)

        # Split the path into drive and the rest
        drive, path_without_drive = os.path.splitdrive(normalized_path)

        # Remove leading slashes (if any) from the path without the drive
        trimmed_path = path_without_drive.lstrip(os.sep)
        trimmed_path = trimmed_path.replace("\\", "/")

        return trimmed_path

    def check_validity_by_path_parts(self, sg_item):
        """
        Check if the filepath leads to a valid ShotGrid entity
        :param sg_item: ShotGrid item information
        :return: entity and published file info if found, None otherwise
        """
        if not sg_item or "path" not in sg_item:
            return None, None

        logger.debug(f">>>>> Checking validity by path parts: sg_item: {sg_item}")
        local_path = sg_item["path"].get("local_path", None)
        if not local_path or not os.path.exists(local_path):
            msg = f"File does not exist locally: {local_path}"
            logger.debug(f">>>>> {msg}")
            # self.send_error_message(msg)
            # return None, None
        logger.debug(f">>>>> Checking validity by path parts: local_path: {local_path}")

        sg = sgtk.platform.current_bundle()

        # Extract information from the file path using the extract_info_from_path method
        asset_info = self.extract_info_from_path(local_path)
        logger.debug(f">>>>> Extracted asset info: {asset_info}")

        # Check if required information is extracted
        if not asset_info.get("project_tank_name") or not asset_info.get("code"):
            logger.debug("Unable to extract necessary information from the file path.")
            return None, None

        # Constructing the filter query based on the extracted information
        # Adjust this query as per your requirement and available fields in ShotGrid
        filter_query = [['project.Project.tank_name', 'is', asset_info["project_tank_name"]],
                        ['code', 'is', asset_info["code"]]]
        entity = sg.shotgun.find_one("Asset", filter_query, ['id', 'code', 'description', 'image', 'project'])

        if entity:
            logger.debug(f">>>>> Retrieved entity: {entity}")
            return entity, None

        msg = f"Failed to retrieve the associated ShotGrid entity for the file located at {local_path}"
        logger.debug(f">>>>> {msg}")
        return None, None

    def extract_info_from_path(self, local_path):
        """
        Extract information from the file path.
        This function parses the local_path to extract various asset-related information,
        such as the project tank name, asset library, asset type, asset section, and folder name.
        The 'code' is also constructed from these extracted parts.

        Example:
        Extracting info from path: local_path: Z:/ArkDepot/Mods/DinoDefense/Content/UI/Textures/_raw/TXR/backdrop.png
        Project Tank Name: ArkDepot
        sg_asset_library: DinoDefense
        sg_asset_type: Content
        sg_asset_section: UI
        sg_folder_name: Textures
        code: DinoDefense_UI_Textures
        """
        logger.debug(f">>>>> Extracting info from path: local_path: {local_path}")
        local_path = local_path.replace('//', '/', 1).replace("\\", "/")
        path_parts = local_path.split('/')  # Splitting the path using '/' as separator
        logger.debug(f">>>>> path_parts: {path_parts}")

        # Extracting asset information and constructing the 'code'
        asset_info = {
            "project_tank_name": path_parts[1],  # Extracting project tank name
            "sg_asset_library": path_parts[3],  # Extracting asset library
            "sg_asset_type": path_parts[4],  # Extracting asset type
            "sg_asset_section": path_parts[5],  # Extracting asset section
            "sg_folder_name": path_parts[6]  # Extracting folder name
        }
        asset_info["code"] = "_".join(
            [asset_info["sg_asset_library"], asset_info["sg_asset_section"], asset_info["sg_folder_name"]])

        return asset_info

    def convert_to_relative_path(self, absolute_path):
        # Split the path on ":/" and take the second part, if it exists
        parts = absolute_path.split(":/", 1)
        relative_path = parts[1] if len(parts) > 1 else absolute_path

        return relative_path


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


