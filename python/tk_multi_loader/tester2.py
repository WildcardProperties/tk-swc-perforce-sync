from PyQt5 import QtCore, QtWidgets

class GroupDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        group_value = index.data(QtWidgets.Qt.UserRole)
        if group_value:
            painter.drawText(option.rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, group_value)
        else:
            super(GroupDelegate, self).paint(painter, option, index)

def group_by_user(self):
    self.ui.column_view.setItemDelegateForColumn(7, GroupDelegate())  # Set the delegate for the "User" column
    self.ui.column_view.sortByColumn(7, QtCore.Qt.AscendingOrder)  # Sort by the "User" column
    self.assign_group_values(7)  # Assign unique group values to each item in the "User" column

def group_by_folder(self):
    self.ui.column_view.setItemDelegateForColumn(0, GroupDelegate())  # Set the delegate for the "Folder" column
    self.ui.column_view.sortByColumn(0, QtCore.Qt.AscendingOrder)  # Sort by the "Folder" column
    self.assign_group_values(0)  # Assign unique group values to each item in the "Folder" column

def assign_group_values(self, column):
    # Iterate through the items in the specified column and assign unique group values
    model = self.column_view_model
    prev_value = None
    group_value = None
    for row in range(model.rowCount()):
        index = model.index(row, column)
        value = index.data()
        if value != prev_value:
            group_value = value
        model.setData(index, group_value, QtCore.Qt.UserRole)
        prev_value = value
