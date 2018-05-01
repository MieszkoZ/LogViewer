import os
import re
import sys
import wx
import wx.adv
from wx.lib.wordwrap import wordwrap
from xml.etree import ElementTree
from StatusBar import *
from ConfigDlg import ConfigDlg
from utils import FileDropTarget
import traceback

CONFIG_FILE_NAME = 'config.xml'
CUSTOM_PATTERNS_LIMIT = 10
MAX_CUSTOM_BUTTONS = 10
DEFAULT_FONT_DESC = '0;-13;0;0;0;400;0;0;0;238;3;2;1;34;Verdana'
PUSHED_COLOUR = '#FFF64C'
CUSTOM_EXPRESSION_BUTTON_COLOR = '#AA1111'

DEFAULT_COLORS = [
    '#BB0000',
    '#00BB00',
    '#0000BB',
    '#BB00BB',
    '#00BBBB',
    '#BBBB00',
    '#BB3333',
    '#33BB33',
    '#3333BB',
    '#BBBBBB',
]


class CustomButtonRecord:
    def __init__(self, name='Empty', pattern='', tool_tip='', enabled=False):
        self.name = name
        self.pattern = pattern
        self.enabled = enabled
        self.button = None
        self.tool_tip = tool_tip
        self.pushed = False
        self.foreground_color = None
        self.background_color = None
        self.text_attr = None

        self.make_text_attr()

    def save(self, node):
        save_node = ElementTree.Element('custom_button')

        member_node = ElementTree.Element('name')
        member_node.text = self.name
        save_node.append(member_node)

        member_node = ElementTree.Element('pattern')
        member_node.text = self.pattern
        save_node.append(member_node)

        member_node = ElementTree.Element('enabled')
        member_node.text = str(self.enabled)
        save_node.append(member_node)

        member_node = ElementTree.Element('colors')

        if self.foreground_color is not None:
            color = ElementTree.Element('foreground')
            if isinstance(self.foreground_color, wx.Colour):
                color.text = self.foreground_color.GetAsString(wx.C2S_NAME | wx.C2S_HTML_SYNTAX)
            else:
                color.text = self.foreground_color
            member_node.append(color)

        if self.background_color is not None:
            color = ElementTree.Element('background')
            if isinstance(self.background_color, wx.Colour):
                color.text = self.background_color.GetAsString(wx.C2S_NAME | wx.C2S_HTML_SYNTAX)
            else:
                color.text = self.background_color
            member_node.append(color)

        save_node.append(member_node)

        node.append(save_node)

    def load(self, node):
        member_node = node.find('name')
        if member_node is not None:
            self.name = member_node.text

        member_node = node.find('pattern')
        if member_node is not None:
            self.pattern = member_node.text

        member_node = node.find('enabled')
        if member_node is not None:
            self.enabled = (member_node.text == 'True')

        member_node = node.find('colors')
        if member_node is not None:
            color_node = member_node.find('foreground')
            if color_node is not None:
                self.foreground_color = color_node.text

            color_node = member_node.find('background')
            if color_node is not None:
                self.background_color = color_node.text

        self.make_text_attr()

    def get_tooltip(self):
        if self.tool_tip:
            return self.tool_tip
        else:
            return 'Executes pattern "%s"' % self.pattern

    def set_foreground_color(self, color):
        self.foreground_color = color
        self.make_text_attr()

    def set_background_color(self, color):
        self.background_color = color
        self.make_text_attr()

    def make_text_attr(self):
        self.text_attr = wx.TextAttr(self.foreground_color, self.background_color)

    def push_button(self):
        self.make_text_attr()
        if self.foreground_color:
            self.button.SetForegroundColour(self.foreground_color)
        if self.background_color:
            self.button.SetBackgroundColour(self.background_color)


# ----------------------------------------------------------------------


