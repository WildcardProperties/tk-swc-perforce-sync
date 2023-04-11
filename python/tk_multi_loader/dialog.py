# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.


import sgtk
from sgtk import TankError
from sgtk.platform.qt import QtCore, QtGui
#from tank.platform.qt5 import QtWidgets


from .model_hierarchy import SgHierarchyModel
from .model_entity import SgEntityModel
from .model_latestpublish import SgLatestPublishModel
from .model_publishtype import SgPublishTypeModel
from .model_status import SgStatusModel
from .proxymodel_latestpublish import SgLatestPublishProxyModel
from .proxymodel_entity import SgEntityProxyModel
from .delegate_publish_thumb import SgPublishThumbDelegate
from .delegate_publish_list import SgPublishListDelegate
from .model_publishhistory import SgPublishHistoryModel
from .delegate_publish_history import SgPublishHistoryDelegate
from .search_widget import SearchWidget
from .banner import Banner
from .loader_action_manager import LoaderActionManager
from .utils import resolve_filters
#from .handle_perforce_data import PerforceData

from . import constants
from . import model_item_data

from .ui.dialog import Ui_Dialog
from .publish_item import PublishItem
#from .publisher.api.manager import PublishManager
#from .publish_app import P4SGPUBLISHER
from .publish_app import MultiPublish2
from collections import defaultdict
import os
from os.path import expanduser
import time


logger = sgtk.platform.get_logger(__name__)

# import frameworks
shotgun_model = sgtk.platform.import_framework(
    "tk-swc-framework-shotgunutils", "shotgun_model"
)
settings = sgtk.platform.import_framework("tk-swc-framework-shotgunutils", "settings")
help_screen = sgtk.platform.import_framework("tk-framework-qtwidgets", "help_screen")
overlay_widget = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "overlay_widget"
)
shotgun_search_widget = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "shotgun_search_widget"
)
task_manager = sgtk.platform.import_framework(
    "tk-swc-framework-shotgunutils", "task_manager"
)
shotgun_globals = sgtk.platform.import_framework(
    "tk-swc-framework-shotgunutils", "shotgun_globals"
)

ShotgunModelOverlayWidget = overlay_widget.ShotgunModelOverlayWidget


