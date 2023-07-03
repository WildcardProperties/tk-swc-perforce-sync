from sgtk.platform.qt import QtCore, QtGui
from tank.platform.qt5 import QtWidgets
from collections import OrderedDict
import datetime
from .date_time import create_publish_timestamp
import os
import sgtk
from sgtk.util import login
from .perforce_change import add_to_change

logger = sgtk.platform.get_logger(__name__)

#from tank.platform.qt5.QtWidgets import QTreeWidgetItemIterator

class SWCTreeView(QtWidgets.QTreeView):
    def __init__(self, parent=None, myp4=None):
        super().__init__(parent)

        self.p4 = myp4

        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QTreeView.InternalMove)

        self.setMinimumSize(QtCore.QSize(900, 500))
        self.setMaximumSize(QtCore.QSize(2000, 800))
        self.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)

        # self.setProperty("showDropIndicator", False)
        self.setProperty("showDropIndicator", True)
        self.setIconSize(QtCore.QSize(20, 20))
        self.setStyleSheet("QtWidgets.QTreeView::item { padding: 1px; }")
        self.setUniformRowHeights(True)
        self.setSelectionMode(self.selectionMode().ExtendedSelection)
        # self.setSelectionMode(self.selectionMode().MultiSelection)
        # self.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.setHeaderHidden(True)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        # self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.AllEditTriggers)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        # self.setDefaultDropAction(QtCore.Qt.MoveAction)

        self.setHeaderHidden(True)
        # self.setIndentation(10)
        

        # self.model = QtGui.QFileSystemModel(self)
        # self.model.setHorizontalHeaderLabels(['Change', 'Description','Date Submitted', 'Submitted by'])
        
        # self.expandAll()
        self.collapseAll()

    #def setModel(self, model):
    #    self.setModel(model)

    def dropEvent(self, event):
        if event.source() == self:
            # Retrieve the new parent's data (changelist number)
            target_index = self.indexAt(event.pos())
            target_data = target_index.data(QtCore.Qt.DisplayRole)
            logger.debug("<<<<<<<  New parent data (changelist number): {}".format(target_data))
            #change = target_index.data(QtCore.Qt.ToolTipRole)
            change = target_index.data(QtCore.Qt.UserRole)
            logger.debug("<<<<<<<  parent change is: {}".format(change))
            #change = 19110

            # Retrieve the source item's data (depot file path)
            for source_index in self.selectedIndexes():
                source_data = source_index.data(QtCore.Qt.DisplayRole)

                if source_data:
                    dragged_file = source_data.split("#")[0]
                    logger.debug("<<<<<<<  Source data (depot file): {}".format(dragged_file))
                    # Add the depot file to the new changelist
                    res = add_to_change(self.p4, change, dragged_file)

            # Add the depot file to the new changelist
            # add_to_changelist(source_data, target_data)

            # Call the base dropEvent implementation
            super().dropEvent(event)

    def dragEnterEvent(self, event):
        if event.source() == self:
            event.setDropAction(QtCore.Qt.MoveAction)
            event.accept()
        else:
            super().dragEnterEvent(event)

    def getSelectedIndexes(self):
        return self.selectionModel().selectedIndexes()

    def getSizeHint(self):
        return self.sizeHint()

    def setFirstColumn(self, i):
        return self.setFirstColumnSpanned(i, self.rootIndex(), True)

"""
def add_to_changelist(depot_file, changelist_number):
    # Use Perforce command line to add the depot file to the specified changelist
    cmd = ['p4', 'reopen', '-c', str(changelist_number), depot_file]
    subprocess.run(cmd)
"""

