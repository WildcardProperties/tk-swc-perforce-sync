def _on_pending_view_model_action(self, action):
    # ... [unchanged parts of the function above] ...

    if action == "publish" and selected_indexes:
        for selected_index in selected_indexes:
            try:
                source_index = self._pending_view_model.mapToSource(selected_index)
                change, description = self._get_pending_info_from_source(source_index)
            except Exception as e:
                logger.debug("Error processing selection: {}".format(e))
        if change:
            files_in_changelist = self._list_files_in_changelist(change)
            logger.debug("Files in changelist {}: {}".format(change, files_in_changelist))

            # Validate changelist files using threading
            result, error_list = self._validate_changelist_files_with_threads(files_in_changelist)
            if not result:
                msg = "\n <span style='color:#CC3333'>The following files in the changelist {} are not linked to any Shotgrid entity:</span> \n".format(change)
                self._add_log(msg, 2)
                for filepath in error_list:
                    msg = "\n <span style='color:#CC3333'>{}</span> \n".format(filepath)
                    self._add_log(msg, 2)
                # Exit without publishing
                return

        try:
            # Create the description file
            self._create_description_file(files_in_changelist, description)
        except:
            pass

        # Rest of the publish logic remains unchanged
        # ... [unchanged parts of the function above] ...