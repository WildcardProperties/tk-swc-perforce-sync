def _populate_column_view_widget(self):
    # self._publish_model.hard_refresh()
    self.column_view_dict = {}
    logger.debug(">>> Setting up Column View table ...")
    self._setup_column_view()
    logger.debug(">>> Getting Perforce data...")
    self._perforce_sg_data = self._get_perforce_sg_data()
    length = len(self._perforce_sg_data)
    if not self._perforce_sg_data:
        self._perforce_sg_data = self._sg_data
    if self._perforce_sg_data and length > 0:
        msg = "\n <span style='color:#2C93E2'>Populating the Column View with {} files. Please wait...</span> \n".format(
            length)
        self._add_log(msg, 2)
        logger.debug(">>> Getting Perforce file size...")
        self._perforce_sg_data = self._get_perforce_size(self._perforce_sg_data)
        logger.debug(">>> Populating Column View table...")
        self._populate_column_view(self._perforce_sg_data)
        logger.debug(">>> Updating Column View is complete")
        for sg_item in self._perforce_sg_data:
            id = sg_item.get("id", 0)
            self.column_view_dict[id] = sg_item
        self._get_publish_icons()

        # for key, value in self.column_view_dict.items():
        #   logger.debug("key: {}, value: {}".format(key, value))


def _get_perforce_sg_data(self):
    perforce_sg_data = []

    model = self.ui.publish_view.model()
    if model.rowCount() > 0:
        for row in range(model.rowCount()):
            model_index = model.index(row, 0)
            proxy_model = model_index.model()
            source_index = proxy_model.mapToSource(model_index)
            item = source_index.model().itemFromIndex(source_index)

            is_folder = item.data(SgLatestPublishModel.IS_FOLDER_ROLE)
            if not is_folder:
                # Run default action.
                sg_item = shotgun_model.get_sg_data(model_index)
                if sg_item:
                    perforce_sg_data.append(sg_item)
    return perforce_sg_data


def _reset_perforce_widget(self):
    self.ui.column_view = QtWidgets.QTableView()


def _setup_column_view(self):
    # Define the headers for the table
    headers = ["Folder", "Name", "Action", "Revision", "Size(MB)", "Extension", "Type",
               "User", "Task", "Status", "ID",
               "Description"]
    # headers = ["Name", "Action", "Revision", "Size(MB)", " Extension", "Type", "Step",
    #           "Destination Path", "Description", "Entity Sub-Folder"]

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
    # Set different column widths
    # header = self.ui.column_view.horizontalHeader()
    # header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)  # Auto size column 0
    # header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
    # header.resizeSection(1, 300)  # Set width of column 1 to 300

    # self.ui.column_view.setGroupByColumn(7)


def _create_column_view_context_menu(self):
    self._column_add_action = QtGui.QAction("Add", self.ui.column_view)
    self._column_add_action.triggered.connect(lambda: self._on_column_model_action("add"))
    self._column_edit_action = QtGui.QAction("Edit", self.ui.column_view)
    self._column_edit_action.triggered.connect(lambda: self._on_column_model_action("edit"))
    self._column_delete_action = QtGui.QAction("Delete", self.ui.column_view)
    self._column_delete_action.triggered.connect(lambda: self._on_column_model_action("delete"))

    self._column_revert_action = QtGui.QAction("Revert", self.ui.column_view)
    self._column_revert_action.triggered.connect(lambda: self._on_column_model_action("revert"))

    # self._column_refresh_action = QtGui.QAction("Refresh", self.ui.column_view)
    # self._column_refresh_action.triggered.connect(self._publish_model.async_refresh)

    self.ui.column_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
    self.ui.column_view.customContextMenuRequested.connect(
        self._show_column_actions
    )


def _show_column_actions(self, pos):
    """
           Shows the actions for the current publish selection.

           :param pos: Local coordinates inside the viewport when the context menu was requested.
    """

    # Build a menu with all the actions.
    menu = QtGui.QMenu(self)
    actions = self._action_manager.get_actions_for_publishes(
        self.selected_publishes, self._action_manager.UI_AREA_MAIN
    )
    menu.addActions(actions)

    # Qt is our friend here. If there are no actions available, the separator won't be added, yay!
    menu.addSeparator()
    menu.addAction(self._column_add_action)
    menu.addAction(self._column_edit_action)
    menu.addAction(self._column_delete_action)
    menu.addSeparator()
    menu.addAction(self._column_revert_action)
    menu.addSeparator()
    # menu.addAction(self._column_refresh_action)

    # Wait for the user to pick something.
    menu.exec_(self.ui.column_view.mapToGlobal(pos))


