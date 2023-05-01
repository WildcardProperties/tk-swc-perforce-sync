import os
from sgtk.platform.qt import QtCore, QtGui
from tank.platform.qt5 import QtWidgets
from .publish_item import PublishItem

import datetime
from .date_time import create_human_readable_timestamp, create_publish_timestamp

# Python collections
import collections

import sgtk
from sgtk.util import login
logger = sgtk.platform.get_logger(__name__)

class PublishFilesUI(QtWidgets.QDialog):
    """
    Publish Files UI
    """
    
    WINDOW_TITLE = 'Publish Files'

    def __init__(self, parent_class=None, parent_window=None, sg_data_to_publish=None, sg_entity=None):

        super(PublishFilesUI, self).__init__(parent_window)


        # Setup window
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setMinimumSize(1000, 800)
        self.setMaximumSize(1200, 1200)

        # Shotgrid
        self.app = sgtk.platform.current_bundle()

        # Publish
        self.dialog = parent_class
        self.publish_list = []
        self.sg_data_to_publish = sg_data_to_publish
        self.sg_entity = sg_entity

        # Main layout
        self.main_layout = QtWidgets.QVBoxLayout()

        # Select all layout
        self.select_all_layout = QtWidgets.QHBoxLayout()
        self.deselect_all_button = QtWidgets.QPushButton('Deselect All')
        self.select_all_button = QtWidgets.QPushButton('Select All')
        self.select_all_layout.addWidget(self.deselect_all_button)
        self.select_all_layout.addWidget(self.select_all_button)

        # Button layout
        self.button_layout = QtWidgets.QHBoxLayout()
        self.button_layout.layout().setContentsMargins(0, 15, 0, 2)
        self.cancel_button = QtWidgets.QPushButton('Close')
        self.add_publish_files_button = QtWidgets.QPushButton('Publish Files')

        self.button_layout.addWidget(self.cancel_button)
        self.button_layout.addWidget(self.add_publish_files_button)

        # log layout
        self.log_layout = QtWidgets.QHBoxLayout()
        self.log_window = QtWidgets.QTextBrowser()
        self.log_window.verticalScrollBar().setValue(self.log_window.verticalScrollBar().maximum())
        self.log_window.setMinimumHeight(100)
        self.log_window.setMaximumHeight(150)
        self.log_layout.addWidget(self.log_window)

        # publish list
        publish_widget = QtWidgets.QWidget()
        publish_layout = QtWidgets.QVBoxLayout()
        publish_list = self.create_publish_layout()

        current_publish = ''
        for publish_item in publish_list:
            if publish_item:
                if publish_item[3] != current_publish:
                    sg_item = publish_item[0]
                    info_layout = QtWidgets.QHBoxLayout()
                    info_layout.layout().setContentsMargins(0, 15, 0, 5)

                    change_label = QtWidgets.QLabel()
                    change_label.setMinimumWidth(120)
                    change_label.setMaximumWidth(120)
                    change_txt = self.get_change_list_info(sg_item)
                    change_label.setText(change_txt)

                    publish_time_label = QtWidgets.QLabel()
                    publish_time_label.setMinimumWidth(200)
                    publish_time_label.setMaximumWidth(200)
                    publish_time_txt = self.get_publish_time_info(sg_item)
                    publish_time_label.setText(publish_time_txt)

                    user_name_label = QtWidgets.QLabel()
                    user_name_label.setMinimumWidth(150)
                    user_name_label.setMaximumWidth(150)
                    user_name_txt = self.get_user_name_info(sg_item)
                    user_name_label.setText(user_name_txt)

                    description_label = QtWidgets.QLabel()
                    description_label.setMinimumWidth(400)
                    description_txt = self.get_description_info(sg_item)
                    description_label.setText(description_txt)

                    info_layout.addWidget(change_label)
                    info_layout.addWidget(publish_time_label)
                    info_layout.addWidget(user_name_label)
                    info_layout.addWidget(description_label)
                    publish_layout.addLayout(info_layout)

                    current_publish = publish_item[3]
            publish_layout.addLayout(publish_item[1])
        publish_widget.setLayout(publish_layout)

        for publish in publish_list:
            if publish:
                publish_layout.addLayout(publish[1])
        publish_widget.setLayout(publish_layout)

        # Scroll Area
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(False)
        self.scroll.setWidget(publish_widget)

        self.main_layout.addWidget(self.scroll)
        self.main_layout.addLayout(self.select_all_layout)
        self.main_layout.addLayout(self.button_layout)
        self.main_layout.addLayout(self.log_layout)

        self.setLayout(self.main_layout)

        # Connections
        self.deselect_all_button.clicked.connect(lambda: self.deselect_all_outputs(publish_list))
        self.select_all_button.clicked.connect(lambda: self.select_all_outputs(publish_list))
        self.cancel_button.clicked.connect(self.close)
        self.add_publish_files_button.clicked.connect(lambda: self.publish_files(publish_list))

        msg = "\n <span style='color:#2C93E2'>Select files to publish</span> \n"
        self.add_log(msg, 2)

    def get_change_list_info(self, sg_item):
        """
        Get change list info
        """
        change_txt = ""

        change_list = sg_item.get("headChange", None)
        if change_list:
            change_txt += "<span style='color:#2C93E2'><B>Change List: </B></span>"
            change_txt += "<span><B>{}   </B></span> ".format(change_list)
            # change_txt += "   \t"
        return change_txt

    def get_publish_time_info(self, sg_item):
        publish_time_txt = ""

        publish_time = self.get_publish_time(sg_item)
        if publish_time:
            publish_time_txt += "<span style='color:#2C93E2'><B>Creation Time: </B></span>"
            publish_time_txt += "<span><B>{}   </B></span>".format(publish_time)
        return publish_time_txt

    def get_user_name_info(self, sg_item):
        user_name_txt = ""

        user_name = self.get_publish_user(sg_item)
        if user_name:
            user_name_txt += "<span style='color:#2C93E2'><B>User: </B></span>"
            user_name_txt += "<span><B>{}   </B></span>\t\t".format(user_name)
        return user_name_txt

    def get_description_info(self, sg_item):
        description_txt = ""

        description = sg_item.get("description", None)
        if description:
            description_txt += "<span style='color:#2C93E2'><B>Description: </B></span>"
            description_txt += "<span><B>{}</B></span>\t\t".format(description)

        return description_txt


    def get_publish_time(self, sg_item):
        publish_time= None
        dt = sg_item.get("headTime", None)
        # logger.debug(">>>>> dt is: {}".format(dt))
        if dt:
            publish_time = create_publish_timestamp(dt)
        return publish_time

    def get_publish_user(self, sg_item):
        publish_user, user_name = None, None

        p4_user = sg_item.get("p4_user", None)
        if p4_user:
            publish_user = self.app.shotgun.find_one('HumanUser',
                                              [['sg_p4_user', 'is', p4_user]],
                                              ["id", "type", "email", "login", "name", "image"])
        # logger.debug(">>> Publish user is: {}".format(publish_user))
        if not publish_user:
            action_owner = sg_item.get("actionOwner", None)
            if action_owner:
                publish_user = self.app.shotgun.find_one('HumanUser',
                                                     [['sg_p4_user', 'is', action_owner]],
                                                     ["id", "type", "email", "login", "name", "image"])
        # logger.debug(">>>> Publish user is: {}".format(publish_user))
        if not publish_user:
            publish_user = login.get_current_user(self.app.sgtk)

        # logger.debug(">>>>> Publish user is: {}".format(publish_user))
        if publish_user:
            user_name = publish_user.get("name", None)

        return user_name

    def set_publish_files(self, sg_data_list):
        self.sg_data_to_publish = sg_data_list
        #logger.debug("<<<<<<<  Setting SG data: {}".format(self.sg_data_to_publish))

    def set_entity(self, sg_entity):
        self.sg_entity = sg_entity
        #logger.debug("<<<<<<<  Setting SG entity: {}".format(self.sg_entity))

    def get_change_dictionary(self):
        """
        Creates dictionary for every changelist and all its depot files
        key: changelist number
        value: sorted list of depotfiles
        :return: dictionary
        """
        change_dict = {}
        if self.sg_data_to_publish:
            for sg_item in self.sg_data_to_publish:
                if sg_item:
                    key = sg_item.get("headChange", None)
                    if key:
                        if key not in change_dict:
                            change_dict[key] = []
                        #depot_file = sg_item.get("depotFile", None)
                        #if depot_file:
                        change_dict[key].append(sg_item)

        change_dict_sorted = collections.OrderedDict(sorted(change_dict.items()))

        #for key in change_dict_sorted:
        #   change_dict_sorted[key] = sorted(change_dict_sorted[key])
        # print(change_dict_sorted)
        return change_dict_sorted
        
    def create_publish_layout(self):
        publish_list = []
        node_dictionary = self.get_change_dictionary()
        logger.debug("<<<<<<<  node_dictionary: {}".format(node_dictionary))
        for key in node_dictionary.keys():
            if key:
                logger.debug("<<<<<<<  key: {}".format(key))
                publish_label = QtWidgets.QLabel()
                publish_label.setText(str(key))
                for sg_item in node_dictionary[key]:
                    if sg_item:
                        logger.debug("<<<<<<<  sg_item: {}".format(sg_item))
                        depot_path = self.get_depot_path(sg_item)
                        # depot_file_name = self.get_depot_file_name(depot_path, sg_item)
                        action = self.get_action(sg_item)

                        publish_layout = QtWidgets.QHBoxLayout()
                        publish_checkbox = QtWidgets.QCheckBox()

                        action_line_edit = QtWidgets.QLineEdit()
                        action_line_edit.setMinimumWidth(80)
                        action_line_edit.setMaximumWidth(80)
                        action_line_edit.setText('{}'.format(action))
                        # action_line_edit.setEnabled(False)

                        publish_path_line_edit = QtWidgets.QLineEdit()
                        publish_path_line_edit.setMinimumWidth(750)
                        publish_path_line_edit.setText('{}'.format(depot_path))
                        # publish_path_line_edit.setEnabled(False)

                        publish_layout.addWidget(publish_checkbox)
                        publish_layout.addWidget(action_line_edit)
                        publish_layout.addWidget(publish_path_line_edit)

                        publish_list.append((sg_item, publish_layout, publish_checkbox, key))
        return publish_list

    def get_action(self, sg_item):
        """
        Get action
        """
        head_action = sg_item.get("headAction", None)
        if not head_action:
            head_action = "N/A"
        return head_action

    def get_local_path(self, sg_item):
        """
        Get local path
        """
        # publish_path
        publish_path = None
        if 'path' in sg_item:
            publish_path = sg_item['path'].get('local_path', None)
        return publish_path

    def get_depot_path(self, sg_item):
        """
        Get depot path
        """
        depot_file = sg_item.get("depotFile", None)
        head_rev = sg_item.get("headRev", None)
        if head_rev:
            depot_file = "{}#{}".format(depot_file, head_rev)
        return depot_file
    
    def get_depot_file_name(self, publish_path, sg_item):
        """
        Get depot filename
        """
        depot_file_name = sg_item.get("code", None)
        if publish_path and not depot_file_name:
            depot_file_name = os.path.basename(publish_path)
        
        return depot_file_name

    def publish_files(self, publish_list):
        self.add_publish_files(publish_list)
        self.publish_depot_data()
        self.dialog.post_publish()
        # self.close()

    def add_publish_files(self, publish_list):
        """
        Adds checked publishs to list for Deadline Submitter
        :param publish_list: publishs(loadlayer) in the current scene
        """
        
        for publish_item in publish_list:
            if publish_item:
                sg_item = publish_item[0]
                check_box = publish_item[2]

                if check_box.isChecked():
                    self.publish_list.append(sg_item)
        #logger.debug("<<<<<<<<  Publish list {}".format(self.publish_list))



    def publish_depot_data(self):
        """
        Publish Depot Data
        """

        if self.publish_list:
            msg = "\n <span style='color:#2C93E2'>Sending unpublished depot files to the Shotgrid Publisher...</span> \n"
            self.add_log(msg, 2)
            for sg_item in self.publish_list:
                sg_item["entity"] = self.sg_entity
                if 'path' in sg_item:
                    file_to_publish = sg_item['path'].get('local_path', None)
                    msg = "Publishing file: {}...".format(file_to_publish)
                    self.add_log(msg, 4)

                    publisher = PublishItem(sg_item)
                    publish_result = publisher.publish_file()
                    if publish_result:
                        logger.debug("New data is: {}".format(publish_result))
            msg = "\n <span style='color:#2C93E2'>Publishing is complete. You may publish other files or close this window.</span> \n"
            self.add_log(msg, 2)
            self.publish_list = []

    def add_log(self, msg, flag):
        if flag <= 2:
            msg = "\n{}\n".format(msg)
        else:
            msg = "{}".format(msg)
        self.log_window.append(msg)
        #if flag < 4:
        #    logger.debug(msg)
        self.log_window.verticalScrollBar().setValue(self.log_window.verticalScrollBar().maximum())
        QtCore.QCoreApplication.processEvents()

    def select_all_outputs(self, output_list):
        """
        Select all render outputs
        """
        for output in output_list:
            if output:
                check_box = output[2]
                check_box.setChecked(True)

    def deselect_all_outputs(self, output_list):
        """
        Select all render outputs
        """
        for output in output_list:
            if output:
                check_box = output[2]
                check_box.setChecked(False)
                
                
        
        
        
