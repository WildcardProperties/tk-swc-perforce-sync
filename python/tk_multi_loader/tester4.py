def _setup_column_view(self):
    # ... Existing code ...

    # Create a table model and set headers
    self.column_view_model = QtGui.QStandardItemModel(0, len(headers))
    self.column_view_model.setHorizontalHeaderLabels(headers)

    # Create a proxy model for sorting and grouping
    self.perforce_proxy_model = QtGui.QSortFilterProxyModel()
    self.perforce_proxy_model.setSourceModel(self.column_view_model)

    self.ui.column_view.setModel(self.perforce_proxy_model)

    # Set the header to be clickable for sorting
    self.ui.column_view.horizontalHeader().setSectionsClickable(True)
    self.ui.column_view.horizontalHeader().setSortIndicatorShown(True)

    # Sort by the first column initially
    self.ui.column_view.sortByColumn(0, QtCore.Qt.AscendingOrder)

    # Grouping by "Entity Sub-Folder"
    self.ui.column_view.setSortingEnabled(True)
    # self.ui.column_view.sortByColumn(12, QtCore.Qt.AscendingOrder)

    header = self.ui.column_view.horizontalHeader()
    for col in range(len(headers)):
        header.setSectionResizeMode(col, QtWidgets.QHeaderView.ResizeToContents)

    self.ui.column_view.clicked.connect(self.on_column_view_row_clicked)

    self._create_column_view_context_menu()

    # Add the "Group by folder" menu item
    self.group_by_folder_action = QtGui.QAction("Group by folder", self.ui.column_view)
    self.group_by_folder_action.triggered.connect(self.group_by_folder)
    self.ui.column_view.horizontalHeader().addAction(self.group_by_folder_action)

    # Add the "Group by user" menu item
    self.group_by_user_action = QtGui.QAction("Group by user", self.ui.column_view)
    self.group_by_user_action.triggered.connect(self.group_by_user)
    self.ui.column_view.horizontalHeader().addAction(self.group_by_user_action)

    # Add the "Group by action" menu item
    self.group_by_action_action = QtGui.QAction("Group by action", self.ui.column_view)
    self.group_by_action_action.triggered.connect(self.group_by_action)
    self.ui.column_view.horizontalHeader().addAction(self.group_by_action_action)
