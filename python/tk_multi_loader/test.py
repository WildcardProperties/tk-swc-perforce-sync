class SWCTreeView(QtWidgets.QTreeView):
    # ... other existing methods ...

    def dropEvent(self, event):
        if event.mimeData().hasUrls():  # Handle external file drops
            logger.debug("External file drop ...")
            urls = event.mimeData().urls()

            # Determine the target changelist
            target_index = self.indexAt(event.pos())
            target_changelist = target_index.data(QtCore.Qt.UserRole)
            if target_changelist is None:
                target_changelist = "default"  # Use "default" if no specific changelist is targeted
            logger.debug("Target changelist: {}".format(target_changelist))

            # Process each dropped file
            for url in urls:
                if url.isLocalFile():
                    local_path = url.toLocalFile().replace("\\", "/")
                    logger.debug("External dropped file: {}".format(local_path))

                    # Add file to the changelist
                    try:
                        add_to_change(self.p4, target_changelist, local_path)
                        logger.debug("Added {} to changelist {}".format(local_path, target_changelist))
                    except Exception as e:
                        logger.error("Error adding file to changelist: {}".format(e))

            event.acceptProposedAction()
        else:
            # Drop event handling for internal items
            if event.source() == self:
                # Retrieve the new parent's data (changelist number)
                target_index = self.indexAt(event.pos())
                target_data = target_index.data(QtCore.Qt.DisplayRole)
                logger.debug("New parent data (changelist number): {}".format(target_data))
                target_changelist = target_index.data(QtCore.Qt.UserRole)
                target_changelist = str(target_changelist)
                logger.debug("parent change is: {}".format(target_changelist))

                # Retrieve the source item's data (depot file path)
                for source_index in self.selectedIndexes():
                    source_data = source_index.data(QtCore.Qt.DisplayRole)
                    source_changelist = source_index.data(QtCore.Qt.UserRole)
                    source_changelist = str(source_changelist)

                    if source_data:
                        dragged_file = source_data.split("#")[0]
                        dragged_file = dragged_file.strip()
                        logger.debug("Source data (depot file): {}".format(dragged_file))

                        # Add the depot file to the new changelist
                        logger.debug(
                            "Adding dragged file: {} to changelist: {}".format(dragged_file, target_changelist))
                        reopen_res = self.p4.run_reopen("-c", target_changelist, dragged_file)
                        logger.debug("Result of reopen: {}".format(reopen_res))

                super().dropEvent(event)
            else:
                # Call the base dropEvent implementation
                super().dropEvent(event)

    # ... other existing methods ...