def _create_column_view_context_menu_old(self):
    self.context_menu = QtWidgets.QMenu(self)
    self._column_add_action = self.context_menu.addAction("Add")
    self._column_edit_action = self.context_menu.addAction("Edit")
    self._column_delete_action = self.context_menu.addAction("Delete")
    self.context_menu.addSeparator()
    self._column_revert_action = self.context_menu.addAction("Revert")
    self.context_menu.addSeparator()
    # self._column_refresh_action = self.context_menu.addAction("Refresh")

    # Connect the actions to their respective callbacks

    self._column_add_action.triggered.connect(lambda: self._on_column_model_action("add"))
    self._column_edit_action.triggered.connect(lambda: self._on_column_model_action("edit"))
    self._column_delete_action.triggered.connect(lambda: self._on_column_model_action("delete"))
    self._column_revert_action.triggered.connect(lambda: self._on_column_model_action("revert"))
    # self._column_refresh_action.triggered.connect(lambda: self._on_column_model_action("refresh"))

    # Connect the context menu to the table view
    self.ui.column_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
    self.ui.column_view.customContextMenuRequested.connect(self.show_context_menu)


def show_context_menu(self, pos):
    # Show the context menu at the cursor position
    selected_index = self.ui.column_view.indexAt(pos)
    if selected_index.isValid():
        source_index = self.perforce_proxy_model.mapToSource(selected_index)
        selected_row_data = self.get_row_data_from_source(source_index)
        if selected_row_data:
            self.context_menu.exec_(self.ui.column_view.mapToGlobal(pos))


def get_row_data_from_source(self, source_index):
    # Get data from the source model using the source index
    row_data = []
    if source_index.isValid():
        row_number = source_index.row()
        for col in range(self.column_view_model.columnCount()):
            item = source_index.model().item(row_number, col)
            if item:
                row_data.append(item.text())
    logger.debug("Row data: {}".format(row_data))
    return row_data


def on_column_view_row_clicked(self, index):
    source_index = self.perforce_proxy_model.mapToSource(index)
    row_number = source_index.row()
    item = self.column_view_model.item(row_number, 10)  # Assuming you want data from the first column
    if item:
        data = item.text()
        # Perform actions with the data from the clicked row
        logger.debug(f"Clicked Row {row_number}, Data: {data}")
        id = int(data)
        self._setup_column_details_panel(id)


def _get_perforce_size(self, sg_data):
    """
    Get Perforce file size.
    """
    try:
        self._size_dict = {}
        for key in self._item_path_dict:
            if key:
                # logger.debug(">>>>>>>>>>  key is: {}".format(key))
                key = self._convert_local_to_depot(key).rstrip('/')
                # Get the file size from Perforce for all revisions
                # fstat_list = self._p4.run("fstat", "-T", "fileSize, clientFile, headRev", "-Of", "-Ol", key + '/...')
                # Get the file size from Perforce
                fstat_list = self._p4.run("fstat", "-T", "fileSize, clientFile", "-Ol", key + '/...')
                # logger.debug(">>>>>>>>>>  fstat_list is: {}".format(fstat_list))
                for fstat in fstat_list:
                    # if isinstance(fstat, list) and len(fstat) == 1:
                    #    fstat = fstat[0]
                    # logger.debug(">>>>>>>>>>  fstat is: {}".format(fstat))
                    if fstat:
                        size = fstat.get("fileSize", "N/A")
                        if size != "N/A":
                            size = "{:.2f}".format(int(size) / 1024 / 1024)
                            size = float(size)
                            # logger.debug(">>>>>>>>>>  size is: {}".format(size))
                        client_file = fstat.get('clientFile', None)

                        if client_file:
                            newkey = self._create_key(client_file)
                            # head_rev = fstat.get('headRev', "0")
                            # newkey = "{}#{}".format(newkey, head_rev)
                            if newkey:
                                if newkey not in self._size_dict:
                                    self._size_dict[newkey] = {}
                                self._size_dict[newkey]['fileSize'] = size
                # logger.debug(">>>>>>>>>>  self._size_dict is: {}".format(self._size_dict))

                for i, sg_item in enumerate(sg_data):

                    if "path" in sg_item:
                        if "local_path" in sg_item["path"]:
                            local_path = sg_item["path"].get("local_path", None)
                            modified_local_path = self._create_key(local_path)

                            if modified_local_path and modified_local_path in self._size_dict:
                                if 'fileSize' in self._size_dict[modified_local_path]:
                                    sg_item["fileSize"] = self._size_dict[modified_local_path].get('fileSize', None)
                            # logger.debug(">>>>>>>>>>  sg_item is: {}".format(sg_item))
        # logger.debug(">>>>>>>>>>  sg_data is: {}".format(sg_data))
    except Exception as e:
        logger.debug("Error getting Perforce file size: {}".format(e))
        pass
    return sg_data


