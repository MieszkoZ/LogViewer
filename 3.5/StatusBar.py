import os.path
from wx import StatusBar


class CustomStatusBar(StatusBar):
    def __init__(self, parent):
        StatusBar.__init__(self, parent, -1)
        self.SetFieldsCount(3)

    def set_file_name(self, fn):
        path, file_name = os.path.split(fn)
        self.SetStatusText(file_name, 0)

    def set_row_col(self, row, col):
        self.SetStatusText("%d,%d" % (row, col), 1)

    def set_dirty(self, dirty):
        if dirty:
            self.SetStatusText("...", 2)
        else:
            self.SetStatusText(" ", 2)

