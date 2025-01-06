""" Widgets to list episodes, sequences and changelists with load options """

# python
import os


from sgtk.platform.qt import QtCore
for name, cls in QtCore.__dict__.items():
    if isinstance(cls, type): globals()[name] = cls

from sgtk.platform.qt import QtGui
for name, cls in QtGui.__dict__.items():
    if isinstance(cls, type): globals()[name] = cls


class ChangelistSelectionWidget(QDialog):
    """
    Changelist Select Widget to display a list of changelists
    """

    def __init__(self, parent=None):
        """
        Constructor
        :param parent: The parent Qt application
        """

        super(ChangelistSelectionWidget, self).__init__(parent)

        # Setup the UI
        self.setObjectName('changlists_selection_widget')
        self.setMinimumSize(400, 550)

        # Layout
        # Main Layout
        self.main_layout = QVBoxLayout()

        # Content Layout
        self.load_content_layout = QHBoxLayout()
        self.load_content_layout.setAlignment(Qt.AlignCenter)
        self.load_content_layout.layout().setContentsMargins(10, 10, 10, 20)

        self.load_buttons_layout = QHBoxLayout()
        self.load_buttons_layout.setAlignment(Qt.AlignCenter)
        self.load_buttons_layout.layout().setContentsMargins(10, 10, 10, 20)

        # ------------------------------------------------------------------------------------
        # Load Changelists Layout
        self.load_changelists_frame = QFrame()
        #self.load_changelists_frame.setMaximumWidth(300)
        self.load_changelists_frame.setObjectName('changelists_frame')
        self.load_changelists_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.load_changelists_frame.setStyleSheet(
            '''
            QFrame#changelists_frame {
            padding: 0px;
            border-radius: 8px;
            border-style: solid;
            border-width: 1px 1px 1px 1px;
            }'''
        )
        self.load_changelists_layout = QVBoxLayout()
        self.load_changelists_widget_layout = QVBoxLayout()
        self.load_changelists_frame.setLayout(self.load_changelists_widget_layout)

        # Widgets
        # Shot Selection Label
        self.changelists_selection_label = QLabel('Pending changelists')
        self.changelists_selection_label.setStyleSheet("font: 10pt;")
        #self.changelists_selection_label.setAlignment(Qt.AlignLeft)

        
        # changelists list
        self.changelists_lst = QListWidget()
        #self.changelists_lst.setFixedHeight(400)
        self.changelists_lst.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.changelists_lst.setSelectionMode(QAbstractItemView.SingleSelection)
        self.changelists_lst.setToolTip('Select a changelist')
        # Set changelists_lst row height
        self.changelists_lst.setStyleSheet("QListView::item { height: 30px; }")


        # changelists description
        self.changelists_desc_label = QLabel('Changelist description')
        self.changelists_description = QLineEdit()

        
        # Load Shot Button
        self.new_button = QPushButton('Add files to a new changelist')
        self.new_button.setFixedWidth(220)
        self.new_button.setFixedHeight(30)
        # Set tooltip for new_button
        self.new_button.setToolTip('Based on the given description, create a new changelist and incorporate the files.')
        self.ok_button = QPushButton('Add files to the selected changelist')
        self.ok_button.setToolTip('Add the files to the selected changelist')
        self.ok_button.setFixedWidth(220)
        self.ok_button.setFixedHeight(30)

        # Setup Layouts
        self.load_changelists_layout.addWidget(self.load_changelists_frame)
        self.load_changelists_widget_layout.addWidget(self.changelists_selection_label)
        self.load_changelists_widget_layout.addWidget(self.changelists_lst)
        self.load_changelists_widget_layout.addWidget(self.changelists_desc_label)
        self.load_changelists_widget_layout.addWidget(self.changelists_description)


        # Load Button
        self.load_buttons_layout.addWidget(self.new_button, alignment=Qt.AlignCenter)
        self. load_buttons_layout.addWidget(self.ok_button, alignment=Qt.AlignCenter)


       
        # ----------------------------------------------------------------------------------------------------
        # Add to Main Layout
        self.load_content_layout.addLayout(self.load_changelists_layout)

        self.main_layout.addLayout(self.load_content_layout)
        self.main_layout.addLayout(self.load_buttons_layout)

        self.setLayout(self.main_layout)
