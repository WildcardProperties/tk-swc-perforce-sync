
from sgtk.platform.qt import QtCore
for name, cls in QtCore.__dict__.items():
    if isinstance(cls, type): globals()[name] = cls

from sgtk.platform.qt import QtGui
for name, cls in QtGui.__dict__.items():
    if isinstance(cls, type): globals()[name] = cls

datas = {
    "Category 1": [
        ("New Game 2", "Playnite2", "", "", "A", "Played", ""),
        ("New Game 3", "Playnite3", "", "", "B", "Not Played", ""),
    ],
    "No Category": [
        ("New Game", "Playnite1", "", "", "C", "Not Plated", ""),
    ]
}

class GroupDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super(GroupDelegate, self).__init__(parent)
        #self._plus_icon = QIcon("plus.png")
        #self._minus_icon = QIcon("minus.png")

    def initStyleOption(self, option, index):
        super(GroupDelegate, self).initStyleOption(option, index)
        if not index.parent().isValid():
            is_open = bool(option.state & QStyle.State_Open)
            option.features |= QStyleOptionViewItem.HasDecoration
            #option.icon = self._minus_icon if is_open else self._plus_icon

class GroupView(QTreeView):
    def __init__(self, model, parent=None):
        super(GroupView, self).__init__(parent)
        self.setIndentation(0)
        self.setExpandsOnDoubleClick(False)
        self.clicked.connect(self.on_clicked)
        delegate = GroupDelegate(self)
        self.setItemDelegateForColumn(0, delegate)
        self.setModel(model)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        #self.setStyleSheet("background-color: #0D1225;")

        # Enable sorting by column
        self.setSortingEnabled(True)

    @pyqtSlot(QModelIndex)
    def on_clicked(self, index):
        if not index.parent().isValid() and index.column() == 0:
            self.setExpanded(index, not self.isExpanded(index))


class GroupModel(QStandardItemModel):
    def __init__(self, parent=None):
        super(GroupModel, self).__init__(parent)
        self.setColumnCount(8)
        self.setHorizontalHeaderLabels(["", "Name", "Library", "Release Date", "Genre(s)", "Last Played", "Time Played", ""])
        for i in range(self.columnCount()):
            it = self.horizontalHeaderItem(i)
            #it.setForeground(QColor("#F2F2F2"))

    def add_group(self, group_name):
        item_root = QStandardItem()
        item_root.setEditable(False)
        item = QStandardItem(group_name)
        item.setEditable(False)
        ii = self.invisibleRootItem()
        i = ii.rowCount()
        for j, it in enumerate((item_root, item)):
            ii.setChild(i, j, it)
            ii.setEditable(False)
        for j in range(self.columnCount()):
            it = ii.child(i, j)
            if it is None:
                it = QStandardItem()
                ii.setChild(i, j, it)
            it.setBackground(QColor("#002842"))
            it.setForeground(QColor("#F2F2F2"))
        return item_root

    def append_element_to_group(self, group_item, texts):
        j = group_item.rowCount()
        item_icon = QStandardItem()
        item_icon.setEditable(False)
        item_icon.setIcon(QIcon("game.png"))
        item_icon.setBackground(QColor("#0D1225"))
        group_item.setChild(j, 0, item_icon)
        for i, text in enumerate(texts):
            item = QStandardItem(text)
            item.setEditable(False)
            item.setBackground(QColor("#0D1225"))
            item.setForeground(QColor("#F2F2F2"))
            group_item.setChild(j, i+1, item)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        model = GroupModel(self)
        tree_view = GroupView(model)
        self.setCentralWidget(tree_view)

        for group, childrens in datas.items():
            group_item = model.add_group(group)
            for children in childrens:
                model.append_element_to_group(group_item, children)

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(720, 240)
    w.show()
    sys.exit(app.exec_())