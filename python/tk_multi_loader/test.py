def _show_pending_view_actions(self, pos):
    """
    Shows the actions for the current pending view selection and adjusts the selection mode.

    :param pos: Local coordinates inside the viewport when the context menu was requested.
    """

    # Get the index of the item at the menu position
    index = self._pending_view_widget.indexAt(pos)
    if not index.isValid():
        return

    # Determine if the index is a parent or a child
    is_parent = not index.parent().isValid()

    # Set selection mode based on whether the item is a parent or a child
    if is_parent:
        self._pending_view_widget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
    else:
        self._pending_view_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

    # Build a menu with all the actions.
    menu = QtGui.QMenu(self)

    # Add "Publish..." for parent rows, "Revert" for child rows
    if is_parent:
        menu.addAction(self._pending_view_publish_action)
    else:
        menu.addAction(self._pending_view_revert_action)

    menu.addSeparator()

    # Calculate the global position of the menu
    global_pos = self._pending_view_widget.mapToGlobal(pos)

    # Execute the menu using a QEventLoop to block until an action is triggered
    event_loop = QtCore.QEventLoop()
    menu.aboutToHide.connect(event_loop.quit)
    menu.exec_(global_pos)
    event_loop.exec_()
