import wx


class FileDropTarget(wx.FileDropTarget):

    def __init__(self, window):
        wx.FileDropTarget.__init__(self)
        self.window = window

    def OnDropFiles(self, x, y, file_names):
        self.window.open_file(file_names[0])