def _populate_column_view(self, sg_data):
    """ Populate the table with data"""
    row = 0
    for sg_item in sg_data:
        if not sg_item:
            continue
        try:
            # logger.debug(">>> Getting row {} data".format(row))
            # self._print_sg_item(sg_item)
            # Extract relevant data from the Shotgun response
            name = sg_item.get("name", "N/A")
            action = sg_item.get("action") or sg_item.get("headAction") or "N/A"
            revision = sg_item.get("revision", "N/A")
            if revision != "N/A":
                revision = "#{}".format(revision)

            local_path = "N/A"
            difference_str = "N/A"
            if "path" in sg_item:
                path = sg_item.get("path", None)
                if path:
                    local_path = path.get("local_path", "N/A")
                    if local_path and local_path != "N/A":
                        local_directory = os.path.dirname(local_path)
                        difference_str = self._path_difference(self._entity_path, local_directory)
                        if difference_str:
                            difference_str = "{}\\".format(difference_str)

            file_extension = "N/A"
            if local_path and local_path != "N/A":
                file_extension = local_path.split(".")[-1] or "N/A"

            type = "N/A"
            if file_extension and file_extension != "N/A":
                type = self.settings.get(file_extension, "N/A")

            size = sg_item.get("fileSize", 0)

            # published_file_type = sg_item.get("published_file_type", {}).get("name", "N/A")
            # Todo: get the step
            # step = sg_item.get("step", {}).get("name", "N/A")
            # step = sg_item.get("task.Task.step.Step.code", "N/A") if step == "N/A" else step

            description = sg_item.get("description", "N/A")

            task_name = "N/A"
            if "task" in sg_item:
                task = sg_item.get("task", None)
                if task:
                    task_name = task.get("name", "N/A")

            task_status = sg_item.get("task.Task.sg_status_list", "N/A")

            user_name = "N/A"
            if "created_by" in sg_item:
                user = sg_item.get("created_by", None)
                if user:
                    user_name = user.get("name", "N/A")

            publish_id = 0
            if "id" in sg_item:
                publish_id = sg_item.get("id", 0)

            # entity_sub_folder = sg_item.get("entity.Sub-Folder", "N/A")

            # Insert data into the table
            # logger.debug(">>> Inserting row {} data".format(row))
            item_data = [difference_str, name, action, revision, size, file_extension, type,
                         user_name, task_name, task_status, publish_id,
                         description]
            self._insert_perforce_row(row, item_data, sg_item)
            # logger.debug(">>> Done with  row {}".format(row))
        except Exception as e:
            logger.debug("Failed to populate row %s, error: %s" % (row, e))
            pass
        row += 1


def _insert_perforce_row(self, row, data, sg_item):
    for col, value in enumerate(data):
        item = QtGui.QStandardItem(str(value))
        tooltip = self._get_tooltip(data, sg_item)
        item.setToolTip(tooltip)
        if col == 3:
            item.setData(value, QtCore.Qt.DisplayRole)

        self.column_view_model.setItem(row, col, item)


def print_selected_row(self):
    # Get the selected indexes from the column view
    selected_indexes = self.ui.column_view.selectionModel().selectedRows()

    if selected_indexes:
        for index in selected_indexes:
            row_number = index.row()
            print(f"Selected Row {row_number + 1}:")
            # You can access the data in each column of the selected row like this:
            for col in range(self.column_view_model.columnCount()):
                item = self.column_view_model.item(row_number, col)
                print(f"Column {col + 1}: {item.text()}")
    else:
        print("No rows selected.")


def _on_column_model_action(self, action):
    selected_actions = []
    selected_indexes = self.ui.column_view.selectionModel().selectedRows()
    for selected_index in selected_indexes:

        source_index = self.perforce_proxy_model.mapToSource(selected_index)
        selected_row_data = self.get_row_data_from_source(source_index)
        id = 0
        if (len(selected_row_data) >= 11):
            id = selected_row_data[10]

        sg_item = self.column_view_dict.get(int(id), None)
        logger.debug("selected_row_data: {}".format(selected_row_data))

        if "path" in sg_item:
            if "local_path" in sg_item["path"]:
                target_file = sg_item["path"].get("local_path", None)
                depot_file = sg_item.get("depotFile", None)

                if action in ["add", "move/add", "edit", "delete"]:
                    sg_item_action = sg_item.get("action", None)
                    if sg_item_action and sg_item_action == "delete":
                        msg = "Cannot perform the action on the file {} as it has already been marked for deletion or is deleted.".format(
                            depot_file)

                        self._add_log(msg, 2)

                    if action == "delete":
                        msg = "Marking file {} for deletion ...".format(depot_file)
                    else:
                        msg = "{} file {}".format(action, depot_file)
                    self._add_log(msg, 2)
                    selected_actions.append((sg_item, action))

                elif action == "revert":
                    msg = "Revert file {} ...".format(target_file)
                    self._add_log(msg, 3)
                    # p4_result = self._p4.run("revert", "-v", target_file)
                    p4_result = self._p4.run("revert", target_file)
                    if p4_result:
                        self.refresh_publish_data()

    if selected_actions:
        self.peform_changelist_selection(selected_actions)