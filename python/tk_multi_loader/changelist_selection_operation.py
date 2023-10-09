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
            change = self.change
            desc = self.changelists_description.text()
            if change:
                for sg_item, action in self.selected_actions:
                    perform_actions = PerformActions(self.p4, sg_item, action, change, desc)
                    self.new_sg_item = perform_actions.run()

                self.parent.refresh_publish_data()

        except Exception as e:
            logger.debug("Error setting changelist: {}".format(e))
        self.close()

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


