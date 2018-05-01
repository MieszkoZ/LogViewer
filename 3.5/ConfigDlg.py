import wx


class ConfigDlg(wx.Dialog):

    def __init__(
            self, parent, data, title='Configure custom buttons', size=wx.DefaultSize, pos=wx.DefaultPosition,
            style=wx.DEFAULT_DIALOG_STYLE,
            use_metal=True):

        widget_id = wx.NewId()

        self.data = data

        wx.Dialog.__init__(self)
        self.SetExtraStyle(wx.FRAME_EX_CONTEXTHELP)
        self.Create(parent, widget_id, title, pos, size, style)

        # This extra style can be set after the UI object has been created.
        if 'wxMac' in wx.PlatformInfo and use_metal:
            self.SetExtraStyle(wx.DIALOG_EX_METAL)

        # Now continue with the normal construction of the dialog
        # contents
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.sets = [wx.BoxSizer(wx.HORIZONTAL) for _ in range(len(data))]

        self.foregrounds = {}
        self.backgrounds = {}

        index = 0
        for box in self.sets:
            button_data = data[index]

            button = self.add_control(box, wx.CheckBox, (-1, 20))
            button.SetValue(button_data.enabled)

            button = self.add_control(box, wx.TextCtrl, (100, -1))
            button.SetValue(button_data.name)

            button = self.add_control(box, wx.TextCtrl, (200, -1))
            if button_data.pattern is not None:
                button.SetValue(button_data.pattern)

            button = self.add_control(box, wx.Button, (-1, -1))
            button.SetLabel('Foreground')
            if button_data.foregroundColor is not None:
                button.SetBackgroundColour(button_data.foregroundColor)
            self.Bind(wx.EVT_BUTTON, self.on_color_button, id=button.Id)
            self.foregrounds[str(button.Id)] = button_data

            button = self.add_control(box, wx.Button, (-1, -1))
            button.SetLabel('Background')
            if button_data.backgroundColor is not None:
                button.SetBackgroundColour(button_data.backgroundColor)
            self.Bind(wx.EVT_BUTTON, self.on_color_button, id=button.Id)
            self.backgrounds[str(button.Id)] = button_data

            sizer.Add(box, 0, wx.ALIGN_CENTRE | wx.ALL | wx.EXPAND, 2)

            index = index + 1

        button_sizer = wx.StdDialogButtonSizer()

        if wx.Platform != '__WXMSW__':
            btn = wx.ContextHelpButton(self)
            button_sizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        self.Bind(wx.EVT_BUTTON, self.on_ok, id=wx.ID_OK)
        button_sizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        button_sizer.AddButton(btn)
        button_sizer.Realize()

        sizer.Add(button_sizer, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

    def add_control(self, container, control_type, min_size):
        button_id = wx.NewId()
        button = control_type(self, button_id)
        button.SetMinSize(min_size)

        container.Add(button, 0, 0)

        return button

    def on_ok(self, event):
        i = 0
        for box in self.sets:
            items = box.GetChildren()
            custom_button = self.data[i]
            custom_button.enabled = items[0].Window.GetValue()
            custom_button.name = items[1].Window.GetValue()
            custom_button.pattern = items[2].Window.GetValue()
            i = i + 1

        self.Unbind(wx.EVT_BUTTON, id=wx.ID_OK)
        wx.Dialog.ProcessEvent(self, event)

    def on_color_button(self, event):
        dlg = wx.ColourDialog(self)

        # Ensure the full colour dialog is displayed,
        # not the abbreviated version.
        dlg.GetColourData().SetChooseFull(True)

        custom_button = None
        str_id = str(event.Id)
        if str_id in self.foregrounds:
            custom_button = self.foregrounds[str_id]
            dlg.GetColourData().SetColour(custom_button.foregroundColor)
        elif str_id in self.backgrounds:
            custom_button = self.backgrounds[str_id]
            dlg.GetColourData().SetColour(custom_button.backgroundColor)

        if dlg.ShowModal() == wx.ID_OK:

            # If the user selected OK, then the dialog's wx.ColourData will
            # contain valid information. Fetch the data ...
            data = dlg.GetColourData()

            # ... then do something with it. The actual colour data will be
            # returned as a three-tuple (r, g, b) in this particular case.
            if str_id in self.foregrounds:
                custom_button.SetForegroundColor(data.GetColour().GetAsString())
                event.EventObject.SetBackgroundColour(custom_button.foregroundColor)
            elif str_id in self.backgrounds:
                custom_button.SetBackgroundColor(data.GetColour().GetAsString())
                event.EventObject.SetBackgroundColour(custom_button.backgroundColor)

        # Once the dialog is destroyed, Mr. wx.ColourData is no longer your
        # friend. Don't use it again!
        dlg.Destroy()