class AppDialog(QtGui.QWidget):
    """
    Main dialog window for the App
    """

    # enum to control the mode of the main view
    (MAIN_VIEW_LIST, MAIN_VIEW_THUMB) = range(2)

    # signal emitted whenever the selected publish changes
    # in either the main view or the details history view
    selection_changed = QtCore.Signal()

    def __init__(self, action_manager, parent=None):
        """
        Constructor

        :param action_manager:  The action manager to use - if not specified
                                then the default will be used instead
        :param parent:          The parent QWidget for this control
        """
        QtGui.QWidget.__init__(self, parent)
        # self.app = QtWidgets.QApplication.instance()


        self._action_manager = action_manager

        # The loader app can be invoked from other applications with a custom
        # action manager as a File Open-like dialog. For these managers, we won't
        # be using the banner system.

        # We will support the banners only for the default loader.
        if isinstance(action_manager, LoaderActionManager):
            self._action_banner = Banner(self)
            self._action_manager.pre_execute_action.connect(self._pre_execute_action)
            self._action_manager.post_execute_action.connect(
                lambda _: self._action_banner.hide_banner()
            )

        # create a settings manager where we can pull and push prefs later
        # prefs in this manager are shared
        self._settings_manager = settings.UserSettings(sgtk.platform.current_bundle())

        # create a background task manager
        self._task_manager = task_manager.BackgroundTaskManager(
            self, start_processing=True, max_threads=2
        )

        shotgun_globals.register_bg_task_manager(self._task_manager)

        # set up the UI
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self._app = sgtk.platform.current_bundle()
        #################################################
        # Perforce
        self._fw = sgtk.platform.get_framework("tk-framework-perforce")
        self._p4 = self._fw.connection.connect()
        #################################################
        # maintain a list where we keep a reference to
        # all the dynamic UI we create. This is to make
        # the GC happy.
        self._dynamic_widgets = []

        # maintain a special flag so that we can switch profile
        # tabs without triggering events
        self._disable_tab_event_handler = False

        #################################################
        # hook a helper model tracking status codes so we
        # can use those in the UI
        self._status_model = SgStatusModel(self, self._task_manager)

        #################################################
        # details pane
        self._details_pane_visible = False

        self._details_action_menu = QtGui.QMenu()
        self.ui.detail_actions_btn.setMenu(self._details_action_menu)

        self.ui.info.clicked.connect(self._toggle_details_pane)

        self.ui.thumbnail_mode.clicked.connect(self._on_thumbnail_mode_clicked)
        self.ui.list_mode.clicked.connect(self._on_list_mode_clicked)

        self._publish_history_model = SgPublishHistoryModel(self, self._task_manager)

        self._publish_history_model_overlay = ShotgunModelOverlayWidget(
            self._publish_history_model, self.ui.history_view
        )

        self._publish_history_proxy = QtGui.QSortFilterProxyModel(self)
        self._publish_history_proxy.setSourceModel(self._publish_history_model)

        # now use the proxy model to sort the data to ensure
        # higher version numbers appear earlier in the list
        # the history model is set up so that the default display
        # role contains the version number field in shotgun.
        # This field is what the proxy model sorts by default
        # We set the dynamic filter to true, meaning QT will keep
        # continously sorting. And then tell it to use column 0
        # (we only have one column in our models) and descending order.
        self._publish_history_proxy.setDynamicSortFilter(True)
        self._publish_history_proxy.sort(0, QtCore.Qt.DescendingOrder)

        self.ui.history_view.setModel(self._publish_history_proxy)
        self._history_delegate = SgPublishHistoryDelegate(
            self.ui.history_view, self._status_model, self._action_manager
        )
        self.ui.history_view.setItemDelegate(self._history_delegate)

        # event handler for when the selection in the history view is changing
        # note! Because of some GC issues (maya 2012 Pyside), need to first establish
        # a direct reference to the selection model before we can set up any signal/slots
        # against it
        self._history_view_selection_model = self.ui.history_view.selectionModel()
        self._history_view_selection_model.selectionChanged.connect(
            self._on_history_selection
        )

        self._multiple_publishes_pixmap = QtGui.QPixmap(
            ":/res/multiple_publishes_512x400.png"
        )
        self._no_selection_pixmap = QtGui.QPixmap(":/res/no_item_selected_512x400.png")
        self._no_pubs_found_icon = QtGui.QPixmap(":/res/no_publishes_found.png")

        self.ui.detail_playback_btn.clicked.connect(self._on_detail_version_playback)
        self._current_version_detail_playback_url = None

        # set up right click menu for the main publish view
        self._refresh_history_action = QtGui.QAction("Refresh", self.ui.history_view)
        self._refresh_history_action.triggered.connect(
            self._publish_history_model.async_refresh
        )
        self.ui.history_view.addAction(self._refresh_history_action)
        self.ui.history_view.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        # if an item in the list is double clicked the default action is run
        self.ui.history_view.doubleClicked.connect(self._on_history_double_clicked)

        #################################################
        # load and initialize cached publish type model
        self._publish_type_model = SgPublishTypeModel(
            self, self._action_manager, self._settings_manager, self._task_manager
        )
        self.ui.publish_type_list.setModel(self._publish_type_model)

        self._publish_type_overlay = ShotgunModelOverlayWidget(
            self._publish_type_model, self.ui.publish_type_list
        )

        #################################################
        # setup publish model
        self._publish_model = SgLatestPublishModel(
            self, self._publish_type_model, self._task_manager
        )

        self._publish_main_overlay = ShotgunModelOverlayWidget(
            self._publish_model, self.ui.publish_view
        )

        # set up a proxy model to cull results based on type selection
        self._publish_proxy_model = SgLatestPublishProxyModel(self)
        self._publish_proxy_model.setSourceModel(self._publish_model)

        # whenever the number of columns change in the proxy model
        # check if we should display the "sorry, no publishes found" overlay
        self._publish_model.cache_loaded.connect(self._on_publish_content_change)
        self._publish_model.data_refreshed.connect(self._on_publish_content_change)
        self._publish_proxy_model.filter_changed.connect(
            self._on_publish_content_change
        )

        # hook up view -> proxy model -> model
        self.ui.publish_view.setModel(self._publish_proxy_model)

        # set up custom delegates to use when drawing the main area
        self._publish_thumb_delegate = SgPublishThumbDelegate(
            self.ui.publish_view, self._action_manager
        )

        self._publish_list_delegate = SgPublishListDelegate(
            self.ui.publish_view, self._action_manager
        )

        # recall which the most recently mode used was and set that
        main_view_mode = self._settings_manager.retrieve(
            "main_view_mode", self.MAIN_VIEW_THUMB
        )
        self._set_main_view_mode(main_view_mode)

        # whenever the type list is checked, update the publish filters
        self._publish_type_model.itemChanged.connect(
            self._apply_type_filters_on_publishes
        )

        # if an item in the table is double clicked the default action is run
        self.ui.publish_view.doubleClicked.connect(self._on_publish_double_clicked)

        # event handler for when the selection in the publish view is changing
        # note! Because of some GC issues (maya 2012 Pyside), need to first establish
        # a direct reference to the selection model before we can set up any signal/slots
        # against it
        self.ui.publish_view.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self._publish_view_selection_model = self.ui.publish_view.selectionModel()
        self._publish_view_selection_model.selectionChanged.connect(
            self._on_publish_selection
        )

        # set up right click menu for the main publish view

        self._add_action = QtGui.QAction("Add", self.ui.publish_view)
        self._add_action.triggered.connect(lambda: self._on_publish_model_action("add"))
        self._edit_action = QtGui.QAction("Edit", self.ui.publish_view)
        self._edit_action.triggered.connect(lambda: self._on_publish_model_action("edit"))
        self._delete_action = QtGui.QAction("Delete", self.ui.publish_view)
        self._delete_action.triggered.connect(lambda: self._on_publish_model_action("delete"))

        self._refresh_action = QtGui.QAction("Refresh", self.ui.publish_view)
        self._refresh_action.triggered.connect(self._publish_model.async_refresh)

        self.ui.publish_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.publish_view.customContextMenuRequested.connect(
            self._show_publish_actions
        )

        #################################################
        # popdown publish filter widget for the main view
        # note:
        # we parent the widget to a frame that flows around the
        # main publish area - this is in order to avoid a scenario
        # where the overlay that sometimes pops up on top of the
        # publish area and the search widget would be competing
        # for the same z-index. The result in some of these cases
        # is that the search widget is hidden under the "publishes
        # not found" overlay. By having it parented to the frame
        # instead, it will always be above the overlay.
        self._search_widget = SearchWidget(self.ui.publish_frame)
        # hook it up with the search button the main toolbar
        self.ui.search_publishes.clicked.connect(self._on_publish_filter_clicked)
        # hook it up so that it signals the publish proxy model whenever the filter changes
        self._search_widget.filter_changed.connect(
            self._publish_proxy_model.set_search_query
        )

        #################################################
        # checkboxes, buttons etc
        self.ui.fix_files.clicked.connect(self._on_fix_files)
        self.ui.sync_files.clicked.connect(self._on_sync_files)
        self.ui.publish_files.clicked.connect(self._on_publish_files)
        # self.ui.show_sub_items.toggled.connect(self._on_show_subitems_toggled)

        self.ui.check_all.clicked.connect(self._publish_type_model.select_all)
        self.ui.check_none.clicked.connect(self._publish_type_model.select_none)

        #################################################
        # thumb scaling
        scale_val = self._settings_manager.retrieve("thumb_size_scale", 140)
        # position both slider and view
        self.ui.thumb_scale.setValue(scale_val)
        self.ui.publish_view.setIconSize(QtCore.QSize(scale_val, scale_val))
        # and track subsequent changes
        self.ui.thumb_scale.valueChanged.connect(self._on_thumb_size_slider_change)

        #################################################
        # setup history

        self._history = []
        self._history_index = 0
        # state flag used by history tracker to indicate that the
        # current navigation operation is happen as a part of a
        # back/forward operation and not part of a user's click
        self._history_navigation_mode = False
        self.ui.navigation_home.clicked.connect(self._on_home_clicked)
        self.ui.navigation_prev.clicked.connect(self._on_back_clicked)
        self.ui.navigation_next.clicked.connect(self._on_forward_clicked)

        #################################################
        # set up cog button actions
        self._help_action = QtGui.QAction("Show Help Screen", self)
        self._help_action.triggered.connect(self.show_help_popup)
        self.ui.cog_button.addAction(self._help_action)

        self._doc_action = QtGui.QAction("View Documentation", self)
        self._doc_action.triggered.connect(self._on_doc_action)
        self.ui.cog_button.addAction(self._doc_action)

        self._reload_action = QtGui.QAction("Reload", self)
        self._reload_action.triggered.connect(self._on_reload_action)
        self.ui.cog_button.addAction(self._reload_action)

        #################################################
        # set up preset tabs and load and init tree views
        self._entity_presets = {}
        self._current_entity_preset = None

        self._load_entity_presets()

        # load visibility state for details pane
        show_details = self._settings_manager.retrieve("show_details", False)
        self._set_details_pane_visiblity(show_details)

        # trigger an initial evaluation of filter proxy model
        self._apply_type_filters_on_publishes()
        #################################################
        # Sync
        self._files_to_sync = []
        #################################################
        # Publishing
        self._home_dir = None
        self._sg_data = []
        self._create_publisher_dir()
        self._depot_files_to_publish = []
        self._fstat_dict = {}
        self._action_data_to_publish = []
        #################################################
        # Perforce data

        self.status_dict = {
            "add": "p4add",
            "delete": "p4del",
            "edit": "p4edit"
        }
        self.settings = {
            "wire": "Alias File",
            "abc": "Alembic Cache",
            "max": "3dsmax Scene",
            "hrox": "NukeStudio Project",
            "hip": "Houdini Scene",
            "hipnc": "Houdini Scene",
            "ma": "Maya Scene",
            "mb": "Maya Scene",
            "fbx": "Motion Builder FBX",
            "nk": "Nuke Script",
            "psd": "Photoshop Image",
            "psb": "Photoshop Image",
            "vpb": "VRED Scene",
            "vpe": "VRED Scene",
            "osb": "VRED Scene",
            "dpx": "Rendered Image",
            "exr": "Rendered Image",
            "tiff": "Texture",
            "tx": "Texture",
            "tga": "Texture",
            "dds": "Texture",
            "jpeg": "Image",
            "jpg": "Image",
            "mov": "Movie",
            "mp4": "Movie",
            "pdf": "PDF"
        }

    def _show_publish_actions(self, pos):
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
        menu.addAction(self._add_action)
        menu.addAction(self._edit_action)
        menu.addAction(self._delete_action)
        menu.addSeparator()
        menu.addAction(self._refresh_action)

        # Wait for the user to pick something.
        menu.exec_(self.ui.publish_view.mapToGlobal(pos))

    @property
    def selected_publishes(self):
        """
        Get the selected sg_publish details
        """
        # check to see if something is selected in the details history view:
        selection_model = self.ui.history_view.selectionModel()
        if selection_model.hasSelection():
            # only handle single selection atm
            proxy_index = selection_model.selection().indexes()[0]

            # the incoming model index is an index into our proxy model
            # before continuing, translate it to an index into the
            # underlying model
            source_index = proxy_index.model().mapToSource(proxy_index)

            # now we have arrived at our model derived from StandardItemModel
            # so let's retrieve the standarditem object associated with the index
            item = source_index.model().itemFromIndex(source_index)

            sg_data = item.get_sg_data()
            if sg_data:
                return [sg_data]

        sg_data_list = []

        # nothing selected in the details view so check to see if something is selected
        # in the main publish view:
        selection_model = self.ui.publish_view.selectionModel()
        if selection_model.hasSelection():

            for proxy_index in selection_model.selection().indexes():

                # the incoming model index is an index into our proxy model
                # before continuing, translate it to an index into the
                # underlying model
                source_index = proxy_index.model().mapToSource(proxy_index)

                # now we have arrived at our model derived from StandardItemModel
                # so let's retrieve the standarditem object associated with the index
                item = source_index.model().itemFromIndex(source_index)

                sg_data = item.get_sg_data()

                sg_data = item.get_sg_data()
                if sg_data and not item.data(SgLatestPublishModel.IS_FOLDER_ROLE):
                    sg_data_list.append(sg_data)

        return sg_data_list

    def closeEvent(self, event):
        """
        Executed when the main dialog is closed.
        All worker threads and other things which need a proper shutdown
        need to be called here.
        """
        # display exit splash screen
        splash_pix = QtGui.QPixmap(":/res/exit_splash.png")
        splash = QtGui.QSplashScreen(splash_pix, QtCore.Qt.WindowStaysOnTopHint)
        splash.setMask(splash_pix.mask())
        splash.show()
        QtCore.QCoreApplication.processEvents()

        try:
            # clear the selection in the main views.
            # this is to avoid re-triggering selection
            # as items are being removed in the models
            #
            # note that we pull out a fresh handle to the selection model
            # as these objects sometimes are deleted internally in the view
            # and therefore persisting python handles may not be valid
            self.ui.history_view.selectionModel().clear()
            self.ui.publish_view.selectionModel().clear()

            # disconnect some signals so we don't go all crazy when
            # the cascading model deletes begin as part of the destroy calls
            for p in self._entity_presets:
                self._entity_presets[
                    p
                ].view.selectionModel().selectionChanged.disconnect(
                    self._reload_treeview
                )

            # gracefully close all connections
            shotgun_globals.unregister_bg_task_manager(self._task_manager)
            self._task_manager.shut_down()

        except:
            app = sgtk.platform.current_bundle()
            app.log_exception("Error running Loader App closeEvent()")

        # close splash
        splash.close()

        # okay to close dialog
        event.accept()

    def is_first_launch(self):
        """
        Returns true if this is the first time UI is being launched
        """
        ui_launched = self._settings_manager.retrieve(
            "ui_launched", False, self._settings_manager.SCOPE_ENGINE
        )
        if ui_launched == False:
            # store in settings that we now have launched
            self._settings_manager.store(
                "ui_launched", True, self._settings_manager.SCOPE_ENGINE
            )

        return not (ui_launched)

    ########################################################################################
    # info bar related

    def _on_history_selection(self, selected, deselected):
        """
        Called when the selection changes in the history view in the details panel

        :param selected:    Items that have been selected
        :param deselected:  Items that have been deselected
        """
        # emit the selection_changed signal
        self.selection_changed.emit()

    def _on_history_double_clicked(self, model_index):
        """
        When someone double clicks on a publish in the history view, run the
        default action

        :param model_index:    The model index of the item that was double clicked
        """
        # the incoming model index is an index into our proxy model
        # before continuing, translate it to an index into the
        # underlying model
        proxy_model = model_index.model()
        source_index = proxy_model.mapToSource(model_index)

        # now we have arrived at our model derived from StandardItemModel
        # so let's retrieve the standarditem object associated with the index
        item = source_index.model().itemFromIndex(source_index)

        # Run default action.
        sg_item = shotgun_model.get_sg_data(model_index)
        default_action = self._action_manager.get_default_action_for_publish(
            sg_item, self._action_manager.UI_AREA_HISTORY
        )
        if default_action:
            default_action.trigger()

    def _on_publish_filter_clicked(self):
        """
        Executed when someone clicks the filter button in the main UI
        """
        if self.ui.search_publishes.isChecked():
            self.ui.search_publishes.setIcon(
                QtGui.QIcon(QtGui.QPixmap(":/res/search_active.png"))
            )
            self._search_widget.enable()
        else:
            self.ui.search_publishes.setIcon(
                QtGui.QIcon(QtGui.QPixmap(":/res/search.png"))
            )
            self._search_widget.disable()

    def _on_thumbnail_mode_clicked(self):
        """
        Executed when someone clicks the thumbnail mode button
        """
        self._set_main_view_mode(self.MAIN_VIEW_THUMB)

    def _on_list_mode_clicked(self):
        """
        Executed when someone clicks the list mode button
        """
        self._set_main_view_mode(self.MAIN_VIEW_LIST)

    def _set_main_view_mode(self, mode):
        """
        Sets up the view mode for the main view.

        :param mode: either MAIN_VIEW_LIST or MAIN_VIEW_THUMB
        """
        if mode == self.MAIN_VIEW_LIST:
            self.ui.list_mode.setIcon(
                QtGui.QIcon(QtGui.QPixmap(":/res/mode_switch_card_active.png"))
            )
            self.ui.list_mode.setChecked(True)
            self.ui.thumbnail_mode.setIcon(
                QtGui.QIcon(QtGui.QPixmap(":/res/mode_switch_thumb.png"))
            )
            self.ui.thumbnail_mode.setChecked(False)
            self.ui.publish_view.setViewMode(QtGui.QListView.ListMode)
            self.ui.publish_view.setItemDelegate(self._publish_list_delegate)
            self._show_thumb_scale(False)
        elif mode == self.MAIN_VIEW_THUMB:
            self.ui.list_mode.setIcon(
                QtGui.QIcon(QtGui.QPixmap(":/res/mode_switch_card.png"))
            )
            self.ui.list_mode.setChecked(False)
            self.ui.thumbnail_mode.setIcon(
                QtGui.QIcon(QtGui.QPixmap(":/res/mode_switch_thumb_active.png"))
            )
            self.ui.thumbnail_mode.setChecked(True)
            self.ui.publish_view.setViewMode(QtGui.QListView.IconMode)
            self.ui.publish_view.setItemDelegate(self._publish_thumb_delegate)
            self._show_thumb_scale(True)
        else:
            raise TankError("Undefined view mode!")

        self.ui.publish_view.selectionModel().clear()
        self._settings_manager.store("main_view_mode", mode)

    def _show_thumb_scale(self, is_visible):
        """
        Shows or hides the scale widgets.

        :param bool is_visible: If True, scale slider will be shown.
        """
        self.ui.thumb_scale.setVisible(is_visible)
        self.ui.scale_label.setVisible(is_visible)

    def _toggle_details_pane(self):
        """
        Executed when someone clicks the show/hide details button
        """
        if self.ui.details.isVisible():
            self._set_details_pane_visiblity(False)
        else:
            self._set_details_pane_visiblity(True)

    def _set_details_pane_visiblity(self, visible):
        """
        Specifies if the details pane should be visible or not
        """
        # store our value in a setting
        self._settings_manager.store("show_details", visible)

        if visible == False:
            # hide details pane
            self._details_pane_visible = False
            self.ui.details.setVisible(False)
            self.ui.info.setText("Show Details")

        else:
            # show details pane
            self._details_pane_visible = True
            self.ui.details.setVisible(True)
            self.ui.info.setText("Hide Details")

            # if there is something selected, make sure the detail
            # section is focused on this
            selection_model = self.ui.publish_view.selectionModel()

            self._setup_details_panel(selection_model.selectedIndexes())

    def _setup_details_panel(self, items):
        """
        Sets up the details panel with info for a given item.
        """

        def __make_table_row(left, right):
            """
            Helper method to make a detail table row
            """
            return (
                "<tr><td><b style='color:#2C93E2'>%s</b>&nbsp;</td><td>%s</td></tr>"
                % (left, right)
            )

        def __set_publish_ui_visibility(is_publish):
            """
            Helper method to enable disable publish specific details UI
            """
            # disable version history stuff
            self.ui.version_history_label.setEnabled(is_publish)
            self.ui.history_view.setEnabled(is_publish)

            # hide actions and playback stuff
            self.ui.detail_actions_btn.setVisible(is_publish)
            self.ui.detail_playback_btn.setVisible(is_publish)

        def __clear_publish_history(pixmap):
            """
            Helper method that clears the history view on the right hand side.

            :param pixmap: image to set at the top of the history view.
            """
            self._publish_history_model.clear()
            self.ui.details_header.setText("")
            self.ui.details_image.setPixmap(pixmap)
            __set_publish_ui_visibility(False)

        # note - before the UI has been shown, querying isVisible on the actual
        # widget doesn't work here so use member variable to track state instead
        if not self._details_pane_visible:
            return

        if len(items) == 0:
            __clear_publish_history(self._no_selection_pixmap)
        elif len(items) > 1:
            __clear_publish_history(self._multiple_publishes_pixmap)
        else:

            model_index = items[0]
            # the incoming model index is an index into our proxy model
            # before continuing, translate it to an index into the
            # underlying model
            proxy_model = model_index.model()
            source_index = proxy_model.mapToSource(model_index)

            # now we have arrived at our model derived from StandardItemModel
            # so let's retrieve the standarditem object associated with the index
            item = source_index.model().itemFromIndex(source_index)

            sg_data = item.get_sg_data()
            """
            if sg_data:
                # published_file_type = sg_data.get('published_file_type', None)
                published_file_type = sg_data.get('type', None)
                logger.debug(">>>>> Type is {}".format(sg_data.get('type', None)))
                if published_file_type not in ['PublishedFile']:
                # if not published_file_type:
                    __clear_publish_history(self._no_selection_pixmap)
                    return
            """
            # render out details
            thumb_pixmap = item.icon().pixmap(512)
            self.ui.details_image.setPixmap(thumb_pixmap)

            if sg_data is None:
                # an item which doesn't have any sg data directly associated
                # typically an item higher up the tree
                # just use the default text
                folder_name = __make_table_row("Name", item.text())
                self.ui.details_header.setText("<table>%s</table>" % folder_name)
                __set_publish_ui_visibility(False)

            elif item.data(SgLatestPublishModel.IS_FOLDER_ROLE):
                # folder with sg data - basically a leaf node in the entity tree

                status_code = sg_data.get("sg_status_list")
                if status_code is None:
                    status_name = "No Status"
                else:
                    status_name = self._status_model.get_long_name(status_code)

                status_color = self._status_model.get_color_str(status_code)
                if status_color:
                    status_name = (
                        "%s&nbsp;<span style='color: rgb(%s)'>&#9608;</span>"
                        % (status_name, status_color)
                    )

                if sg_data.get("description"):
                    desc_str = sg_data.get("description")
                else:
                    desc_str = "No description entered."

                msg = ""
                display_name = shotgun_globals.get_type_display_name(sg_data["type"])
                msg += __make_table_row(
                    "Name", "%s %s" % (display_name, sg_data.get("code"))
                )
                msg += __make_table_row("Status", status_name)
                msg += __make_table_row("Description", desc_str)
                self.ui.details_header.setText("<table>%s</table>" % msg)

                # blank out the version history
                __set_publish_ui_visibility(False)
                self._publish_history_model.clear()

            else:
                # this is a publish!
                __set_publish_ui_visibility(True)

                sg_item = item.get_sg_data()

                # sort out the actions button
                actions = self._action_manager.get_actions_for_publish(
                    sg_item, self._action_manager.UI_AREA_DETAILS
                )
                if len(actions) == 0:
                    self.ui.detail_actions_btn.setVisible(False)
                else:
                    self.ui.detail_playback_btn.setVisible(True)
                    self._details_action_menu.clear()
                    for a in actions:
                        self._dynamic_widgets.append(a)
                        self._details_action_menu.addAction(a)

                # if there is an associated version, show the play button
                if sg_item.get("version"):
                    sg_url = sgtk.platform.current_bundle().shotgun.base_url
                    url = "%s/page/media_center?type=Version&id=%d" % (
                        sg_url,
                        sg_item["version"]["id"],
                    )

                    self.ui.detail_playback_btn.setVisible(True)
                    self._current_version_detail_playback_url = url
                else:
                    self.ui.detail_playback_btn.setVisible(False)
                    self._current_version_detail_playback_url = None

                if sg_item.get("name") is None:
                    name_str = "No Name"
                else:
                    name_str = sg_item.get("name")

                type_str = shotgun_model.get_sanitized_data(
                    item, SgLatestPublishModel.PUBLISH_TYPE_NAME_ROLE
                )

                msg = ""
                msg += __make_table_row("Name", name_str)
                msg += __make_table_row("Type", type_str)

                version = sg_item.get("version_number")
                vers_str = "%03d" % version if version is not None else "N/A"

                msg += __make_table_row("Version", "%s" % vers_str)

                if sg_item.get("entity"):
                    display_name = shotgun_globals.get_type_display_name(
                        sg_item.get("entity").get("type")
                    )
                    entity_str = "<b>%s</b> %s" % (
                        display_name,
                        sg_item.get("entity").get("name"),
                    )
                    msg += __make_table_row("Link", entity_str)

                # sort out the task label
                if sg_item.get("task"):

                    if sg_item.get("task.Task.content") is None:
                        task_name_str = "Unnamed"
                    else:
                        task_name_str = sg_item.get("task.Task.content")

                    if sg_item.get("task.Task.sg_status_list") is None:
                        task_status_str = "No Status"
                    else:
                        task_status_code = sg_item.get("task.Task.sg_status_list")
                        task_status_str = self._status_model.get_long_name(
                            task_status_code
                        )

                    msg += __make_table_row(
                        "Task", "%s (%s)" % (task_name_str, task_status_str)
                    )

                # if there is a version associated, get the status for this
                if sg_item.get("version.Version.sg_status_list"):
                    task_status_code = sg_item.get("version.Version.sg_status_list")
                    task_status_str = self._status_model.get_long_name(task_status_code)
                    msg += __make_table_row("Review", task_status_str)

                if sg_item.get("revision"):
                    revision = sg_item.get("revision")
                    msg += __make_table_row("Revision#", revision)



                if sg_item.get("action"):
                    action = sg_item.get("action")
                    msg += __make_table_row("Action", action)
                else:
                    if sg_item.get("headAction"):
                        head_action = sg_item.get("headAction", "N/A")
                        msg += __make_table_row("Action", head_action)


                self.ui.details_header.setText("<table>%s</table>" % msg)

                # tell details pane to load stuff
                sg_data = item.get_sg_data()
                self._publish_history_model.load_data(sg_data)

            self.ui.details_header.updateGeometry()

    def _on_detail_version_playback(self):
        """
        Callback when someone clicks the version playback button
        """
        # the code that sets up the version button also populates
        # a member variable which olds the current media center url.
        if self._current_version_detail_playback_url:
            QtGui.QDesktopServices.openUrl(
                QtCore.QUrl(self._current_version_detail_playback_url)
            )

    ########################################################################################
    # history related

    def _compute_history_button_visibility(self):
        """
        compute history button enabled/disabled state based on contents of history stack.
        """
        self.ui.navigation_next.setEnabled(True)
        self.ui.navigation_prev.setEnabled(True)
        if self._history_index == len(self._history):
            self.ui.navigation_next.setEnabled(False)
        if self._history_index == 1:
            self.ui.navigation_prev.setEnabled(False)

    def _add_history_record(self, preset_caption, std_item):
        """
        Adds a record to the history stack
        """
        # self._history_index is a one based index that points at the currently displayed
        # item. If it is not pointing at the last element, it means a user has stepped back
        # in that case, discard the history after the current item and add this new record
        # after the current item

        if (
            not self._history_navigation_mode
        ):  # do not add to history when browsing the history :)
            # chop off history at the point we are currently
            self._history = self._history[: self._history_index]
            # append our current item to the chopped history
            self._history.append({"preset": preset_caption, "item": std_item})
            self._history_index += 1

        # now compute buttons
        self._compute_history_button_visibility()

    def _history_navigate_to_item(self, preset, item):
        """
        Focus in on an item in the tree view.
        """
        # tell rest of event handlers etc that this navigation
        # is part of a history click. This will ensure that no
        # *new* entries are added to the history log when we
        # are clicking back/next...
        self._history_navigation_mode = True
        try:
            self._select_item_in_entity_tree(preset, item)
        finally:
            self._history_navigation_mode = False

    def _on_home_clicked(self):
        """
        User clicks the home button.
        """
        # first, try to find the "home" item by looking at the current app context.
        found_preset = None
        found_hierarchy_preset = None
        found_item = None

        # get entity portion of context
        ctx = sgtk.platform.current_bundle().context

        if ctx.entity:
            # now step through the profiles and find a matching entity
            for preset_index, preset in self._entity_presets.items():

                if isinstance(preset.model, SgHierarchyModel):
                    # Found a hierarchy model, we select it right away, since it contains the
                    # entire project, no need to scan for other tabs.
                    found_hierarchy_preset = preset_index
                    break
                else:
                    if preset.entity_type == ctx.entity["type"]:
                        # found an at least partially matching entity profile.
                        found_preset = preset_index

                        # now see if our context object also exists in the tree of this profile
                        model = preset.model
                        item = model.item_from_entity(
                            ctx.entity["type"], ctx.entity["id"]
                        )

                        if item is not None:
                            # find an absolute match! Break the search.
                            found_item = item
                            break

        if found_hierarchy_preset:
            # We're about to programmatically set the tab and then the item, so inform
            # the tab switcher that this is a combo operation and shouldn't be tracked
            # by the history.
            self._select_tab(found_hierarchy_preset, track_in_history=False)
            # Kick off an async load of an entity, which in the context of the loader
            # is always meant to switch select that item.
            preset.model.async_item_from_entity(ctx.entity)
            return
        else:
            if found_preset is None:
                # no suitable item found. Use the first tab
                found_preset = self.ui.entity_preset_tabs.tabText(0)

            # select it in the left hand side tree view
            self._select_item_in_entity_tree(found_preset, found_item)

    def _on_back_clicked(self):
        """
        User clicks the back button
        """
        self._history_index += -1
        # get the data for this guy (note: index are one based)
        d = self._history[self._history_index - 1]
        self._history_navigate_to_item(d["preset"], d["item"])
        self._compute_history_button_visibility()

    def _on_forward_clicked(self):
        """
        User clicks the forward button
        """
        self._history_index += 1
        # get the data for this guy (note: index are one based)
        d = self._history[self._history_index - 1]
        self._history_navigate_to_item(d["preset"], d["item"])
        self._compute_history_button_visibility()

    ########################################################################################
    # filter view

    def _apply_type_filters_on_publishes(self):
        """
        Executed when the type listing changes
        """
        # go through and figure out which checkboxes are clicked and then
        # update the publish proxy model so that only items of that type
        # is displayed
        sg_type_ids = self._publish_type_model.get_selected_types()
        show_folders = self._publish_type_model.get_show_folders()
        self._publish_proxy_model.set_filter_by_type_ids(sg_type_ids, show_folders)

    ########################################################################################
    # publish view

    def _on_publish_content_change(self):
        """
        Triggered when the number of columns in the model is changing
        """
        # if no publish items are visible, display not found overlay
        num_pub_items = self._publish_proxy_model.rowCount()

        if num_pub_items == 0:
            # show 'nothing found' image
            self._publish_main_overlay.show_message_pixmap(self._no_pubs_found_icon)
        else:
            self._publish_main_overlay.hide()



    def _on_show_subitems_toggled(self):
        """
        Triggered when the show sub items checkbox is clicked
        """

        # Check if we should pop up that help screen.
        # The hierarchy model cannot handle "Show items in subfolders" mode.
        if self.ui.show_sub_items.isChecked() and not isinstance(
            self._entity_presets[self._current_entity_preset].model, SgHierarchyModel
        ):
            subitems_shown = self._settings_manager.retrieve(
                "subitems_shown", False, self._settings_manager.SCOPE_ENGINE
            )
            if subitems_shown == False:
                # store in settings that we now clicked the subitems at least once
                self._settings_manager.store(
                    "subitems_shown", True, self._settings_manager.SCOPE_ENGINE
                )
                # and display help
                app = sgtk.platform.current_bundle()
                help_pix = [
                    QtGui.QPixmap(":/res/subitems_help_1.png"),
                    QtGui.QPixmap(":/res/subitems_help_2.png"),
                    QtGui.QPixmap(":/res/subitems_help_3.png"),
                    QtGui.QPixmap(":/res/help_4.png"),
                ]
                help_screen.show_help_screen(self.window(), app, help_pix)

        # tell publish UI to update itself
        item = self._get_selected_entity()
        self._load_publishes_for_entity_item(item)
        # self._get_perforce_summary()

    def _on_thumb_size_slider_change(self, value):
        """
        When scale slider is manipulated
        """
        self.ui.publish_view.setIconSize(QtCore.QSize(value, value))
        self._settings_manager.store("thumb_size_scale", value)

    def _on_publish_selection(self, selected, deselected):
        """
        Slot triggered when someone changes the selection in the main publish area
        """
        selected_indexes = self.ui.publish_view.selectionModel().selectedIndexes()

        if len(selected_indexes) == 0:
            self._setup_details_panel([])
        else:
            self._setup_details_panel(selected_indexes)

        # emit the selection changed signal:
        self.selection_changed.emit()

    def _on_publish_double_clicked(self, model_index):
        """
        When someone double clicks on a publish, run the default action
        """
        # the incoming model index is an index into our proxy model
        # before continuing, translate it to an index into the
        # underlying model
        proxy_model = model_index.model()
        source_index = proxy_model.mapToSource(model_index)

        # now we have arrived at our model derived from StandardItemModel
        # so let's retrieve the standarditem object associated with the index
        item = source_index.model().itemFromIndex(source_index)

        is_folder = item.data(SgLatestPublishModel.IS_FOLDER_ROLE)

        if is_folder:
            # get the corresponding tree view item
            tree_view_item = self._publish_model.get_associated_tree_view_item(item)

            # select it in the tree view
            self._select_item_in_entity_tree(
                self._current_entity_preset, tree_view_item
            )

        else:
            # Run default action.
            sg_item = shotgun_model.get_sg_data(model_index)
            default_action = self._action_manager.get_default_action_for_publish(
                sg_item, self._action_manager.UI_AREA_MAIN
            )
            if default_action:
                default_action.trigger()

    def _on_fix_files(self):
        """
        When someone clicks on the "Fix Files" button
        Send unpublished depot files to the Shotgrid Publisher.
        """
        # Get list of unpublished depot files
        self._publish_depot_data()

        msg = "\n <span style='color:#2C93E2'>Hard refreshing data...</span> \n"
        self._add_log(msg, 2)
        #self._publish_model.hard_refresh()

        self._reload_treeview()
        self._setup_details_panel([])

        self._update_perforce_data()
        self.print_publish_data()

    def _create_publisher_dir(self):
        home_dir = expanduser("~")
        self._home_dir = "{}/.publisher".format(home_dir)
        if not os.path.exists(self._home_dir):
            os.makedirs(self._home_dir)

    def _on_publish_files(self):
        files_count = len(self._action_data_to_publish)
        if files_count > 0:
            msg = "\n <span style='color:#2C93E2'>Publishing files ...</span> \n"
            self._add_log(msg, 2)

            for i, sg_item in enumerate(self._action_data_to_publish):
                if "local_path" in sg_item["path"]:
                    file_path = sg_item["path"].get("local_path", None)
                    if file_path:
                        msg = "({}/{})  Publishing file: {}".format(i + 1, files_count, file_path)
                        self._add_log(msg, 3)
                        publisher = PublishItem(sg_item)
                        publish_result = publisher.publish_file()
        else:
            msg = "\n <span style='color:#2C93E2'>There are no files to publish</span> \n"
            self._add_log(msg, 2)

        # publisher = PublishManager()
        #publisher = P4SGPUBLISHER()
        #publisher = MultiPublish2()

        #engine = sgtk.platform.current_engine()
        #engine.commands['Publish...']["callback"]()

        # Reset _action_data_to_publish list
        self._action_data_to_publish = []


    def _on_sync_files(self):
        """
        When someone clicks on the "Sync" button
        """
        #if not self._p4:
        #    self._connect()
        files_to_sync, total_file_count = self._get_files_to_sync()
        files_to_sync_count = len(files_to_sync)
        if files_to_sync_count == 0:
            msg = "\n <span style='color:#2C93E2'>No Need to sync</span> \n"
            self._add_log(msg, 2)

        elif files_to_sync_count > 0:
            msg = "\n <span style='color:#2C93E2'>Syncing {} files ... </span> \n".format(files_to_sync_count)
            self._add_log(msg, 2)
            self._do_sync_files(files_to_sync)
            msg = "\n <span style='color:#2C93E2'>Syncing files is complete</span> \n"
            self._add_log(msg, 2)
            msg = "\n <span style='color:#2C93E2'>Reloading data ...</span> \n"
            self._add_log(msg, 2)
            self._status_model.hard_refresh()
            self._publish_history_model.hard_refresh()
            # self._publish_type_model.hard_refresh()
            self._publish_model.hard_refresh()
            #for p in self._entity_presets:
            #    self._entity_presets[p].model.hard_refresh()
            self._setup_details_panel([])
            # self._get_perforce_summary()

            msg = "\n <span style='color:#2C93E2'>Reloading data is complete</span> \n"
            self._add_log(msg, 2)

    def _get_perforce_summary(self):
        """
        When someone clicks on the "Sync" button
        """
        #if not self._p4:
        #    self._connect()
        files_to_sync, total_file_count = self._get_files_to_sync()
        files_to_sync_count = len(files_to_sync)
        if files_to_sync_count == 0:
            msg = "\n <span style='color:#2C93E2'>No Need to sync</span> \n"
            self._add_log(msg, 2)



    ########################################################################################

    # Perforce connection, Sync, and related GUI items
    def _publish_depot_data(self):
        """
        Publish Depot Data
        """
        selected_item = self._get_selected_entity()
        sg_entity = shotgun_model.get_sg_data(selected_item)
        # logger.debug(">>>>>>>>>>  sg_entity {}".format(sg_entity))

        if self._depot_files_to_publish:
            msg = "\n <span style='color:#2C93E2'>Sending unpublished depot files to the Shotgrid Publisher...</span> \n"
            self._add_log(msg, 2)
            for sg_item in self._depot_files_to_publish:
                sg_item["entity"] = sg_entity
                if 'path' in sg_item:
                    file_to_publish = sg_item['path'].get('local_path', None)
                    msg = "Publishing file: {}...".format(file_to_publish)
                    self._add_log(msg, 4)
                    publisher = PublishItem(sg_item)
                    publish_result = publisher.publish_file()
                    #if publish_result:
                    #    logger.debug("New data is: {}".format(publish_result))


            msg = "\n <span style='color:#2C93E2'>Publishing files is complete</span> \n"
            self._add_log(msg, 2)
            msg = "\n <span style='color:#2C93E2'>Reloading data</span> \n"
            self._add_log(msg, 2)
            #self._reload_treeview()

        else:
            msg = "\n <span style='color:#2C93E2'>No need to publish any file</span> \n"
            self._add_log(msg, 2)

        self._depot_files_to_publish = []

    def _create_key(self, file_path):
        key = None
        if file_path:
            file_path = file_path.replace("\\", "")
            file_path = file_path.replace("/", "")
            key = file_path.lower()
        return key

    def _get_files_to_sync(self):
        """
        Get Perforce Data
        :return:
        """
        total_file_count = 0
        files_to_sync = []

        model = self.ui.publish_view.model()
        for row in range(model.rowCount()):
            model_index = model.index(row, 0)
            proxy_model = model_index.model()
            source_index = proxy_model.mapToSource(model_index)
            # now we have arrived at our model derived from StandardItemModel
            # so let's retrieve the standarditem object associated with the index
            item = source_index.model().itemFromIndex(source_index)

            is_folder = item.data(SgLatestPublishModel.IS_FOLDER_ROLE)
            if not is_folder:
                # Run default action.
                total_file_count += 1
                sg_item = shotgun_model.get_sg_data(model_index)
                # logger.info("--------->>>>>>  sg_item is: {}".format(sg_item))
                if 'path' in sg_item:
                    local_path = sg_item['path'].get('local_path', None)
                    if local_path:
                        action = sg_item.get("action", None)
                        head_action = sg_item.get("headAction", None)
                        if action and action != head_action:
                            files_to_sync.append(local_path)
                            msg = "Publishing file: {}...".format(local_path)
                            self._add_log(msg, 4)
                            publisher = PublishItem(sg_item)
                            publish_result = publisher.publish_file()
                        else:
                            have_rev = sg_item.get('haveRev', "0")
                            head_rev = sg_item.get('headRev', "0")
                            if self._to_sync(have_rev, head_rev):
                                files_to_sync.append(local_path)

        return files_to_sync, total_file_count

    def _do_sync_files(self, files_to_sync):
        """
        Get latest revision
        """
        progress_sum = 0
        total = len(files_to_sync)
        if total > 0:
            for i, file_path in enumerate(files_to_sync):
                progress_sum = ((i + 1) / total) * 100
                p4_result = self._p4.run("sync", "-f", file_path + "#head")
                logger.debug("Syncing file: {}".format(file_path))
                msg = "({}/{})  Syncing file: {}".format(i+1, total, file_path)
                self._add_log(msg, 3)
                self._update_progress(progress_sum)

    def _update_progress(self, value):
        if 100 > value > 0:
            self.ui.progress.setValue(value)
            self.ui.progress.setVisible(True)
        else:
            self.ui.progress.setVisible(False)
        QtCore.QCoreApplication.processEvents()

    def _add_log(self, msg, flag):
        if flag <= 2:
            msg = "\n{}\n".format(msg)
        else:
            msg = "{}".format(msg)
        self.ui.log_window.append(msg)
        if flag < 4:
            logger.debug(msg)
        self.ui.log_window.verticalScrollBar().setValue(self.ui.log_window.verticalScrollBar().maximum())
        QtCore.QCoreApplication.processEvents()

    def _to_sync (self, have_rev, head_rev):
        """
        Determine if we should sync the file
        """
        have_rev_int = int(have_rev)
        head_rev_int = int(head_rev)
        if head_rev_int > 0 and have_rev_int < head_rev_int:
            return True
        return False

    def _connect(self):
        """
        Connect to Perforce.  If a connection can't be established with
        the current settings then the connection UI will be shown.
        """
        try:
            if not self._p4:
                logger.debug("Connecting to perforce ...")
                self._fw = sgtk.platform.get_framework("tk-framework-perforce")
                self._p4 = self._fw.connection.connect()
        except:
            #Todo add error message
            logger.debug("Failed to connect!")
            raise
    ########################################################################################
    # cog icon actions

    def _pre_execute_action(self, action):
        """
        Called before a custom action is executed.

        :param action: The QAction that is being executed.
        """
        data = action.data()

        # If there is a single item, we'll put its name in the banner.
        if len(data) == 1:
            sg_data = data[0]["sg_publish_data"]
            name_str = sg_data.get("name") or "Unnamed"
            version_number = sg_data.get("version_number")
            vers_str = "%03d" % version_number if version_number is not None else "N/A"

            self._action_banner.show_banner(
                "<center>Action <b>%s</b> launched on <b>%s Version %s</b></center>"
                % (action.text(), name_str, vers_str)
            )
        else:
            # Otherwise we'll simply mention the selection.
            self._action_banner.show_banner(
                "<center>Action <b>%s</b> launched on selection.</center>"
                % (action.text(),)
            )

        # Force the window to be redrawn and process events right away since the
        # hooks will be run right after this method returns, which wouldn't
        # leave space for the event loop to update the UI.
        self.window().repaint()
        QtGui.QApplication.processEvents()

    def show_help_popup(self):
        """
        Someone clicked the show help screen action
        """
        app = sgtk.platform.current_bundle()
        help_pix = [
            QtGui.QPixmap(":/res/help_1.png"),
            QtGui.QPixmap(":/res/help_2.png"),
            QtGui.QPixmap(":/res/help_3.png"),
            QtGui.QPixmap(":/res/help_4.png"),
        ]
        help_screen.show_help_screen(self.window(), app, help_pix)

    def _on_doc_action(self):
        """
        Someone clicked the show docs action
        """
        app = sgtk.platform.current_bundle()
        app.log_debug("Opening documentation url %s..." % app.documentation_url)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(app.documentation_url))

    def _on_reload_action(self):
        """
        Hard reload all caches
        """
        self._status_model.hard_refresh()
        self._publish_history_model.hard_refresh()
        self._publish_type_model.hard_refresh()
        self._publish_model.hard_refresh()
        for p in self._entity_presets:
            self._entity_presets[p].model.hard_refresh()
        # self._get_perforce_summary()

    def _on_reload_action_simplified(self):
        """
        Hard reload all caches
        """
        self._status_model.hard_refresh()
        self._publish_history_model.hard_refresh()
        self._publish_type_model.hard_refresh()
        self._publish_model.hard_refresh()

    ########################################################################################
    # entity listing tree view and presets toolbar

    def _get_selected_entity(self):
        """
        Returns the item currently selected in the tree view, None
        if no selection has been made.
        """

        selected_item = None
        selection_model = self._entity_presets[
            self._current_entity_preset
        ].view.selectionModel()
        if selection_model.hasSelection():

            current_idx = selection_model.selection().indexes()[0]

            model = current_idx.model()

            if not isinstance(model, (SgHierarchyModel, SgEntityModel)):
                # proxy model!
                current_idx = model.mapToSource(current_idx)

            # now we have arrived at our model derived from StandardItemModel
            # so let's retrieve the standarditem object associated with the index
            selected_item = current_idx.model().itemFromIndex(current_idx)

        return selected_item

    def _select_tab(self, tab_caption, track_in_history):
        """
        Programmatically selects a tab based on the requested caption.

        :param str tab_caption: Name of the tab to bring forward.
        :param track_in_history: If ``True``, the tab switch will be registered in the
            history.
        """
        if tab_caption != self._current_entity_preset:
            for idx in range(self.ui.entity_preset_tabs.count()):
                tab_name = self.ui.entity_preset_tabs.tabText(idx)
                if tab_name == tab_caption:
                    # found the new tab index we should set! now switch tabs.
                    #
                    # first switch the tab widget around but without triggering event
                    # code (this would mean an infinite loop!)
                    self._disable_tab_event_handler = True
                    try:
                        self.ui.entity_preset_tabs.setCurrentIndex(idx)
                    finally:
                        self._disable_tab_event_handler = False
                    # now run the logic for the switching
                    self._switch_profile_tab(idx, track_in_history)

    def _select_item_in_entity_tree(self, tab_caption, item):
        """
        Select an item in the entity tree, ensure the tab
        which holds it is selected and scroll to make it visible.

        Item can be None - in this case, nothing is selected.
        """
        # this method is called when someone clicks the home button,
        # clicks the back/forward history buttons or double clicks on
        # a folder in the thumbnail UI.

        # there are three basic cases here:
        # 1) we are already on the right tab but need to switch item
        # 2) we are on the wrong tab and need to switch tabs and then switch item
        # 3) we are on the wrong tab and need to switch but there is no item to select

        # Phase 1 - first check if we need to switch tabs
        self._select_tab(tab_caption, item is None)

        # Phase 2 - Now select and zoom onto the item
        view = self._entity_presets[self._current_entity_preset].view
        selection_model = view.selectionModel()

        if item:
            # ensure that the tree view is expanded and that the item we are about
            # to selected is in vertically centered in the widget

            # get the currently selected item in our tab
            selected_item = self._get_selected_entity()

            if selected_item and selected_item.index() == item.index():
                # the item is already selected!
                # because there is no easy way to "kick" the selection
                # model in QT, explicitly call the callback
                # which is normally being called when an item in the
                # treeview gets selected.
                self._on_treeview_item_selected()

            else:
                # we are about to select a new item in the tree view!
                # when we pass selection indices into the view, must first convert them
                # from deep model index into proxy model index style indicies
                proxy_index = view.model().mapFromSource(item.index())
                # and now perform view operations
                view.scrollTo(proxy_index, QtGui.QAbstractItemView.PositionAtCenter)
                selection_model.select(
                    proxy_index, QtGui.QItemSelectionModel.ClearAndSelect
                )
                selection_model.setCurrentIndex(
                    proxy_index, QtGui.QItemSelectionModel.ClearAndSelect
                )

        else:
            # clear selection to match no items
            selection_model.clear()

            # note: the on-select event handler will take over at this point and register
            # history, handle click logic etc.

    def _load_entity_presets(self):
        """
        Loads the entity presets from the configuration and sets up buttons and models
        based on the config.
        """
        app = sgtk.platform.current_bundle()

        for setting_dict in app.get_setting("entities"):

            # Validate that the setting dictionary contains all items needed.
            # Here is an example of Hierarchy setting dictionary:
            #     {'caption': 'Project',
            #      'type':    'Hierarchy',
            #      'root':    '{context.project}'
            # Here is an example of Query setting dictionary:
            #     {'caption':     'My Tasks',
            #      'type':        'Query',
            #      'entity_type': 'Task',
            #      'hierarchy':   ['project', 'entity', 'content'],
            #      'filters':     [['task_assignees', 'is', '{context.user}'],
            #                      ['project.Project.sg_status', 'is', 'Active']]}

            key_error_msg = (
                "Configuration error: 'entities' item %s is missing key '%s'!"
            )
            value_error_msg = "Configuration error: 'entities' item %s key '%s' has an invalid value '%s'!"

            key = "caption"
            if key not in setting_dict:
                raise TankError(key_error_msg % (setting_dict, key))

            preset_name = setting_dict["caption"]

            key = "type"
            if key in setting_dict:
                value = setting_dict[key]
                if value not in ("Hierarchy", "Query"):
                    raise TankError(value_error_msg % (setting_dict, key, value))
                type_hierarchy = value == "Hierarchy"
            else:
                # When the type is not given, default to "Query".
                type_hierarchy = False

            if type_hierarchy:

                key = "root"
                if key not in setting_dict:
                    raise TankError(key_error_msg % (setting_dict, key))

                sg_entity_type = "Project"

            else:

                for key in ("entity_type", "hierarchy", "filters"):
                    if key not in setting_dict:
                        raise TankError(key_error_msg % (setting_dict, key))

                sg_entity_type = setting_dict["entity_type"]

            # get optional publish_filter setting
            # note: actual value in the yaml settings can be None,
            # that's why we cannot use setting_dict.get("publish_filters", [])
            publish_filters = setting_dict.get("publish_filters")
            if publish_filters is None:
                publish_filters = []

            # Create the model.
            if type_hierarchy:
                entity_root = self._get_entity_root(setting_dict["root"])
                (model, proxy_model) = self._setup_hierarchy_model(app, entity_root)
            else:
                (model, proxy_model) = self._setup_query_model(app, setting_dict)

            # Add a new tab and its layout to the main tab bar.
            tab = QtGui.QWidget()
            layout = QtGui.QVBoxLayout(tab)
            layout.setSpacing(0)
            layout.setContentsMargins(0, 0, 0, 0)
            self.ui.entity_preset_tabs.addTab(tab, preset_name)

            # Add a tree view in the tab layout.
            view = QtGui.QTreeView(tab)
            layout.addWidget(view)

            # Configure the view.
            view.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
            view.setProperty("showDropIndicator", False)
            view.setIconSize(QtCore.QSize(20, 20))
            view.setStyleSheet("QTreeView::item { padding: 6px; }")
            view.setUniformRowHeights(True)
            view.setHeaderHidden(True)
            view.setModel(proxy_model)

            # Keep a handle to all the new Qt objects, otherwise the GC may not work.
            self._dynamic_widgets.extend([model, proxy_model, tab, layout, view])

            if not type_hierarchy:

                # FIXME: We should probably remove all of this block in favor of something like. Doesn't quite
                # work at the moment so I'm leaving it as a suggestion to a future reader.
                # search = SearchWidget(tab)
                # search.setToolTip("Use the <i>search</i> field to narrow down the items displayed in the tree above.")
                # search_layout.addWidget(search)
                # search.set_placeholder_text("Search...")
                # search.search_changed.connect(
                #     lambda text, v=view, pm=proxy_model: self._on_search_text_changed(text, v, pm)
                # )

                # Add a layout to host search.
                search_layout = QtGui.QHBoxLayout()
                layout.addLayout(search_layout)

                # Add the search text field.
                search = QtGui.QLineEdit(tab)
                search.setStyleSheet(
                    "QLineEdit{ border-width: 1px; "
                    "background-image: url(:/res/search.png); "
                    "background-repeat: no-repeat; "
                    "background-position: center left; "
                    "border-radius: 5px; "
                    "padding-left:20px; "
                    "margin:4px; "
                    "height:22px; "
                    "}"
                )
                search.setToolTip(
                    "Use the <i>search</i> field to narrow down the items displayed in the tree above."
                )

                try:
                    # This was introduced in Qt 4.7, so try to use it if we can...
                    search.setPlaceholderText("Search...")
                except:
                    pass

                search_layout.addWidget(search)

                # Add a cancel search button, disabled by default.
                clear_search = QtGui.QToolButton(tab)
                icon = QtGui.QIcon()
                icon.addPixmap(
                    QtGui.QPixmap(":/res/clear_search.png"),
                    QtGui.QIcon.Normal,
                    QtGui.QIcon.Off,
                )
                clear_search.setIcon(icon)
                clear_search.setAutoRaise(True)
                # Ignore the boolean parameter in the lambda. There seems to be an odd bug here,
                # probably in PySide2. Contrary to other places where we simply
                # accept a two parameters, one for the boolean and a second default one,
                # here we have to pass a default value to checked. If we don't, we get
                #   TypeError: <lambda>() missing 1 required positional argument: 'checked'
                #
                clear_search.clicked.connect(
                    lambda checked=True, editor=search: editor.setText("")
                )
                clear_search.setToolTip("Click to clear your current search.")
                search_layout.addWidget(clear_search)

                # Drive the proxy model with the search text.
                search.textChanged.connect(
                    lambda text, v=view, pm=proxy_model: self._on_search_text_changed(
                        text, v, pm
                    )
                )

                # Keep a handle to all the new Qt objects, otherwise the GC may not work.
                self._dynamic_widgets.extend(
                    [search_layout, search, clear_search, icon]
                )

            else:
                search = shotgun_search_widget.HierarchicalSearchWidget(tab)

                search.search_root = entity_root

                # When a selection is made, we are only interested into the paths to the node so we can refresh
                # the model and expand the item.
                search.node_activated.connect(
                    lambda entity_type, entity_id, name, path_label, incremental_paths, view=view, proxy_model=proxy_model: self._node_activated(
                        incremental_paths, view, proxy_model
                    )
                )
                # When getting back the model items that were loaded, we will need the view and proxy model
                # to expand the item.
                model.async_item_retrieval_completed.connect(
                    lambda item, view=view, proxy_model=proxy_model: self._async_item_retrieval_completed(
                        item, view, proxy_model
                    )
                )
                search.set_bg_task_manager(self._task_manager)
                layout.addWidget(search)

                self._dynamic_widgets.extend([search])

            # We need to handle tool tip display ourselves for action context menus.
            def action_hovered(action):
                tip = action.toolTip()
                if tip == action.text():
                    QtGui.QToolTip.hideText()
                else:
                    QtGui.QToolTip.showText(QtGui.QCursor.pos(), tip)

            # Set up a view right click menu.
            if type_hierarchy:

                action_ca = QtGui.QAction("Collapse All Folders", view)
                action_ca.hovered.connect(lambda: action_hovered(action_ca))
                action_ca.triggered.connect(view.collapseAll)
                view.addAction(action_ca)
                self._dynamic_widgets.append(action_ca)

                action_reset = QtGui.QAction("Reset", view)
                action_reset.setToolTip(
                    "<nobr>Reset the tree to its SG hierarchy root collapsed state.</nobr><br><br>"
                    "Any existing data contained in the tree will be cleared, "
                    "affecting selection and other related states, and "
                    "available cached data will be immediately reloaded.<br><br>"
                    "The rest of the data will be lazy-loaded when navigating down the tree."
                )
                action_reset.hovered.connect(lambda: action_hovered(action_reset))
                action_reset.triggered.connect(model.reload_data)
                view.addAction(action_reset)
                self._dynamic_widgets.append(action_reset)

            else:

                action_ea = QtGui.QAction("Expand All Folders", view)
                action_ea.hovered.connect(lambda: action_hovered(action_ea))
                action_ea.triggered.connect(view.expandAll)
                view.addAction(action_ea)
                self._dynamic_widgets.append(action_ea)

                action_ca = QtGui.QAction("Collapse All Folders", view)
                action_ca.hovered.connect(lambda: action_hovered(action_ca))
                action_ca.triggered.connect(view.collapseAll)
                view.addAction(action_ca)
                self._dynamic_widgets.append(action_ca)

                action_refresh = QtGui.QAction("Refresh", view)
                action_refresh.setToolTip(
                    "<nobr>Refresh the tree data to ensure it is up to date with ShotGrid.</nobr><br><br>"
                    "Since this action is done in the background, the tree update "
                    "will be applied whenever the data is returned from ShotGrid.<br><br>"
                    "When data has been added, it will be added into the existing tree "
                    "without affecting selection and other related states.<br><br>"
                    "When data has been modified or deleted, a tree rebuild will be done, "
                    "affecting selection and other related states."
                )
                action_refresh.hovered.connect(lambda: action_hovered(action_refresh))
                action_refresh.triggered.connect(model.async_refresh)
                view.addAction(action_refresh)
                self._dynamic_widgets.append(action_refresh)

            view.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

            # Set up an on-select callback.
            selection_model = view.selectionModel()
            self._dynamic_widgets.append(selection_model)

            selection_model.selectionChanged.connect(self._on_treeview_item_selected)

            overlay = ShotgunModelOverlayWidget(model, view)
            self._dynamic_widgets.append(overlay)

            # Store all these objects keyed by the caption.
            ep = EntityPreset(
                preset_name, sg_entity_type, model, proxy_model, view, publish_filters
            )

            self._entity_presets[preset_name] = ep

        # hook up an event handler when someone clicks a tab
        self.ui.entity_preset_tabs.currentChanged.connect(
            self._on_entity_profile_tab_clicked
        )

        # finalize initialization by clicking the home button, but only once the
        # data has properly arrived in the model.
        self._on_home_clicked()

    def _get_entity_root(self, root):
        """
        Translates the string from the settings into an entity.

        :param str root: Can be '{context.project} or empty.

        :returns: Entity that will be used for the root.
        """

        app = sgtk.platform.current_bundle()

        # FIXME: API doesn't support non-project entities as the root yet.
        # if root == "{context.entity}":
        #     if app.context.entity:
        #         return app.context.entity
        #     else:
        #         app.log_warning(
        #             "There is no entity in the current context %s. "
        #             "Hierarchy will default to project." % app.context
        #         )
        #         root = "{context.project}"

        if root == "{context.project}":
            if app.context.project:
                return app.context.project
            else:
                app.log_warning(
                    "There is no project in the current context %s. "
                    "Hierarchy will default to site." % app.context
                )
                root = None

        if root is not None:
            app.log_warning(
                "Unknown root was specified: %s. "
                "Hierarchy will default to site." % root
            )

        return None

    def _setup_hierarchy_model(self, app, root):
        """
        Create the model and proxy model required by a hierarchy type configuration setting.

        :param app: :class:`Application`, :class:`Engine` or :class:`Framework` bundle instance
                    associated with the loader.
        :param root: The path to the root of the Shotgun hierarchy to display.
        :return: Created `(model, proxy model)`.
        """

        # If the root is a project, include it in the hierarchy model so that
        # we can display project publishes. We do an innocent little hack here
        # by including a space at the front of the project root item to make it
        # display first in the tree.
        if root.get("type") == "Project":
            include_root = " %s" % (root.get("name", "Project Publishes"),)

        # Construct the hierarchy model and load a hierarchy that leads
        # to entities that are linked via the "PublishedFile.entity" field.
        model = SgHierarchyModel(
            self,
            root_entity=root,
            bg_task_manager=self._task_manager,
            include_root=include_root,
        )

        # Create a proxy model.
        proxy_model = QtGui.QSortFilterProxyModel(self)
        proxy_model.setSourceModel(model)

        # Impose and keep the sorting order on the default display role text.
        proxy_model.sort(0)
        proxy_model.setDynamicSortFilter(True)

        # When clicking on a node, we fetch all the nodes under it so we can populate the
        # right hand-side. Make sure we are notified when the child come back so we can load
        # publishes for the current item.
        model.data_refreshed.connect(self._hierarchy_refreshed)

        return (model, proxy_model)

    def _hierarchy_refreshed(self):
        """
        Slot triggered when the hierarchy model has been refreshed. This allows to show all the
        folder items in the right-hand side for the current selection.
        """
        selected_item = self._get_selected_entity()

        # tell publish UI to update itself
        self._load_publishes_for_entity_item(selected_item)

    def _node_activated(self, incremental_paths, view, proxy_model):
        """
        Called when a user picks a result from the search widget.
        """
        source_model = proxy_model.sourceModel()
        # Asynchronously retrieve the nodes that lead to the item we picked.
        source_model.async_item_from_paths(incremental_paths)

    def _async_item_retrieval_completed(self, item, view, proxy_model):
        """
        Called when the last node from the deep load is loaded.
        """
        # Ask the view to set the current index.
        proxy_idx = proxy_model.mapFromSource(item.index())
        view.setCurrentIndex(proxy_idx)

    def _setup_query_model(self, app, setting_dict):
        """
        Create the model and proxy model required by a query type configuration setting.

        :param app: :class:`Application`, :class:`Engine` or :class:`Framework` bundle instance
                    associated with the loader.
        :param setting_dict: Configuration setting dictionary for a tab.
        :return: Created `(model, proxy model)`.
        """

        # Resolve any magic tokens in the filters.
        resolved_filters = resolve_filters(setting_dict["filters"])
        setting_dict["filters"] = resolved_filters

        # Construct the query model.
        model = SgEntityModel(
            self,
            setting_dict["entity_type"],
            setting_dict["filters"],
            setting_dict["hierarchy"],
            self._task_manager,
        )

        # Create a proxy model.
        proxy_model = SgEntityProxyModel(self)
        proxy_model.setSourceModel(model)

        return (model, proxy_model)

    def _on_search_text_changed(self, pattern, tree_view, proxy_model):
        """
        Triggered when the text in a search editor changes.

        :param pattern: new contents of search box
        :param tree_view: associated tree view.
        :param proxy_model: associated proxy model
        """

        # tell proxy model to reevaulate itself given the new pattern.
        proxy_model.setFilterFixedString(pattern)

        # change UI decorations based on new pattern.
        # for performance, make sure filtering only kicks in
        # once we have typed a couple of characters
        if pattern and len(pattern) >= constants.TREE_SEARCH_TRIGGER_LENGTH:
            # indicate with a blue border that a search is active
            tree_view.setStyleSheet(
                """
                QTreeView {{
                    border-width: 3px;
                    border-style: solid;
                    border-color: {highlight};
                }}
                QTreeView::item {{
                    padding: 6px;
                }}
                """.format(
                    highlight=self.palette().highlight().color().name()
                )
            )
            # expand all nodes in the tree
            tree_view.expandAll()
        else:
            # revert to default style sheet
            tree_view.setStyleSheet("QTreeView::item { padding: 6px; }")

    def _on_entity_profile_tab_clicked(self):
        """
        Called when someone clicks one of the profile tabs
        """
        if not self._disable_tab_event_handler:
            curr_tab_index = self.ui.entity_preset_tabs.currentIndex()
            self._switch_profile_tab(curr_tab_index, track_in_history=True)

    def _switch_profile_tab(self, new_index, track_in_history):
        """
        Switches to use the specified profile tab.

        :param new_index: tab index to switch to
        :param track_in_history: Hint to this method that the actions should be tracked in the
            history.
        """
        # qt returns unicode/qstring here so force to str
        curr_tab_name = shotgun_model.sanitize_qt(
            self.ui.entity_preset_tabs.tabText(new_index)
        )

        # and set up which our currently visible preset is
        self._current_entity_preset = curr_tab_name

        # The hierarchy model cannot handle "Show items in subfolders" mode.
        if isinstance(
            self._entity_presets[self._current_entity_preset].model, SgHierarchyModel
        ):
            self.ui.show_sub_items.hide()
        else:
            self.ui.show_sub_items.show()

        if self._history_navigation_mode == False:
            # When we are not navigating back and forth as part of history navigation,
            # ask the currently visible view to (background async) refresh its data.
            # Refreshing the data only makes sense for SgEntityModel based tabs since
            # SgHierarchyModel does not yet support this kind of functionality.
            model = self._entity_presets[self._current_entity_preset].model
            if isinstance(model, SgEntityModel):
                model.async_refresh()

        if track_in_history:
            # figure out what is selected
            selected_item = self._get_selected_entity()

            # update breadcrumbs
            self._populate_entity_breadcrumbs(selected_item)

            # add history record
            self._add_history_record(self._current_entity_preset, selected_item)

            # tell details view to clear
            self._setup_details_panel([])

            # tell the publish view to change
            self._load_publishes_for_entity_item(selected_item)

    def _get_entity_path(self, entity_data):
        """
        Get entity path
        """
        entity_path = None
        #logger.debug(">>>>>>>>>>>>>> entity_data is: {}".format(entity_data))
        if entity_data:
            entity_id = entity_data.get('id', 0)
            entity_type = entity_data.get('type', None)
            entity_path = self._app.sgtk.paths_from_entity(entity_type, entity_id)
            if not entity_path:
                self._app.sgtk.create_filesystem_structure(entity_type, entity_id)
                entity_path = self._app.sgtk.paths_from_entity(entity_type, entity_id)
            if entity_path and len(entity_path) > 0:
                entity_path = entity_path[0]
                msg = "\n <span style='color:#2C93E2'>Entity path: {}</span> \n".format(entity_path)
                self._add_log(msg, 2)
        return entity_path

    def _on_treeview_item_selected(self):
        """
        Slot triggered when someone changes the selection in a treeview.
        """

        entity_data = self._reload_treeview()
        self._entity_path = self._get_entity_path(entity_data)

        self.get_current_sg_data()

        self._update_perforce_data()
        self.print_publish_data()

    def get_current_sg_data(self):
        total_file_count = 0
        self._sg_data = []
        self._depot_files_to_publish = []

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
                    total_file_count += 1
                    sg_item = shotgun_model.get_sg_data(model_index)
                    self._sg_data.append(sg_item)
                # else:
                #    is_folder = selected_item.data(SgLatestPublishModel.IS_FOLDER_ROLE)
                #     if not is_folder:
                #        self._publish_main_overlay.show_message_pixmap(self._no_pubs_found_icon)

        # time.sleep(1)
        #logger.debug(">>>>>>>>>>  sg_data is: {}".format(self._sg_data))

    def _update_perforce_data(self):

        self._get_peforce_data()
        #logger.debug(">>>>>>>>>>  self._fstat_dict is: {}".format(self._fstat_dict))

        msg = "\n <span style='color:#2C93E2'>Updating data ...</span> \n"
        self._add_log(msg, 2)
        self._update_fstat_data()
        self._get_depot_files_to_publish()

        #msg = "\n <span style='color:#2C93E2'>Soft refreshing data ...</span> \n"
        #self._add_log(msg, 2)
        self._publish_model.async_refresh()

    def print_publish_data(self):
        if self._depot_files_to_publish:
            msg = "\n <span style='color:#2C93E2'>List of unpublished depot files:</span> \n"
            self._add_log(msg, 2)
            for sg_item in self._depot_files_to_publish:
                if 'path' in sg_item:
                    file_to_publish = sg_item['path'].get('local_path', None)
                    msg = "{}".format(file_to_publish)
                    self._add_log(msg, 4)
            msg = "\n <span style='color:#2C93E2'>Click on 'Fix Files' to publish above files</span> \n"
            self._add_log(msg, 2)

    def _update_fstat_data(self):
        if self._fstat_dict:
            model = self.ui.publish_view.model()
            for row in range(model.rowCount()):
                model_index = model.index(row, 0)
                proxy_model = model_index.model()
                source_index = proxy_model.mapToSource(model_index)
                item = source_index.model().itemFromIndex(source_index)

                is_folder = item.data(SgLatestPublishModel.IS_FOLDER_ROLE)
                if not is_folder:
                    sg_item = shotgun_model.get_sg_data(model_index)
                    if "path" in sg_item:
                        if "local_path" in sg_item["path"]:
                            local_path = sg_item["path"].get("local_path", None)
                            modified_local_path = self._create_key(local_path)

                            if modified_local_path and modified_local_path in self._fstat_dict:
                                self._fstat_dict[modified_local_path]['Published'] = True

                                have_rev = self._fstat_dict[modified_local_path].get('haveRev', "0")
                                head_rev = self._fstat_dict[modified_local_path].get('headRev', "0")

                                sg_item["haveRev"], sg_item["headRev"] = have_rev, head_rev
                                sg_item["revision"] = "{}/{}".format(have_rev, head_rev)
    
                                sg_item["headAction"] = self._fstat_dict[modified_local_path].get('headAction', None)
                                sg_item["action"] = self._fstat_dict[modified_local_path].get('action', None)
                                sg_item["sg_status_list"] = self._fstat_dict[modified_local_path].get('sg_status_list', None)
                                
                                # logger.debug(">>>>>>>>>>  Updated sg_item is: {}".format(sg_item.get("revision", None)))
                                item.setData(sg_item, SgLatestPublishModel.SG_DATA_ROLE)
                                #new_sg_item = shotgun_model.get_sg_data(model_index)
                                #logger.debug(">>>>>>>>>>  new sg_item revision data is: {}".format(new_sg_item.get("revision", None)))
                                #logger.debug(">>>>>>>>>>  new sg_item revision action is: {}".format(new_sg_item.get("action", None)))

    def _get_depot_files_to_publish(self):
        for key in self._fstat_dict:
            if not self._fstat_dict[key]["Published"]:
                sg_item = {}
                # sg_item = self._fstat_dict[key]
                file_path = self._fstat_dict[key].get("clientFile", None)
                # logger.debug("----->>>>>>>    file_path: {}".format(file_path))
                if file_path:
                    sg_item["name"] = os.path.basename(file_path)
                    sg_item["path"] = {}
                    sg_item["path"]["local_path"] = file_path
                sg_item["code"] = "{}#{}".format(sg_item["name"], self._fstat_dict[key].get("headRev", 0))
                # sg_item["type"] = "depotFile"
                # sg_item["published_file_type"] = None
                have_rev = self._fstat_dict[key].get('haveRev', "0")
                head_rev = self._fstat_dict[key].get('headRev', "0")
                sg_item["haveRev"] = have_rev
                sg_item["headRev"] = head_rev
                sg_item["revision"] = "#{}/{}".format(have_rev, head_rev)
                sg_item["created_at"] = 0
                sg_item["depotFile"] = self._fstat_dict[key].get('depotFile', None)
                sg_item["headChange"] = self._fstat_dict[key].get('headChange', "0")
                sg_item["headModTime"] = self._fstat_dict[key].get('headModTime', "0")
                # sg_item["version_number"] = self._fstat_dict[key]["headRev"]

                p4_status = self._fstat_dict[key].get("headAction", None)
                sg_item["sg_status_list"] = self._get_p4_status(p4_status)

                sg_item["depot_file_type"] = self._get_publish_type(file_path)
                #  file_path : {}".format(file_path))
                if file_path:
                    description, user = self._get_file_log(file_path)
                    if description:
                        sg_item["description"] = description
                    self._depot_files_to_publish.append(sg_item)
                #logger.debug("----->>>>>>>    sg_item to publish: {}".format(sg_item))

    def _on_publish_model_action(self, action):
        #if not self._p4:
        #    self._connect()
        selected_indexes = self.ui.publish_view.selectionModel().selectedIndexes()
        for model_index in selected_indexes:
            proxy_model = model_index.model()
            source_index = proxy_model.mapToSource(model_index)
            item = source_index.model().itemFromIndex(source_index)

            is_folder = item.data(SgLatestPublishModel.IS_FOLDER_ROLE)
            if not is_folder:
                sg_item = shotgun_model.get_sg_data(model_index)

                if "path" in sg_item:
                    if "local_path" in sg_item["path"]:
                        target_file = sg_item["path"].get("local_path", None)
                        target_change = "default"
                        # Actions: add, edit, delete
                        #args = "-c {} -v {}".format(target_change, target_file)
                        args = "-n {}".format(target_file)
                        if action == "add":
                            msg = "Add file {} to changelist {}".format(target_file, target_change)
                            self._add_log(msg, 3)
                            # self._p4.run("add", args)
                            p4_result = self._p4.run("add", "-v", target_file)
                            if p4_result:
                                sg_item["sg_status_list"] = "p4add"
                                sg_item["action"] = "add"
                                sg_item["description"] = "Adding file"
                                item.setData(sg_item, SgLatestPublishModel.SG_DATA_ROLE)
                                #self._action_data_to_publish.append(sg_item)
                        elif action == "edit":
                            msg = "Edit file {} to changelist {}".format(target_file, target_change)
                            self._add_log(msg, 3)
                            # self._p4.run("edit", args)
                            p4_result = self._p4.run("edit", "-v", target_file)
                            if p4_result:
                                sg_item["sg_status_list"] = "p4edit"
                                sg_item["action"] = "edit"
                                sg_item["description"] = "Editing file"
                                item.setData(sg_item, SgLatestPublishModel.SG_DATA_ROLE)
                                #self._action_data_to_publish.append(sg_item)
                        elif action == "delete":
                            # msg = "Open file {} in a client workspace for deletion from the depot using changelist {}".format(target_file, target_change)
                            msg = "Delete file {} to changelist {}".format(target_file, target_change)
                            self._add_log(msg, 3)
                            #self._p4.run("delete", args)
                            p4_result = self._p4.run("delete", "-v", target_file)
                            if p4_result:
                                sg_item["sg_status_list"] = "p4del"
                                sg_item["action"] = "delete"
                                sg_item["description"] = "Deleting file"
                                #item.setData(sg_item, SgLatestPublishModel.SG_DATA_ROLE)
                                #self._action_data_to_publish.append(sg_item)

                        #logger.debug(">>>> sg_item to publish: {}", sg_item)
                        #msg = "Publishing file: {}".format(target_file)
                        #self._add_log(msg, 3)
                        #publisher = PublishItem(sg_item)
                        #publish_result = publisher.publish_file()

        self._update_perforce_data()
        # self.print_publish_data()
        self._publish_model.hard_refresh()
        #self._publish_model.async_refresh()


    def _reload_treeview(self):
        """
        Slot triggered when someone changes the selection in a treeview.
        """
        sg_data = {}
        selected_item = self._get_selected_entity()

        # update breadcrumbs
        self._populate_entity_breadcrumbs(selected_item)

        # when an item in the treeview is selected, the child
        # nodes are displayed in the main view, so make sure
        # they are loaded.
        model = self._entity_presets[self._current_entity_preset].model
        if selected_item and model.canFetchMore(selected_item.index()):
            model.fetchMore(selected_item.index())
        #sg_item = model.get_sg_data(selected_item.index())
        #logger.debug(">>>>>>>>>>  Asset sg_data is: {}".format(sg_item))
        #logger.debug(">>>>>>>>>>  selected_item is: {}".format(selected_item))
        #logger.debug(">>>>>>>>>>  model is: {}".format(model))
        #logger.debug(">>>>>>>>>>  self._current_entity_preset is: {}".format(self._current_entity_preset))

        # notify history
        self._add_history_record(self._current_entity_preset, selected_item)

        # tell details panel to clear itself
        self._setup_details_panel([])

        # tell publish UI to update itself
        sg_data = self._load_publishes_for_entity_item(selected_item)
        return sg_data

    def _load_publishes_for_entity_item(self, item):
        """
        Given an item from the treeview, or None if no item
        is selected, prepare the publish area UI.
        """

        # clear selection. If we don't clear the model at this point,
        # the selection model will attempt to pair up with the model is
        # data is being loaded in, resulting in many many events
        sg_data = {}
        self.ui.publish_view.selectionModel().clear()

        # Determine the child folders.
        child_folders = []
        proxy_model = self._entity_presets[self._current_entity_preset].proxy_model

        if item is None:
            # nothing is selected, bring in all the top level
            # objects in the current tab
            num_children = proxy_model.rowCount()

            for x in range(num_children):
                # get the (proxy model) index for the child
                child_idx_proxy = proxy_model.index(x, 0)
                # switch to shotgun model index
                child_idx = proxy_model.mapToSource(child_idx_proxy)
                # resolve the index into an actual standarditem object
                i = self._entity_presets[
                    self._current_entity_preset
                ].model.itemFromIndex(child_idx)
                child_folders.append(i)

        else:
            # we got a specific item to process!

            # now get the proxy model level item instead - this way we can take search into
            # account as we show the folder listings.
            root_model_idx = item.index()
            root_model_idx_proxy = proxy_model.mapFromSource(root_model_idx)
            num_children = proxy_model.rowCount(root_model_idx_proxy)

            # get all the folder children - these need to be displayed
            # by the model as folders

            for x in range(num_children):
                # get the (proxy model) index for the child
                child_idx_proxy = root_model_idx_proxy.child(x, 0)
                # switch to shotgun model index
                child_idx = proxy_model.mapToSource(child_idx_proxy)
                # resolve the index into an actual standarditem object
                i = self._entity_presets[
                    self._current_entity_preset
                ].model.itemFromIndex(child_idx)
                child_folders.append(i)

        # Is the show child folders checked?
        # The hierarchy model cannot handle "Show items in subfolders" mode.
        show_sub_items = self.ui.show_sub_items.isChecked() and not isinstance(
            self._entity_presets[self._current_entity_preset].model, SgHierarchyModel
        )

        if show_sub_items:
            # indicate this with a special background color
            color = self.palette().highlight().color()
            self.ui.publish_view.setStyleSheet(
                "#publish_view {{ background-color: rgba({red}, {green}, {blue}, 20%); }}".format(
                    red=color.red(), green=color.green(), blue=color.blue()
                )
            )
            if len(child_folders) > 0:
                # delegates are rendered in a special way
                # if we are on a non-leaf node in the tree (e.g there are subfolders)
                self._publish_thumb_delegate.set_sub_items_mode(True)
                self._publish_list_delegate.set_sub_items_mode(True)
            else:
                # we are at leaf level and the subitems check box is checked
                # render the cells
                self._publish_thumb_delegate.set_sub_items_mode(False)
                self._publish_list_delegate.set_sub_items_mode(False)
        else:
            self.ui.publish_view.setStyleSheet("")
            self._publish_thumb_delegate.set_sub_items_mode(False)
            self._publish_list_delegate.set_sub_items_mode(False)

        # now finally load up the data in the publish model
        publish_filters = self._entity_presets[
            self._current_entity_preset
        ].publish_filters
        sg_data = self._publish_model.load_data(
            item, child_folders, show_sub_items, publish_filters
        )
        #logger.info(">>>> item is {}".format(item))
        #logger.info(">>>> child_folders is {}".format(child_folders))
        #logger.info(">>>> show_sub_items is {}".format(show_sub_items))
        #logger.info(">>>> publish_filters is {}".format(publish_filters))
        #logger.info(">>>> sg_data is {}".format(sg_data))
        return sg_data


    def _populate_entity_breadcrumbs(self, selected_item):
        """
        Computes the current entity breadcrumbs

        :param selected_item: Item currently selected in the tree view or
                              `None` when no selection has been made.
        """

        crumbs = []

        if selected_item:

            # figure out the tree view selection,
            # walk up to root, list of items will be in bottom-up order...
            tmp_item = selected_item
            while tmp_item:

                # Extract the Shotgun data and field value from the node item.
                (sg_data, field_value) = model_item_data.get_item_data(tmp_item)

                # now figure out the associated value and type for this node

                if sg_data:
                    # leaf node
                    name = str(field_value)
                    sg_type = sg_data.get("type")

                elif (
                    isinstance(field_value, dict)
                    and "name" in field_value
                    and "type" in field_value
                ):
                    name = field_value["name"]
                    sg_type = field_value["type"]

                elif isinstance(field_value, list):
                    # this is a list of some sort. Loop over all elements and extrat a comma separated list.
                    formatted_values = []
                    if len(field_value) == 0:
                        # no items in list
                        formatted_values.append("No Value")
                    for v in field_value:
                        if isinstance(v, dict) and "name" in v and "type" in v:
                            # This is a link field
                            if v.get("name"):
                                formatted_values.append(v.get("name"))
                        else:
                            formatted_values.append(str(v))

                    name = ", ".join(formatted_values)
                    sg_type = None

                else:
                    # other value (e.g. intermediary non-entity link node like sg_asset_type)
                    name = str(field_value)
                    sg_type = None

                # now set up the crumbs
                if sg_type is None:
                    crumbs.append(name)

                else:
                    # lookup the display name for the entity type:
                    sg_type_display_name = shotgun_globals.get_type_display_name(
                        sg_type
                    )
                    crumbs.append("<b>%s</b> %s" % (sg_type_display_name, name))
                tmp_item = tmp_item.parent()

        # lastly add the name of the tab
        crumbs.append("<b>%s</b>" % self._current_entity_preset)

        breadcrumbs = " <span style='color:#2C93E2'>&#9656;</span> ".join(crumbs[::-1])

        self.ui.entity_breadcrumbs.setText("<big>%s</big>" % breadcrumbs)

    ################################################################################################
    def _get_peforce_data(self):

        """
        if len(self._sg_data) <= 1:
            logger.debug(">>>>>>>>>>  Processing small data")

            self._get_small_peforce_data(self._sg_data)
        else:
        """
        logger.debug(">>>>>>>>>>  Processing large data ...")
        self._get_large_peforce_data()

    def _get_large_peforce_data(self):
        """"
        Get large perforce data
        """
        item_path_dict = defaultdict(int)
        self._fstat_dict = {}
        self._depot_files_to_publish = []
        # logger.debug("self._entity_path is: {}".format(self._entity_path))
        if self._entity_path:
            if not os.path.exists(self._entity_path):
                item_path_dict[self._entity_path] += 1
                #logger.debug("item_path_dict is: {}".format(item_path_dict))
        else:
            if self._sg_data:
                for i, sg_item in enumerate(self._sg_data):
                    #if i == 0:
                    #    logger.debug("sg_item is: {}".format(sg_item))
                    if "path" in sg_item:
                        local_path = sg_item["path"].get("local_path", None)
                        if local_path:
                            # logger.debug("local_path is: {}".format(local_path))
                            # item_path = self._get_item_path(local_path)
                            item_path = os.path.dirname(local_path)
                            item_path_dict[item_path] += 1
                #logger.debug(">>>>>>>>>>  item_path_dict is: {}".format(item_path_dict))

        for key in item_path_dict:
            if key:
                # logger.debug(">>>>>>>>>>  key is: {}".format(key))
                key = "{}\\...".format(key)
                # logger.debug("^^^ key is: {}".format(key))
                fstat_list = self._p4.run("fstat", key)
                for i, fstat in enumerate(fstat_list):
                    #if i == 0:
                    #logger.debug(">>>>>>>>>  fstat is: {}".format(fstat))
                    # logger.debug("{}: >>>>>  fstat is: {}".format(i, fstat))
                    client_file = fstat.get('clientFile', None)
                    # if i == 0:
                    #    logger.debug(">>>>>>>>>>  client_file is: {}".format(client_file))
                    if client_file:

                        # if i == 0:
                        #    logger.debug(">>>>>>>>>>  have_rev is: {}".format(have_rev))
                        #    logger.debug(">>>>>>>>>>  head_rev is: {}".format(head_rev))
                        modified_client_file = self._create_key(client_file)
                        if modified_client_file not in self._fstat_dict:

                            # if i == 0:
                            #    logger.debug(">>>>>>>>>>  client_file is: {}".format(client_file))
                            self._fstat_dict[modified_client_file] = {}
                            # self._fstat_dict[modified_client_file] = fstat
                            self._fstat_dict[modified_client_file]['clientFile'] = client_file
                            self._fstat_dict[modified_client_file]['haveRev'] = fstat.get('haveRev', "0")
                            self._fstat_dict[modified_client_file]['headRev'] = fstat.get('headRev', "0")
                            self._fstat_dict[modified_client_file]['Published'] = False
                            self._fstat_dict[modified_client_file]['headModTime'] = fstat.get('headModTime', 'N/A')
                            self._fstat_dict[modified_client_file]['depotFile'] = fstat.get('depotFile', None)
                            self._fstat_dict[modified_client_file]['headAction'] = fstat.get('headAction', None)
                            self._fstat_dict[modified_client_file]['action'] = fstat.get('action', None)
                            self._fstat_dict[modified_client_file]['headChange'] = fstat.get('headChange', None)
                            action = fstat.get('action', None)
                            if action:
                                sg_status = self._get_p4_status(action)
                                if sg_status:
                                    self._fstat_dict[modified_client_file]['sg_status_list'] = sg_status

                            # if i == 0:
                            #     logger.debug(">>>>>>>>>>  self._fstat_dict[client_file] is: {}".format(self._fstat_dict[modified_client_file]))
        #logger.debug(">>>>>>>>>>  self._fstat_dict is: {}".format(self._fstat_dict))

    def _get_file_log(self, file_path):
        try:
            filelog_list = self._p4.run("filelog", file_path)
            # logger.debug(">>>>>> filelog_list: {}".format(filelog_list))
            if filelog_list:
                filelog = filelog_list[0]
                # 'desc': ['- Climb Idle ']
                desc = filelog.get("desc", None)
                if desc:
                    desc = desc[0]
                    if desc.startswith("-"):
                        desc = desc[1:]
                    if desc.startswith(" "):
                        desc = desc[1:]
                # 'user': ['michael']
                user = filelog.get("user", None)
                if user:
                    user = user[0]
                    user = user.capitalize()
                return desc, user
            else:
                return None, None
        except:
            return None, None

    def _get_publish_type(self, publish_path):
        """
        Get a publish type
        """
        publish_type = None
        publish_path = os.path.splitext(publish_path)
        if len(publish_path) >= 2:
            extension = publish_path[1]

            # ensure lowercase and no dot
            if extension:
                extension = extension.lstrip(".").lower()
                publish_type = self.settings.get(extension, None)
                if not publish_type:
                    # publish type is based on extension
                    publish_type = "%s File" % extension.capitalize()
            else:
                # no extension, assume it is a folder
                publish_type = "Folder"
        return publish_type

    def _get_p4_status(self, p4_status):

        p4_status = p4_status.lower()
        sg_status = self.status_dict.get(p4_status, None)
        # logger.debug("p4_status: {}".format(p4_status))
        # logger.debug("sg_status: {}".format(sg_status))
        return sg_status

    def _create_key(self, file_path):
        if file_path:
            file_path = file_path.replace("\\", "")
            file_path = file_path.replace("/", "")
            file_path = file_path.lower()
        return file_path


    def _get_item_path (self, local_path):
        """
        Get item path
        """
        item_path = ""
        if local_path:
            local_path = local_path.split("\\")
            local_path = local_path[:7]
            item_path = "\\".join(local_path)
        return item_path

    def _get_small_peforce_data(self, sg_data):
        """"
        Get small perforce data
        """

        if sg_data:
            for i, sg_item in enumerate(sg_data):
                if "path" in sg_item:
                    local_path = sg_item["path"].get("local_path", None)

                    # logger.debug(">>>>>>> local_path is: {}".format(local_path))
                    if local_path:
                        fstat_list = self._p4.run("fstat", local_path)
                        # logger.debug("fstat_list: {}".format(fstat_list))
                        fstat = fstat_list[0]
                        # logger.debug("fstat is: {}".format(fstat))
                        have_rev = fstat.get('haveRev', "0")
                        head_rev = fstat.get('headRev', "0")
                        sg_item["haveRev"], sg_item["headRev"] = have_rev, head_rev
                        sg_item["revision"] = "{}/{}".format(have_rev, head_rev )
                        # logger.debug("{}: Revision: {}".format(i, sg_item["revision"]))
                        # sg_item['depotFile'] = fstat.get('depotFile', None)

            # logger.debug("{}: SG item: {}".format(i, sg_item))

        return sg_data

    def _get_latest_revision(self, files_to_sync):
        for file_path in files_to_sync:
            p4_result = self._p4.run("sync", "-f", file_path + "#head")
            logger.debug("Syncing file: {}".format(file_path))

    def _to_sync (self, have_rev, head_rev):
        """
        Determine if we should sync the file
        """
        have_rev_int = int(have_rev)
        head_rev_int = int(head_rev)
        if head_rev_int > 0 and have_rev_int < head_rev_int:
            return True
        return False

    def _get_depot_path(self, local_path):
        """
        Convert local path to depot path
        For example, convert: 'B:\\Ark2Depot\\Content\\Base\\Characters\\Human\\Survivor\\Armor\\Cloth_T3\\_ven\\MDL\\Survivor_M_Armor_Cloth_T3_MDL.fbx'
        to "//Ark2Depot/Content/Base/Characters/Human/Survivor/Armor/Cloth_T3/_ven/MDL/Survivor_M_Armor_Cloth_T3_MDL.fbx"
        """
        local_path = local_path[2:]
        depot_path = local_path.replace("\\", "/")
        depot_path = "/{}".format(depot_path)
        return depot_path


################################################################################################
# Helper stuff


class EntityPreset(object):
    """
    Little struct that represents one of the tabs / presets in the
    Left hand side entity tree view
    """

    def __init__(self, name, entity_type, model, proxy_model, view, publish_filters):
        self.model = model
        self.proxy_model = proxy_model
        self.name = name
        self.view = view
        self.entity_type = entity_type
        self.publish_filters = publish_filters
