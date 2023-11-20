def dropEvent(self, event):
    if event.mimeData().hasUrls():  # Handle external file drops
        logger.debug("External file drop ...")
        urls = event.mimeData().urls()
        logger.debug("urls: {}".format(urls))
        if not urls:
            logger.debug("No URLs found in mimeData.")
            return

        for url in urls:
            logger.debug("url: {}".format(url))
            if url.isLocalFile():
                logger.debug("url: {} is a local file".format(url))
                local_path = url.toLocalFile()
                local_path = str(local_path)
                local_path = local_path.replace("\\", "/")
                logger.debug("External dropped file: {}".format(local_path))
            else:
                logger.debug("Non-local file URL: {}".format(url))
        event.acceptProposedAction()
    else:
        # Existing logic for handling internal item drops
        # ...

def dragEnterEvent(self, event):
    if event.source() == self:
        event.setDropAction(QtCore.Qt.MoveAction)
        event.accept()
    elif event.mimeData().hasUrls():  # Check for external file drops
        logger.debug("Drag event with URLs detected.")
        event.acceptProposedAction()
    else:
        super().dragEnterEvent(event)