class TreeViewWidget(QtWidgets.QWidget):
    """
    TreeView Widget
    """
    selected_item_signal = QtCore.Signal(QtCore.QModelIndex)
    def __init__(self, data_dict=None, sorted=False, mode=None, p4=None):
        super(TreeViewWidget, self).__init__()
        self.data_dict = {}
        self.sorted = sorted
        self.mode = mode
        self.p4 = p4

        self._app = sgtk.platform.current_bundle()

        # set up layout
        self.main_layout = QtWidgets.QVBoxLayout()

        # major widgets

        self.tree_view = SWCTreeView(myp4=self.p4)
        self.model = QtGui.QStandardItemModel()
        self.tree_view.setModel(self.model)

        #self.tree_view = QtWidgets.QTreeView()
        #self.model = QtGui.QStandardItemModel()
        #self.tree_view.setModel(self.model)

        self.publish_dict = {}

        # Data
        if data_dict:
            self.data_dict = data_dict

        # Icons
        self.repo_root = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        submitted_image_path = os.path.join(self.repo_root, "icons/mode_switch_submitted_active.png")
        self.submitted_icon = QtGui.QIcon(QtGui.QPixmap(submitted_image_path))

        pending_image_path = os.path.join(self.repo_root, "icons/mode_switch_pending_active.png")
        self.pending_icon = QtGui.QIcon(QtGui.QPixmap(pending_image_path))

        p4_file_add_path = os.path.join(self.repo_root, "icons/p4_file_add.png")
        self.p4_file_add_icon = QtGui.QIcon(QtGui.QPixmap(p4_file_add_path))

        p4_file_edit_path = os.path.join(self.repo_root, "icons/p4_file_edit.png")
        self.p4_file_edit_icon = QtGui.QIcon(QtGui.QPixmap(p4_file_edit_path))

        p4_file_delete_path = os.path.join(self.repo_root, "icons/p4_file_delete.png")
        self.p4_file_delete_icon = QtGui.QIcon(QtGui.QPixmap(p4_file_delete_path))

        #self.pending_icon = QtGui.QIcon(":/res/pending.png")

    def select_items(self):
        #selected = self.tree_view.getSelectedIndexes()
        selected = self.tree_view.selectionModel().selectedIndexes()
        for index in selected:
            item = self.model.data(index)
            if item:
                for row in item.childCount():
                    child_item = item.child(row)
                    child_item.setSelected(True)

    def get_selected_publish_items(self):
        data_to_publish = []
        selected = self.tree_view.selectionModel().selectedIndexes()
        for index in selected:
            key = self.model.data(index)
            if key:
                if key in self.publish_dict:
                    sg_item = self.publish_dict.get(key, None)
                    if sg_item:
                        data_to_publish.append(sg_item)

        #logger.debug("<<<<<<<  self.publish_dict: {}".format(self.publish_dict))
        #logger.debug("<<<<<<<  data_to_publish: {}".format(data_to_publish))
        return data_to_publish

    def get_selected_publish_items_by_action(self):
        delete_data_to_publish = []
        other_data_to_publish = []
        selected = self.tree_view.selectionModel().selectedIndexes()
        for index in selected:
            key = self.model.data(index)
            if key:
                if key in self.publish_dict:
                    sg_item = self.publish_dict.get(key, None)
                    if sg_item:
                        action = self._get_action(sg_item)
                        if action not in ["delete"]:
                            other_data_to_publish.append(sg_item)
                        else:
                            delete_data_to_publish.append(sg_item)


        #logger.debug("<<<<<<<  self.publish_dict: {}".format(self.publish_dict))
        #logger.debug("<<<<<<<  data_to_publish: {}".format(data_to_publish))
        return other_data_to_publish, delete_data_to_publish

    def _get_action(self, sg_item):
        """
        Get action
        """
        action = sg_item.get("action", None)
        if not action:
            action = sg_item.get("headAction", None)
        return action


    def get_all_publish_items(self):
        data_to_publish = []
        #selected = self.tree_view.getSelectedIndexes()
        selected = self.tree_view.selectionModel().selectedIndexes()
        for index in selected:
            key = self.model.data(index)
            if key:
                if key in self.publish_dict:
                    sg_item = self.publish_dict.get(key, None)
                    if sg_item:
                        data_to_publish.append(sg_item)

        #logger.debug("<<<<<<<  self.publish_dict: {}".format(self.publish_dict))
        #logger.debug("<<<<<<<  data_to_publish: {}".format(data_to_publish))
        return data_to_publish


    def get_treeview_widget(self):
        #return self.main_layout
        return self.tree_view

    def populate_treeview_widget(self):
        """
        Populate treeview widget with data from data_dict
        """
        self.publish_dict = {}
        parent_icon = self.submitted_icon
        node_dictionary = None

        if self.mode in ["submitted"]:
            node_dictionary = self._get_change_dictionary_submitted(self.data_dict)
            parent_icon = self.submitted_icon
        elif self.mode in ["pending"]:
            node_dictionary = self._get_change_dictionary_pending(self.data_dict)
            parent_icon = self.pending_icon

        #logger.debug("<<<<<<<  node_dictionary: {}".format(node_dictionary))

        for i, key in enumerate(node_dictionary.keys()):
            if key:
                logger.debug("<<<<<<<  key: {}".format(key))
                key_str = str(key)
                change_item = QtGui.QStandardItem(key_str)
                # change_item must allow drops, but cannot be dragged
                change_item.setFlags(
                    (change_item.flags() | QtCore.Qt.ItemFlag.ItemIsDropEnabled) & ~QtCore.Qt.ItemFlag.ItemIsDragEnabled
                )

                msg = "Changelist# {}".format(key)
                change_item.setToolTip(msg)
                change_item.setData(key, QtCore.Qt.UserRole)
                change_item.setSizeHint(QtCore.QSize(0, 25))
                #change_item.setTextAlignment(QtCore.Qt.AlignVCenter)
                change_item.setEditable(False)
                self.model.appendRow([change_item])

                #self.tree_view.setFirstColumn(i)
                self.tree_view.setFirstColumnSpanned(i, self.tree_view.rootIndex(), True)
                enable_change_item = False
                if node_dictionary[key]:
                    if self.mode in ["pending"]:
                        if len(node_dictionary[key]) > 1:
                            parent_icon = self.pending_icon
                        else:
                            parent_icon = self.submitted_icon

                    for j, sg_item in enumerate(node_dictionary[key]):
                        if 'changeListInfo' in sg_item:
                            publish_time_txt = self._get_publish_time_info(sg_item)
                            user_name_txt = self._get_user_name_info(sg_item)
                            description_txt = self._get_description_info(sg_item)

                            msg = "{} \t {} \t {} \t {}".format(key, publish_time_txt, user_name_txt, description_txt)
                            change_item.setText(msg)
                        else:

                            depot_path = sg_item.get("depotFile", None)
                            head_rev = sg_item.get("headRev", 0)
                            is_published = sg_item.get("Published", None)
                            if not is_published:
                                enable_change_item = True
                            action = self._get_action(sg_item)
                            action_icon = self.get_action_icon(action)
                            if depot_path:
                                depot_str = "{}#{}".format(depot_path, head_rev)
                                depot_item = QtGui.QStandardItem(depot_str)
                                # depot_item can be dragged, but must not accept drops
                                depot_item.setFlags(
                                    (depot_item.flags() | QtCore.Qt.ItemFlag.ItemIsDragEnabled) & ~QtCore.Qt.ItemFlag.ItemIsDropEnabled
                                )
                                depot_item.setIcon(action_icon)
                                depot_item.setData(key, QtCore.Qt.UserRole)
                                #depot_item.setToolTip(key)
                                #depot_item.setSizeHint(self.tree_view.getSizeHint())
                                depot_item.setSizeHint(self.tree_view.sizeHint())
                                #depot_item.setTextAlignment(QtCore.AlignVCenter)
                                depot_item.setTextAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
                                change_item.appendRow(depot_item)

                                if self.mode in ["submitted"]:
                                    if is_published:
                                        depot_item.setEnabled(False)
                                    else:
                                        if depot_str not in self.publish_dict:
                                            self.publish_dict[depot_str] = sg_item
                                elif self.mode in ["pending"]:
                                    if depot_str not in self.publish_dict:
                                        self.publish_dict[depot_str] = sg_item
                            if self.mode in ["submitted"] and j == 0:
                                publish_time_txt = self._get_publish_time_info(sg_item)
                                user_name_txt = self._get_user_name_info(sg_item)
                                description_txt = self._get_description_info(sg_item)

                                msg = "{} \t {} \t {} \t {}".format(key, publish_time_txt, user_name_txt, description_txt)
                                change_item.setText(msg)

                #change_item.setTextAlignment(QtCore.AlignVCenter)
                #change_item.setTextAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

                if parent_icon is not None:
                    change_item.setIcon(parent_icon)
                #change_item.setSelectable(False)
                if self.mode in ["submitted"]:
                    if enable_change_item:
                        change_item.setEnabled(True)
                    else:
                        change_item.setEnabled(False)
                elif self.mode in ["pending"]:
                    change_item.setEnabled(True)


    def _create_perforce_ui(self, data_dict, sorted=None):
        # publish list
        publish_widget = QtWidgets.QWidget()
        publish_layout = QtWidgets.QVBoxLayout()

        # Create a proxy model.
        proxy_model = QtGui.QSortFilterProxyModel(self)
        proxy_model.setSourceModel(model)

        # Impose and keep the sorting order on the default display role text.
        proxy_model.sort(0)
        proxy_model.setDynamicSortFilter(True)

        # Create a Tree View
        view = QtGui.QTreeView(tab)
        publish_layout.addWidget(view)

        # Configure the view.
        view.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        view.setProperty("showDropIndicator", False)
        view.setIconSize(QtCore.QSize(20, 20))
        view.setStyleSheet("QTreeView::item { padding: 6px; }")
        view.setUniformRowHeights(True)
        view.setHeaderHidden(True)
        view.setModel(proxy_model)

        publish_list = self._create_publish_layout(data_dict, sorted)

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
                    change_txt = self._get_change_list_info(sg_item)
                    change_label.setText(change_txt)

                    publish_time_label = QtWidgets.QLabel()
                    publish_time_label.setMinimumWidth(200)
                    publish_time_label.setMaximumWidth(200)
                    publish_time_txt = self._get_publish_time_info(sg_item)
                    publish_time_label.setText(publish_time_txt)

                    user_name_label = QtWidgets.QLabel()
                    user_name_label.setMinimumWidth(150)
                    user_name_label.setMaximumWidth(150)
                    user_name_txt = self._get_user_name_info(sg_item)
                    user_name_label.setText(user_name_txt)

                    description_label = QtWidgets.QLabel()
                    description_label.setMinimumWidth(400)
                    user_name_label.setMaximumWidth(2000)
                    description_txt = self._get_description_info(sg_item)
                    description_label.setText(description_txt)

                    info_layout.addWidget(change_label)
                    info_layout.addWidget(publish_time_label)
                    info_layout.addWidget(user_name_label)
                    info_layout.addWidget(description_label)
                    #logger.debug("<<<<<<<  sg_item is: {}".format(sg_item))

                    is_published = sg_item.get("Published", None)
                    #logger.debug("<<<<<<<  sg_item published is: {}".format(is_published))
                    if is_published:
                        info_layout.setEnabled(False)
                    publish_layout.addLayout(info_layout)

                    current_publish = publish_item[3]
            publish_layout.addLayout(publish_item[1])
        publish_widget.setLayout(publish_layout)

        for publish in publish_list:
            if publish:
                publish_layout.addLayout(publish[1])
        publish_widget.setLayout(publish_layout)


        return publish_widget, publish_list
        # Submitted Scroll Area
        # self.ui.submitted_scroll.setWidget(publish_widget)
        #self.ui.submitted_scroll.setVisible(True)

    def _create_publish_layout(self, data_dict, sorted):
        publish_list = []
        if not sorted:
            node_dictionary = self._get_change_dictionary_submitted(data_dict)
        else:
            node_dictionary = data_dict
        #logger.debug("<<<<<<<  node_dictionary: {}".format(node_dictionary))
        for key in node_dictionary.keys():
            if key:
                # logger.debug("<<<<<<<  key: {}".format(key))
                publish_label = QtWidgets.QLabel()
                publish_label.setText(str(key))
                for sg_item in node_dictionary[key]:
                    if sg_item:
                        # logger.debug("<<<<<<<  sg_item: {}".format(sg_item))
                        # depot_path = self._get_depot_path(sg_item)
                        depot_path = sg_item.get("depotFile", None)
                        is_published = sg_item.get("Published", None)

                        action = self._get_action(sg_item)
                        #action_icon = self.get_action_icon(action)

                        publish_layout = QtWidgets.QHBoxLayout()
                        publish_checkbox = QtWidgets.QCheckBox()
                        if is_published:
                            publish_checkbox.setChecked(True)

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

                        if is_published:
                            publish_checkbox.setEnabled(False)
                            action_line_edit.setEnabled(False)
                            publish_path_line_edit.setEnabled(False)
                        else:
                            msg = "<span style='color:#2C93E2'>Check files in the Pending view then click <i>Submit Files</i>to publish them using the <i>Shotgrid Publisher</i>...</span>"
                            publish_checkbox.setToolTip(msg)
                            publish_path_line_edit.setToolTip(msg)


                        publish_list.append((sg_item, publish_layout, publish_checkbox, key))
        return publish_list

    def get_action_icon(self, action):
        action_icon = self.p4_file_add_icon
        if action:
            if action == "edit":
                action_icon  = self.p4_file_edit_icon
            elif action == "delete":
                action_icon = self.p4_file_delete_icon
            else:
                action_icon = self.p4_file_add_icon
        return action_icon


    def _get_change_dictionary_submitted(self, data_dict):
        """
        Creates dictionary for every changelist and all its depot files
        key: changelist number
        value: sorted list of depotfiles
        :return: dictionary
        """
        change_dict = {}

        if data_dict:
            for sg_item in data_dict.values():
                if sg_item:
                    key = sg_item.get("headChange", None)
                    if key:
                        if key not in change_dict:
                            change_dict[key] = []
                        change_dict[key].append(sg_item)

        change_dict_sorted = OrderedDict(sorted(change_dict.items()))

        # for key in change_dict_sorted:
        #   change_dict_sorted[key] = sorted(change_dict_sorted[key])
        # print(change_dict_sorted)
        return change_dict_sorted

    def _get_change_dictionary_pending(self, data_dict):
        """
        Creates dictionary for every changelist and all its depot files
        key: changelist number
        value: sorted list of depotfiles
        :return: dictionary
        """

        change_dict_sorted = OrderedDict(sorted(data_dict.items()))

        # for key in change_dict_sorted:
        #   change_dict_sorted[key] = sorted(change_dict_sorted[key])
        # print(change_dict_sorted)
        return change_dict_sorted


    def _get_action(self, sg_item):
        """
        Get action
        """
        action = sg_item.get("action", None)
        if not action:
            action = sg_item.get("headAction", None)
        return action

    def _get_depot_path(self, sg_item):
        """
        Get depot path
        """
        depot_file = sg_item.get("depotFile", None)
        head_rev = sg_item.get("headRev", None)
        if head_rev:
            depot_file = "{}#{}".format(depot_file, head_rev)
        return depot_file

    def _get_change_list_info(self, sg_item):
        """
        Get change list info
        """
        change_txt = ""
        change_list = sg_item.get("change", None)
        if not change_list:
            change_list = sg_item.get("headChange", None)
        if change_list:
            change_txt += "<span style='color:#2C93E2'><B>Change List: </B></span>"
            change_txt += "<span><B>{}   </B></span> ".format(change_list)
            # change_txt += "   \t"
        return change_txt

    def _get_publish_time_info(self, sg_item):
        publish_time_txt = ""

        publish_time = self._get_publish_time(sg_item)
        if not publish_time:
            return ""
        #if publish_time:
        #    publish_time_txt += "<span style='color:#2C93E2'><B>Creation Time: </B></span>"
        #    publish_time_txt += "<span><B>{}   </B></span>".format(publish_time)

        return publish_time

    def _get_user_name_info(self, sg_item):
        user_name_txt = ""

        user_name = self._get_publish_user(sg_item)
        #if user_name:
        #    user_name_txt += "<span style='color:#2C93E2'><B>User: </B></span>"
        #    user_name_txt += "<span><B>{}   </B></span>\t\t".format(user_name)
        return user_name

    def _get_description_info(self, sg_item):
        description_txt = ""

        description = sg_item.get("description", None)
        #if description:
        #    description_txt += "<span style='color:#2C93E2'><B>Description: </B></span>"
        #    description_txt += "<span><B>{}</B></span>\t\t".format(description)

        return description

    def _get_publish_time(self, sg_item):
        publish_time = None
        dt = sg_item.get("headTime", None)
        # logger.debug(">>>>> dt is: {}".format(dt))
        if dt:
            publish_time = create_publish_timestamp(dt)
        return publish_time

    def _get_publish_user(self, sg_item):
        publish_user, user_name = None, None

        p4_user = sg_item.get("p4_user", None)
        if p4_user:
            publish_user = self._app.shotgun.find_one('HumanUser',
                                                      [['sg_p4_user', 'is', p4_user]],
                                                      ["id", "type", "email", "login", "name", "image"])
        # logger.debug(">>> Publish user is: {}".format(publish_user))
        if not publish_user:
            action_owner = sg_item.get("actionOwner", None)
            if action_owner:
                publish_user = self._app.shotgun.find_one('HumanUser',
                                                          [['sg_p4_user', 'is', action_owner]],
                                                          ["id", "type", "email", "login", "name", "image"])
        # logger.debug(">>>> Publish user is: {}".format(publish_user))
        if not publish_user:
            publish_user = login.get_current_user(self._app.sgtk)

        # logger.debug(">>>>> Publish user is: {}".format(publish_user))
        if publish_user:
            user_name = publish_user.get("name", None)

        return user_name
