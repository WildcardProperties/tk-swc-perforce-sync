
import sys
sys.path.append(r'C:\Python\Python39\Lib\site-packages')
from PyQt5.QtWidgets import QApplication, QTreeView, QWidget, QVBoxLayout, QMainWindow
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt

datas = {
    "Category 1": [
        ("New Game 2", "Playnite2", "", "", "A", "Played", ""),
        ("New Game 3", "Playnite3", "", "", "B", "Not Played", ""),
    ],
    "Category 2": [
        ("New Game", "Playnite1", "", "", "C", "Not Plated", ""),
    ]
}

app = QApplication(sys.argv)
window = QMainWindow()
central_widget = QWidget()
layout = QVBoxLayout(central_widget)

tree_view = QTreeView()
layout.addWidget(tree_view)

model = QStandardItemModel()
model.setHorizontalHeaderLabels(["", "Name", "Game", "Column3", "Column4", "Category", "Status", "Column7"])

# Add items to the model
for category, items in datas.items():
    category_item = QStandardItem(category)
    model.appendRow(category_item)
    for item_data in items:
        item = [QStandardItem(data) for data in item_data]
        category_item.appendRow(item)

tree_view.setModel(model)
tree_view.header().setSectionResizeMode(0)  # Allow column resizing
tree_view.setSortingEnabled(True)  # Enable sorting by columns

window.setCentralWidget(central_widget)
window.show()
sys.exit(app.exec_())