class LogViewerFrame(wx.Frame):
    def __init__(self, parent, frame_id, title, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE):

        wx.Frame.__init__(self, parent, frame_id, title, pos, size, style)

        self.contents = []
        self.patterns = {}
        self.custom_patterns = []
        self.buttons = {}
        self.button_data = {
            'Reload': 'Reload currently viewed file',
            'Exclusion': 'Toggle exclusion or selection of matching lines',
            'Show only matching lines': 'Toggle displaying only matching lines',
            'Clear': 'Clear selected patterns.',
            'Execute pattern': 'Adds typed/selected pattern from list to current set',
        }
        self.special_styling = []
        self.exclusion = False
        self.show_only_matching = True
        self.show_line_numbers = False
        # elf.appendTabbedLines = True
        self.line_format_string = '%4d > %s'
        self.bt_exclusion = None
        self.custom_buttons = {}
        self.custom_buttons_ordered = []
        self.file_name = None
        self.main_menu = None
        self._textCtrl = None
        self.sb = None
        self.custom_toolbar_box = None
        self.main_box = None
        self.custom_pattern_ctrl = None
        self.append_tabbed_lines = None

        self.custom_expression_button = CustomButtonRecord()
        self.custom_expression_button.set_foreground_color(CUSTOM_EXPRESSION_BUTTON_COLOR)

        self.reload_bitmap = wx.Bitmap('reload.png')

        try:
            self.config_params = ElementTree.parse(CONFIG_FILE_NAME)

            node = self.config_params.find('show_line_numbers')
            if node is not None:
                self.show_line_numbers = (node.text == 'True')
            # ode = self.configParams.find( 'append_tabbed_lines' )
            # f node is not None:
            # self.appendTabbedLines = ( node.text == 'True' )
            node = self.config_params.find('line_numbers_format_string')
            if node is not None:
                self.line_format_string = node.text
            node = self.config_params.find('exclusion')
            if node is not None:
                self.exclusion = (node.text == 'True')
            node = self.config_params.find('only_matching')
            if node is not None:
                self.show_only_matching = (node.text == 'True')

        except IOError:
            root = ElementTree.Element('LogViewerConfig')
            self.config_params = ElementTree.ElementTree(root)
            last_file_node = ElementTree.Element('last_file')
            last_file_node.text = ''
            root.append(last_file_node)

            node = ElementTree.Element('show_line_numbers')
            node.text = str(self.show_line_numbers)
            root.append(node)

            # ode = ET.Element( 'append_tabbed_lines' )
            # ode.text = str( self.appendTabbedLines )
            # oot.append( node )

            node = ElementTree.Element('line_numbers_format_string')
            node.text = self.line_format_string
            root.append(node)

            node = ElementTree.Element('custom_buttons')
            bt_custom = CustomButtonRecord('Errors', r' Error:', enabled=True)
            bt_custom.set_foreground_color(DEFAULT_COLORS[0])
            bt_custom.save(node)

            bt_custom = CustomButtonRecord('Warnings', r' Warning:', enabled=True)
            bt_custom.set_foreground_color(DEFAULT_COLORS[1])
            bt_custom.save(node)

            bt_custom = CustomButtonRecord('Display', r' Display:', enabled=True)
            bt_custom.set_foreground_color(DEFAULT_COLORS[2])
            bt_custom.save(node)

            bt_custom = CustomButtonRecord('Verbose', r' Verbose:', enabled=True)
            bt_custom.set_foreground_color(DEFAULT_COLORS[3])
            bt_custom.save(node)

            for i in range(MAX_CUSTOM_BUTTONS - 4):
                bt_custom = CustomButtonRecord()
                bt_custom.set_foreground_color(DEFAULT_COLORS[4 + i])
                bt_custom.save(node)

            root.append(node)

        # splitter = wx.SplitterWindow(self, -1, style=wx.NO_3D|wx.SP_3D)
        window = wx.Panel(self, -1, style=wx.CLIP_CHILDREN)
        window.parent = self
        self.window = window
        # log = self.make_log_window(splitter)

        self.make_status_bar()
        self.make_editor_window(window)
        # self.setup_splitter(splitter, window, log)
        self.make_menus()
        self.make_main_window(window)
        self.register_event_handlers()

        window.Layout()

    # ------------- Init Misc

    def register_event_handlers(self):
        self.Bind(wx.EVT_CLOSE, self.on_close_window)

    def make_menus(self):
        self.main_menu = wx.MenuBar()
        self.add_menus(self.main_menu)
        self.SetMenuBar(self.main_menu)

    # ------------- Init Sub-windows

    def make_editor_window(self, win):
        style = wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.TE_DONTWRAP

        self._textCtrl = wx.TextCtrl(win, -1, style=style)
        dt = FileDropTarget(self)
        self._textCtrl.SetDropTarget(dt)

        font_node = self.config_params.find('font')
        if font_node is not None:
            font = wx.Font(font_node.text)
        else:
            font = wx.Font(DEFAULT_FONT_DESC)
        self._textCtrl.SetFont(font)

    def make_status_bar(self):
        self.sb = CustomStatusBar(self)
        self.SetStatusBar(self.sb)

    def make_log_window(self, container):
        log = wx.TextCtrl(container, -1,
                          style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        wx.Log.SetActiveTarget(wx.LogTextCtrl(log))
        wx.LogMessage('window handle: %s' % self.GetHandle())
        return log

    @staticmethod
    def setup_splitter(splitter, win, log):
        splitter.SplitHorizontally(win, log)
        splitter.SetSashPosition(360, True)
        splitter.SetMinimumPaneSize(40)

    def make_toolbar(self, win):
        toolbar_box = wx.BoxSizer(wx.HORIZONTAL)
        self.add_buttons(win, toolbar_box)
        return toolbar_box

    def make_custom_toolbar(self, win):
        self.custom_toolbar_box = wx.BoxSizer(wx.HORIZONTAL)
        self.setup_custom_buttons(win, self.custom_toolbar_box)
        return self.custom_toolbar_box

    def make_main_window(self, win):
        main_box = wx.BoxSizer(wx.VERTICAL)
        main_box.Add(self.make_toolbar(win))
        main_box.Add(self.make_custom_toolbar(win))
        border_width = 2
        main_box.Add(self._textCtrl, 1, wx.ALL | wx.GROW, border_width)
        win.SetSizer(main_box)
        win.SetAutoLayout(True)
        self.main_box = main_box

    # -------------- Init Menus

    # override this to add more menus
    def add_menus(self, menu):
        self.add_file_menu(menu)
        self.add_view_menu(menu)
        self.add_help_menu(menu)

    def add_menu_item(self, menu, item_text, item_description, item_handler):
        menu_id = wx.NewId()
        menu.Append(menu_id, item_text, item_description)
        self.Bind(wx.EVT_MENU, item_handler, id=menu_id)
        return menu_id

    def add_file_menu(self, menu):
        file_menu = wx.Menu()
        self.add_menu_item(file_menu, 'Reload', 'Reload current file', self.on_reload)
        self.add_menu_item(file_menu, 'Open File', 'Open File', self.on_open_file)
        # self.add_menu_item( file_menu, '&save File\tCtrl-S', 'save File', self.on_save_file )
        self.add_menu_item(file_menu, 'save View As', 'save File As', self.on_save_file_as)
        self.add_menu_item(file_menu, 'Exit', 'Exit', self.on_file_exit)
        menu.Append(file_menu, 'File')

    def add_view_menu(self, menu):
        view_menu = wx.Menu()
        self.add_menu_item(view_menu, 'Select font', 'View area font selection', self.on_set_font)
        self.add_menu_item(view_menu, 'Buttons Config', 'Configure custom buttons', self.on_configure_custom_buttons)
        view_menu.AppendSeparator()

        menu_id = wx.NewId()
        view_menu.Append(menu_id, 'Show line numbers', 'Toggle showing line numbers', wx.ITEM_CHECK)
        view_menu.Check(menu_id, self.show_line_numbers)
        self.Bind(wx.EVT_MENU, self.on_toggle_line_numbers, id=menu_id)

        menu.Append(view_menu, 'View')

    def add_help_menu(self, menu):
        help_menu = wx.Menu()
        self.add_menu_item(help_menu, 'About', 'About the program', self.on_help_about)
        menu.Append(help_menu, 'Help')

    # ---------------- Init Buttons

    def set_tooltip(self, button, data_key):
        if data_key in self.button_data:
            button.SetToolTip(self.button_data[data_key])

    def new_button(self, window, container, name, pos, size, handler):
        button_id = wx.NewId()
        if pos is None or size is None:
            button = wx.Button(window, button_id, name)
        else:
            button = wx.Button(window, button_id, name, pos, size)

        container.Add(button, 0, 0)
        self.Bind(wx.EVT_BUTTON, handler, id=button_id)

        self.set_tooltip(button, name)

        return button_id, button

    def new_custom_button(self, window, container, name, pos, size, handler):
        button_id = wx.NewId()
        if pos is None or size is None:
            button = wx.Button(window, button_id, name)
        else:
            button = wx.Button(window, button_id, name, pos, size)

        container.Add(button, 0, 0)
        self.Bind(wx.EVT_BUTTON, handler, id=button_id)
        return button_id, button

    # override this to make more buttons
    def add_buttons(self, window, container):
        button_pos = None
        button_size = None

        button_id = wx.NewId()
        button = wx.BitmapButton(window, button_id, self.reload_bitmap)
        self.set_tooltip(button, 'Reload')
        # wx.Button( window, button_id,  )
        container.Add(button, 0, 0)
        self.Bind(wx.EVT_BUTTON, self.on_reload, id=button_id)

        self.new_button(window, container, 'Clear', button_pos, button_size, self.on_clear)

        button_id = wx.NewId()
        self.custom_pattern_ctrl = wx.ComboBox(window, button_id, style=wx.CB_DROPDOWN)
        self.custom_pattern_ctrl.SetInitialSize((170, 25))
        container.Add(self.custom_pattern_ctrl, 0, 0)
        self.custom_pattern_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_custom_pattern)
        _, button = self.new_button(window, container, 'Execute pattern', button_pos
                                    , button_size, self.on_custom_pattern)
        button.SetForegroundColour(CUSTOM_EXPRESSION_BUTTON_COLOR)

        container.Add((6, 10))

        button_id = wx.NewId()
        self.bt_exclusion = wx.CheckBox(window, button_id, 'Exclusion')
        self.bt_exclusion.SetMinSize((-1, 23))
        self.set_tooltip(self.bt_exclusion, 'Exclusion')
        self.bt_exclusion.SetValue(self.exclusion)
        container.Add(self.bt_exclusion, 0, 0)
        self.Bind(wx.EVT_CHECKBOX, self.on_exclusion, id=button_id)

        button_id = wx.NewId()
        button = wx.CheckBox(window, button_id, 'Show only matching lines')
        button.SetMinSize((-1, 23))
        self.set_tooltip(button, 'Show only matching lines')
        button.SetValue(self.show_only_matching)
        container.Add(button, 0, 0)
        self.Bind(wx.EVT_CHECKBOX, self.on_show_only_matching, id=button_id)

        # loading previously saved custom patterns
        custom_pattern_node = self.config_params.find('custom_patterns')
        if custom_pattern_node is not None:
            items = []
            for child in custom_pattern_node:
                if child.text is not None:
                    items.append(child.text)

            if len(items) > 0:
                self.custom_patterns.extend(items)
                self.custom_pattern_ctrl.AppendItems(items)

    def setup_custom_buttons(self, window, container):

        if len(self.custom_buttons) == 0:
            custom_buttons = self.config_params.find('custom_buttons')
            for childNode in custom_buttons:
                custom_button = CustomButtonRecord()
                custom_button.load(childNode)

                button_id = self.create_custom_button_from_desc(window, container, custom_button)
                self.custom_buttons[str(button_id)] = custom_button
                self.custom_buttons_ordered.append(custom_button)
        else:
            for custom_button in self.custom_buttons.values():
                self.create_custom_button_from_desc(window, container, custom_button)

    def create_custom_button_from_desc(self, window, container, custom_button):
        button_id = wx.NewId()
        custom_button.button = wx.Button(window, button_id, custom_button.name)
        custom_button.button.SetToolTip(custom_button.get_tooltip())
        self.Bind(wx.EVT_BUTTON, self.on_custom_button, id=button_id)

        if not custom_button.enabled:
            custom_button.button.Enable(False)

        container.Add(custom_button.button, 0, 0)
        return button_id

    # -------------- Init Dialogs

    def message_dialog(self, text, title):
        message_dialog = wx.MessageDialog(self, text, title, wx.OK | wx.ICON_INFORMATION)
        message_dialog.ShowModal()
        message_dialog.Destroy()

    def ok_cancel_dialog(self, text, title):
        dialog = wx.MessageDialog(self, text, title, wx.OK | wx.CANCEL | wx.ICON_INFORMATION)
        result = dialog.ShowModal()
        dialog.Destroy()
        if result == wx.ID_OK:
            return True
        else:
            return False

    def select_file_dialog(self, default_dir=None, default_file=None, wild_card=None):
        if default_dir is None:
            default_dir = '.'
        if default_file is None:
            default_file = ''
        if wild_card is None:
            wild_card = '*.*'
        file_name = None
        file_dialog = wx.FileDialog(self, 'Choose a file', default_dir, default_file, wild_card,
                                    wx.FD_OPEN | wx.FD_MULTIPLE)
        result = file_dialog.ShowModal()
        if result == wx.ID_OK:
            file_name = file_dialog.GetPath()
        # wx.LogMessage('You selected: %s\n' % file_name)
        file_dialog.Destroy()
        return file_name

    def open_file_error(self, file_name):
        # wx.LogMessage( 'Open file error.' )
        self.message_dialog('Error opening file "%s"!' % file_name, 'Error')

    def save_file_error(self, file_name):
        wx.LogMessage('save file error.')
        self.message_dialog('Error saving file "%s"!' % file_name, 'Error')

    # ---------------- Utility functions

    def get_current_dir(self):
        if self.file_name is not None:
            return os.path.split(self.file_name)[0]
        return '.'

    def get_file_name(self):
        if self.file_name is not None:
            return os.path.split(self.file_name)[1]
        return ''

    def new_file(self):
        self._textCtrl.SetValue('')
        self.file_name = None
        self.sb.set_file_name('')

    def save_file(self, file_name):
        try:
            # contents = string.join(self._textCtrl.GetValue(), '\n')
            contents = self._textCtrl.GetValue()
            f = open(file_name, 'w')
            f.write(contents)
            f.close()
            # self.edl.UnTouchBuffer()
            self.sb.set_file_name(file_name)
            return True
        except Exception:
            return False

    def open_file(self, file_name):
        wx.BeginBusyCursor()
        try:
            f = open(file_name, 'r')
            contents = f.readlines()
            f.close()
            contents = [line.strip() for line in contents]
            self.contents = contents
            if len(contents) == 0:
                text = ''
            elif self.show_line_numbers:
                contents_with_numbers = []
                line_number = 0
                for line in contents:
                    line_number = line_number + 1
                    contents_with_numbers.append(self.line_format_string % (line_number, line))
                text = '\n'.join(contents_with_numbers)
            else:
                text = '\n'.join(contents)

            self._textCtrl.SetValue(text)
            self.file_name = file_name
            self.sb.set_file_name(file_name)

            self.clear_parsing()
            wx.EndBusyCursor()
            return True
        except Exception:
            traceback.print_exc()

        wx.EndBusyCursor()
        return False

    def clear_parsing(self):
        self.patterns = {}
        self.special_styling = []
        self._textCtrl.SetDefaultStyle(self._textCtrl.GetDefaultStyle())

        for customButton in self.custom_buttons_ordered:
            customButton.button.SetForegroundColour(wx.NullColour)
            customButton.button.SetBackgroundColour(wx.NullColour)

    # ---------------- Event handlers

    @staticmethod
    def save_value(root, name, value):
        node = ElementTree.Element(name)
        if isinstance(value, str):
            node.text = value
        else:
            node.text = str(value)
        root.append(node)

    def on_close_window(self, event):
        root = ElementTree.Element('LogViewerConfig')
        self.config_params = ElementTree.ElementTree(root)

        node = ElementTree.Element('font')
        font = self._textCtrl.GetFont()
        node.text = font.GetNativeFontInfoDesc()
        root.append(node)

        LogViewerFrame.save_value(root, 'show_line_numbers', self.show_line_numbers)
        # elf.save_value( root, 'append_tabbed_lines', self.appendTabbedLines )
        LogViewerFrame.save_value(root, 'line_numbers_format_string', self.line_format_string)
        LogViewerFrame.save_value(root, 'last_file', self.file_name)
        LogViewerFrame.save_value(root, 'exclusion', self.exclusion)
        LogViewerFrame.save_value(root, 'only_matching', self.show_only_matching)

        node = ElementTree.Element('custom_buttons')
        for i in range(len(node) - 1, -1, -1):
            del node[i]
        for customButton in self.custom_buttons_ordered:
            customButton.save(node)
        root.append(node)

        # saving last 10 patterns
        custom_pattern_node = ElementTree.Element('custom_patterns')
        root.append(custom_pattern_node)

        items = self.custom_pattern_ctrl.GetItems()
        i = 0
        for item in items:
            node = ElementTree.Element('pattern')
            node.text = item
            custom_pattern_node.append(node)
            i = i + 1
            if i >= CUSTOM_PATTERNS_LIMIT:
                break

        # self.edl.on_close_window(event)
        self.config_params.write(CONFIG_FILE_NAME)
        self.Destroy()

    def on_reload(self, event):
        if self.file_name is None:
            return

        if not self.open_file(self.file_name):
            self.open_file_error(self.file_name)


    def on_open_file(self, event):
        file_name = self.select_file_dialog(self.get_current_dir())
        if file_name is not None:
            if not self.open_file(file_name):
                self.open_file_error(file_name)
        self._textCtrl.SetFocus()

    def on_save_file(self, event):
        if self.file_name is None:
            return self.on_save_file_as(event)
        wx.LogMessage('Saving %s...' % self.file_name)
        if self.save_file(self.file_name) is not True:
            self.save_file_error(self.file_name)
        self._textCtrl.SetFocus()

    def on_save_file_as(self, event):
        file_name = self.select_file_dialog(self.get_current_dir(), self.get_file_name())
        if file_name is not None:
            # self.file_name = file_name
            wx.LogMessage('Saving %s...' % file_name)
            if self.save_file(file_name) is not True:
                self.save_file_error(file_name)
        self._textCtrl.SetFocus()

    def on_file_exit(self, event):
        """if self.edl.BufferWasTouched():
            if not self.ok_cancel_dialog("Exit program - abandon changes?", "Exit"):
                return
        """
        self.on_close_window(event)

    def on_help_about(self, event):
        # First we create and fill the info object
        info = wx.adv.AboutDialogInfo()
        info.Name = 'Log File Viewer'
        info.Version = '0.8.1'
        info.Description = wordwrap(
            '\nSimple tool for processing text-based log files.',
            350, wx.ClientDC(self))
        info.Copyright = 'Copyright 2008-2018'
        info.Developers = ['Mieszko Zielinski (MieszkoZ @github)']


        # Then we call wx.AboutBox giving it that info object
        wx.adv.AboutBox(info)

    def on_set_font(self, event):
        dlg = wx.FontDialog(self, wx.FontData())
        dlg.GetFontData().SetInitialFont(self._textCtrl.GetFont())
        if dlg.ShowModal() == wx.ID_OK:
            font = dlg.GetFontData().GetChosenFont()
            self._textCtrl.SetFont(font)

        dlg.Destroy()

    def on_configure_custom_buttons(self, event):
        dlg = ConfigDlg(self, self.custom_buttons_ordered)
        if dlg.ShowModal() == wx.ID_OK:
            for custom_button in self.custom_buttons.values():
                custom_button.button.SetLabel(custom_button.name)
                custom_button.button.Enable(custom_button.enabled)
                # custom_button.button.Show( custom_button.enabled )
                custom_button.button.SetToolTip(custom_button.get_tooltip())

        dlg.Destroy()

    def Show(self, show=True):
        wx.Frame.Show(self, show)
        self._textCtrl.SetFocus()

    # ------------- Startup stuff

    def load_initial_file(self, file_name):
        if file_name is None:
            last_file_node = self.config_params.find('last_file')
            file_name = last_file_node.text
            if file_name is None or len(file_name) == 0:
                return

        if self.open_file(file_name) is False:
            self.open_file_error(file_name)

    # ------------- Parsing stuff

    def parse_content(self):

        wx.BeginBusyCursor()

        self.special_styling = []
        joined = ''

        if len(self.patterns) > 0:
            lines = self.contents
            line_number = 0
            parsed_lines = []

            if not self.exclusion:
                length = 0
                matched = False

                for line in lines:
                    line_number = line_number + 1
                    for patternName in self.patterns:
                        pattern, button = self.patterns[patternName]
                        if re.search(pattern, line):
                            if self.show_line_numbers:
                                line = self.line_format_string % (line_number, line)
                            parsed_lines.append(line)
                            end = length + len(line) + 1
                            self.special_styling.append((length, end, button.text_attr))
                            length = end
                            matched = True
                            break

                    if not self.show_only_matching and not matched:
                        if self.show_line_numbers:
                            line = self.line_format_string % (line_number, line)
                        length = length + len(line) + 1
                        parsed_lines.append(line)

                    matched = False

            else:  # exclusion == True
                for line in lines:
                    line_number = line_number + 1
                    matched = False
                    for patternName in self.patterns:
                        pattern, button = self.patterns[patternName]
                        if re.search(pattern, line):
                            matched = True
                            break
                    if not matched:
                        if self.show_line_numbers:
                            line = self.line_format_string % (line_number, line)
                        parsed_lines.append(line)

            if len(parsed_lines) > 0:
                joined = '\n'.join(parsed_lines)

        elif len(self.contents) > 0:
            if self.show_line_numbers:
                contents_with_numbers = []
                line_number = 0
                for line in self.contents:
                    line_number = line_number + 1
                    contents_with_numbers.append(self.line_format_string % (line_number, line))
                joined = '\n'.join(contents_with_numbers)
            else:
                joined = '\n'.join(self.contents)

        self._textCtrl.SetValue(joined)
        if len(self.special_styling) > 0:
            for start, end, text_attr in self.special_styling:
                self._textCtrl.SetStyle(start, end, text_attr)
        else:
            self._textCtrl.SetDefaultStyle(self._textCtrl.GetDefaultStyle())

        wx.EndBusyCursor()

    def on_exclusion(self, event):
        self.exclusion = (self.bt_exclusion.GetValue() != 0)
        self.parse_content()

    def on_show_only_matching(self, event):
        self.show_only_matching = (event.EventObject.GetValue() != 0)
        self.parse_content()

    def on_clear(self, event):
        self.clear_parsing()
        self.parse_content()

    def xor_pattern_to_list(self, name, pattern, button=None):
        """ returns True if pattern was added, False otherwise"""
        is_added = False
        if name in self.patterns:
            del self.patterns[name]
        elif pattern is not None and len(pattern) > 0:
            self.patterns[name] = (re.compile(pattern), button)
            is_added = True

        self.parse_content()

        return is_added

    def on_custom_pattern(self, event):
        pattern = self.custom_pattern_ctrl.GetValue()
        # rawPat = raw( self.customPatternCtrl.GetValue() )
        if pattern not in self.custom_patterns:
            self.custom_pattern_ctrl.Insert(pattern, 0)
            self.custom_patterns.append(pattern)

        # at this moment it's possible to have several instances of the same
        # pattern used. It doesn't influence parsing results, but it does influence
        # efficiency.
        self.patterns[pattern] = (re.compile(pattern), self.custom_expression_button)

        self.parse_content()

    def on_custom_button(self, event):
        key = str(event.Id)
        if key in self.custom_buttons:
            custom_button = self.custom_buttons[key]

            custom_button.pushed = self.xor_pattern_to_list(custom_button.name, custom_button.pattern, custom_button)
            if custom_button.pushed:
                custom_button.push_button()
            else:
                custom_button.button.SetBackgroundColour(wx.NullColour)
                custom_button.button.SetForegroundColour(wx.NullColour)

    def on_toggle_line_numbers(self, event):
        self.show_line_numbers = (event.Selection != 0)
        self.parse_content()

    def on_toggle_append_tabbed_lines(self, event):
        self.append_tabbed_lines = (event.Selection != 0)
        self.parse_content()


# -------------- Application Launcher utility class

class LogViewerLauncher:

    @staticmethod
    def make_app_frame():
        return LogViewerFrame(None, -1, 'LogViewer', size=(640, 480),
                              style=wx.DEFAULT_FRAME_STYLE | wx.NO_FULL_REPAINT_ON_RESIZE)

    @staticmethod
    def get_argv_filename():
        if len(sys.argv) > 1:
            return sys.argv[1]
        else:
            return None

    @staticmethod
    def main():
        app = wx.App()
        win = LogViewerLauncher.make_app_frame()
        win.SetSize((758, 500))
        win.SetSizeHints(minSize=(758, 150))
        win.Show(True)
        win.load_initial_file(LogViewerLauncher.get_argv_filename())
        app.MainLoop()


# -------------- Main program


if __name__ == '__main__':
    LogViewerLauncher.main()
