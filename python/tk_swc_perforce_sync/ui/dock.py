from PyQt5 import QtWidgets, QtCore

class YourMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(YourMainWindow, self).__init__(parent)

        # Main splitter to organize layout horizontally
        self.splitter = QSplitter(self)
        self.setCentralWidget(self.splitter)

        # Simple widget for file details
        self.file_details = QWidget(self.splitter)
        self.file_details_layout = QVBoxLayout(self.file_details)
        self.file_details_layout.addWidget(QLabel("File Details Area"))

        # QDockWidget to host the panel
        self.panel_dock_widget = QDockWidget("Panel Details", self)
        self.panel_dock_widget.setObjectName("detailsDockWidget")
        self.panel_dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        # QWidget to serve as the dock widget's main widget
        self.panel_widget = QWidget()
        self.panel_dock_widget.setWidget(self.panel_widget)
        self.panel_layout = QVBoxLayout(self.panel_widget)

        # Add the QDockWidget to the main window
        self.addDockWidget(Qt.RightDockWidgetArea, self.panel_dock_widget)

        # Tab widget to manage different views, though might not be needed with docking
        self.details_tab = QTabWidget(self.splitter)
        self.details_tab.addTab(self.file_details, "Files")

        # Signal connection for tab change might be redundant with dock but kept for any additional tabs
        self.details_tab.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index):
        # Check if the newly selected tab is the "Panel" tab (if still using tabs)
        if self.details_tab.tabText(index) == "Panel":
            self.load_shotgun_panel()

    def load_shotgun_panel(self):
        # Get or create the Shotgun panel widget
        shotgun_panel_widget = self.get_shotgun_panel_widget()
        # Add the widget to the panel layout if it's not already added
        if shotgun_panel_widget not in self.get_widgets_in_layout(self.panel_layout):
            self.clear_layout(self.panel_layout)
            self.panel_layout.addWidget(shotgun_panel_widget)

    def get_shotgun_panel_widget(self):
        # Simulated function to get the tk-multi-shotgunpanel widget
        # Replace this with the actual call to your Shotgun application
        return QLabel("Shotgun Panel Widget")

    def clear_layout(self, layout):
        # Function to clear all widgets from a layout
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def get_widgets_in_layout(self, layout):
        # Helper function to retrieve widgets in a layout
        return [layout.itemAt(i).widget() for i in range(layout.count())]

# Setup and run the application
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = YourMainWindow()
    window.show()
    sys.exit(app.exec_())
