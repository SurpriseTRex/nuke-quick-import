import nuke
import os
import re

from PySide import QtGui
from PySide import QtCore
from nukescripts import panels


class QuickReadBrowser(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        self.sequence_list = []

        self.nuke_file_path = "/".join(nuke.root()["name"].value().split("/")[:-1:])
        self.image_filters = ["*.jpg*",
                              "*.jpeg*",
                              "*.png*",
                              "*.tga*",
                              "*.exr*",
                              "*.tif*",
                              "*.tiff*",
                              "*.psd*",
                              "*.hdri*",
                              "*.hdr*",
                              "*.cin*",
                              "*.dpx*"]

        # Declare Models.
        self.dir_model = QtGui.QFileSystemModel()
        self.file_model = QtGui.QFileSystemModel()
        self.seq_model = QtGui.QStringListModel(self.sequence_list)

        # Declare widgets.
        self.dir_view = QtGui.QTreeView()
        self.file_view = QtGui.QListView()
        self.text_edit = QtGui.QLineEdit()
        self.import_button = QtGui.QPushButton("Open")
        self.up_button = QtGui.QPushButton("Up")
        self.seq_box = QtGui.QCheckBox("Image Sequence Mode")
        self.inst_label = QtGui.QLabel("Note: Image sequence names must contain no 0-9 digits except for those which "
                                       "dictate frame numbers.")

        # Define a central widget and its layout.
        self.center_widget = QtGui.QWidget()
        self.lg = QtGui.QGridLayout()

        self.build_models()
        self.add_widgets()
        self.setup_connections()
        self.build_ui()

    def build_ui(self):
        self.resize(600, 350)
        self.setWindowTitle("Nuke 'Quick-Read' Importer")

        # Assign central widget.
        self.setCentralWidget(self.center_widget)
        self.center_widget.setLayout(self.lg)

        self.inst_label.setWordWrap(True)
        self.import_button.setToolTip("Imports the selected file as a Read node.")
        self.seq_box.setToolTip("If this is checked, import any of the files in the sequence to import the "
                                "entire sequence.")

        self.text_edit.setText(self.nuke_file_path)

        self.show()

    def build_models(self):
        """ Sets up fileSystemModels and their links to views. """
        self.dir_model.setRootPath("")
        self.file_model.setRootPath("")

        # Filters.
        self.dir_model.setFilter(QtCore.QDir.AllDirs | QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)
        self.file_model.setFilter(self.file_model.filter() | QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        self.file_model.setNameFilters(self.image_filters)
        self.file_model.setNameFilterDisables(False)

        # Associate Views/Models.
        self.dir_view.setModel(self.dir_model)
        self.file_view.setModel(self.file_model)

        # Set initial indexes.
        self.dir_view.setCurrentIndex(self.dir_model.index(self.nuke_file_path))
        self.file_view.setRootIndex(self.file_model.index(self.nuke_file_path))

        # Hide all but Name column.
        self.dir_view.hideColumn(1)
        self.dir_view.hideColumn(2)
        self.dir_view.hideColumn(3)

    def add_widgets(self):
        # from row, from column, row span, column span.
        self.lg.addWidget(self.up_button, 0, 1, 1, 1)
        self.lg.addWidget(self.seq_box, 0, 2, 1, 1)
        self.lg.addWidget(self.dir_view, 1, 0, 1, 2)
        self.lg.addWidget(self.file_view, 1, 2, 1, 8)
        self.lg.addWidget(self.text_edit, 2, 0, 1, 8)
        self.lg.addWidget(self.import_button, 2, 8, 1, 2)
        self.lg.addWidget(self.inst_label, 3, 0, 2, 10)

    def setup_connections(self):
        """ Sets up input connections from different parts of the interface, to the appropriate methods. """
        self.dir_view.clicked.connect(self.update_from_tree_click)
        self.file_view.clicked.connect(self.update_from_list_click)
        self.file_view.doubleClicked.connect(self.import_to_read_node)
        self.text_edit.editingFinished.connect(self.update_from_text_entry)
        self.import_button.clicked.connect(self.import_to_read_node)
        self.up_button.clicked.connect(self.up_directory)
        self.seq_box.stateChanged.connect(self.sequence_toggle)

    def update_from_tree_click(self):
        if not self.seq_box.isChecked():
            self.text_edit.setText(self.dir_model.filePath(self.dir_view.selectedIndexes()[0]))
            self.file_view.setRootIndex(self.file_model.index(self.dir_model.filePath(self.dir_view.selectedIndexes()[0])))
        self.string_list_refresh()

    def update_from_list_click(self):
        if not self.seq_box.isChecked():
            self.text_edit.setText(self.file_model.filePath(self.file_view.selectedIndexes()[0]))
        self.string_list_refresh()

    def update_from_text_entry(self):
        # Updates both tree and list views with a typed file path.
        if not self.seq_box.isChecked():
            if self.text_edit.text():
                self.dir_view.setCurrentIndex(self.dir_model.index(self.text_edit.text()))
                self.file_view.setRootIndex(self.file_model.index(self.text_edit.text()))
                self.string_list_refresh()

    def up_directory(self):
        """ Provides a 'parent directory' button functionality. """
        parent_path = "/".join(self.file_model.filePath(self.file_view.rootIndex()).split("/")[:-1:])
        self.file_view.setRootIndex(self.file_model.index(parent_path))
        self.text_edit.setText(parent_path)
        self.dir_view.setCurrentIndex(self.dir_model.index(parent_path))
        self.string_list_refresh()

    def import_to_read_node(self):
        """ Handles final importing and directory navigation through the listView. """
        if self.seq_box.isChecked():
            file_path = self.text_edit.text()

            if re.search('\.....?', file_path):
                node = nuke.nodes.Read(file="/".join(file_path.split("/")[:-1:]) + "/" +
                                     self.seq_model.data(self.file_view.selectedIndexes()[0], 0))
            else:
                node = nuke.nodes.Read(file=file_path + "/" + self.seq_model.data(self.file_view.selectedIndexes()[0], 0))

            range_strip = re.compile('\D')

            first = range_strip.sub('', self.scan_folder_sequences()[1][0])
            last = range_strip.sub('', self.scan_folder_sequences()[1][-1])

            node.knob("first").setValue(int(first))
            node.knob("last").setValue(int(last))

        else:
            file_path = self.file_model.filePath(self.file_view.selectedIndexes()[0])

            if self.file_model.isDir(self.file_view.selectedIndexes()[0]):    # Handle opening a directory.
                # Converts from file_view index to dir_model index.
                dir_view_target_index = self.dir_model.index(self.dir_model.filePath(self.file_view.selectedIndexes()[0]))

                self.dir_view.setCurrentIndex(dir_view_target_index)
                self.file_view.setRootIndex(self.file_view.selectedIndexes()[0])

            else:  # Load single image.
                nuke.nodes.Read(file=file_path)

    def sequence_toggle(self):
        """ Handles the shift from showing files in folder to a list of Strings showing sequence names. """
        if self.seq_box.isChecked():
            self.string_list_refresh()
            # Change from a FileSystemModel to a StringListModel with names of sequences.
            self.file_view.setModel(self.seq_model)

        else:
            # Change back to the standard FileSystemModel.
            self.file_view.setModel(self.file_model)
            self.file_view.setRootIndex(
                self.file_model.index(
                self.dir_model.filePath(
                self.dir_view.selectedIndexes()[0])))


    def repl_regex(self, str):
        """ Functions as a find/replace for certain regex operations with unspecified frame number lengths. """
        return "#" * len(str.group())


    def get_folder_contents(self, file_path):
        return [f for f in os.listdir(file_path) if os.path.isfile(os.path.join(file_path, f))]


    def scan_folder_sequences(self):
        """ Returns a list of lists. filtered is a list of only the sequences in the specified path, first_last is
         a list of individual frames of the sequence. """
        file_path = self.dir_model.filePath(self.dir_view.selectedIndexes()[0])
        files_in_folder = self.get_folder_contents(file_path)
        filtered = []
        first_last = []

        for each in files_in_folder:
            if re.search('[0-9]{2,}', each):
                first_last.append(each)
                r = re.sub('[0-9]{2,}', self.repl_regex, each)

                if r not in filtered:
                    filtered.append(r)

        return [filtered, first_last]

    def string_list_refresh(self):
        """ Refresh the StringListModel. """
        sequence_list = self.scan_folder_sequences()[0]
        self.seq_model = QtGui.QStringListModel(sequence_list)


#window = QuickReadBrowser()
panels.registerWidgetAsPanel("QuickReadBrowser", "QuickRead Node Importer", "uk.co.seanjvfx.NukeQuickReadImporter")
