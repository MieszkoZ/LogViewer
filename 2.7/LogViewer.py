import  os
import  re
import  string
import  sys

import  wx

from wx.lib.wordwrap import wordwrap
import wx.lib.pydocview as pydocview

from xml.etree import ElementTree as ET

from StatusBar import *
from ConfigDlg import ConfigDlg
from utils import FileDropTarget

CONFIG_FILE_NAME = 'config.xml'
CUSTOM_PATTERNS_LIMIT = 10
MAX_CUSTOM_BUTTONS = 10
DEFAULT_FONT_DESC = "0;-13;0;0;0;400;0;0;0;238;3;2;1;34;Verdana"
PUSHED_COLOUR = "#FFF64C"
CUSTOM_EXPRESSION_BUTTON_COLOR = "#AA1111"

DEFAULT_COLORS = [
	"#BB0000",
	"#00BB00",
	"#0000BB",
	"#BB00BB",
	"#00BBBB",
	"#BBBB00",
	"#BB3333",
	"#33BB33",
	"#3333BB",
	"#BBBBBB",

]


class CustomButtonRecord:
	def __init__( self, name = "Empty", pattern = "", toolTip = "", enabled = False ):
		self.name = name
		self.pattern = pattern
		self.enabled = enabled
		self.button = None
		self.toolTip = toolTip
		self.pushed = False
		self.foregroundColor = None
		self.backgroundColor = None

		self.MakeTextAttr()

	def Save( self, node ):
		saveNode = ET.Element( 'custom_button' )

		memberNode = ET.Element( 'name' )
		memberNode.text = self.name
		saveNode.append( memberNode )

		memberNode = ET.Element( 'pattern' )
		memberNode.text = self.pattern
		saveNode.append( memberNode )

		memberNode = ET.Element( 'enabled' )
		memberNode.text = str( self.enabled )
		saveNode.append( memberNode )

		memberNode = ET.Element( 'colors' )

		if self.foregroundColor is not None:
			color = ET.Element( 'foreground' )
			if isinstance( self.foregroundColor, wx.Colour ):
				color.text = self.foregroundColor.GetAsString(wx.C2S_NAME|wx.C2S_HTML_SYNTAX)
			else:
				color.text = self.foregroundColor
			memberNode.append( color )

		if self.backgroundColor is not None:
			color = ET.Element( 'background' )
			if isinstance( self.backgroundColor, wx.Colour ):
				color.text = self.backgroundColor.GetAsString(wx.C2S_NAME|wx.C2S_HTML_SYNTAX)
			else:
				color.text = self.backgroundColor
			memberNode.append( color )

		saveNode.append( memberNode )

		node.append( saveNode )

	def Load( self, node ):
		memberNode = node.find( 'name' )
		if memberNode is not None:
			self.name = memberNode.text

		memberNode = node.find( 'pattern' )
		if memberNode is not None:
			self.pattern = memberNode.text

		memberNode = node.find( 'enabled' )
		if memberNode is not None:
			self.enabled = ( memberNode.text == "True" )

		memberNode = node.find( 'colors' )
		if memberNode is not None:
			colorNode = memberNode.find( 'foreground' )
			if colorNode is not None:
				self.foregroundColor = colorNode.text

			colorNode = memberNode.find( 'background' )
			if colorNode is not None:
				self.backgroundColor = colorNode.text

		self.MakeTextAttr()

	def GetToolTip( self ):
		if self.toolTip:
			return self.toolTip
		else:
			return "Executes pattern '%s'" % self.pattern

	def SetForegroundColor(self, color):
		self.foregroundColor = color
		self.MakeTextAttr()

	def SetBackgroundColor(self, color):
		self.backgroundColor = color
		self.MakeTextAttr()

	def MakeTextAttr( self ):
		self.textAttr = wx.TextAttr( self.foregroundColor, self.backgroundColor )

	def PushButton(self):
		self.MakeTextAttr()
		if self.foregroundColor:
			self.button.SetForegroundColour( self.foregroundColor )
		if self.backgroundColor:
			self.button.SetBackgroundColour( self.backgroundColor )

##---------------------------------------------------------------------

def chomp( line ):
	line = string.split( line, '\n' )[0]
	return string.split( line, '\r' )[0]

##---------------------------------------------------------------------

class OutlinerPanel( wx.Panel ):

	def Close( self, event ):
		self.parent.Close()
		wx.Panel.Close( self )

##----------------------------------------------------------------------


class LogViewerFrame( wx.Frame ):
	def __init__( self, parent, ID, title, pos=wx.DefaultPosition,
				 size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE ):

		wx.Frame.__init__( self, parent, ID, title, pos, size, style )

		self.contents = []
		self.patterns = {}
		self.customPatterns = []
		self.buttons = {}
		self.buttonData = {
			'Reload' : 'Reload currently viewed file',
			'Exclusion' : 'Toggle exclusion or selection of matching lines',
			'Show only matching lines' : 'Toggle displaying only matching lines',
			'Clear' : 'Clear selected patterns.',
			'Execute pattern' : 'Adds typed/selected pattern from list to current set',
		}
		self.exclusion = False
		self.showOnlyMatching = True
		self.showLineNumbers = False
		#elf.appendTabbedLines = True
		self.lineFormatString = "%4d > %s"
		self.btBxclution = None
		self.customButtons = {}
		self.customButtonsOrdered = []
		self.customExpresionButton = CustomButtonRecord()

		self.customExpresionButton.SetForegroundColor( CUSTOM_EXPRESSION_BUTTON_COLOR )

		self.reloadBitmap = wx.Bitmap( 'reload.png' )

		try:
			self.configParams = ET.parse( CONFIG_FILE_NAME )

			node = self.configParams.find( 'show_line_numbers' )
			if node is not None:
				self.showLineNumbers = ( node.text == "True" )
			#ode = self.configParams.find( 'append_tabbed_lines' )
			#f node is not None:
			#self.appendTabbedLines = ( node.text == "True" )
			node = self.configParams.find( 'line_numebers_format_string' )
			if node is not None:
				self.lineFormatString = node.text
			node = self.configParams.find( 'exclusion' )
			if node is not None:
				self.exclusion = (node.text == 'True')
			node = self.configParams.find( 'only_matching' )
			if node is not None:
				self.showOnlyMatching = (node.text == 'True')

		except IOError:
			root = ET.Element( 'LogViewerConfig' )
			self.configParams = ET.ElementTree( root )
			lastFileNode = ET.Element( 'last_file' )
			lastFileNode.text = ""
			root.append( lastFileNode )

			node = ET.Element( 'show_line_numbers' )
			node.text = str( self.showLineNumbers )
			root.append( node )

			#ode = ET.Element( 'append_tabbed_lines' )
			#ode.text = str( self.appendTabbedLines )
			#oot.append( node )

			node = ET.Element( 'line_numebers_format_string' )
			node.text = self.lineFormatString
			root.append( node )

			node = ET.Element( 'custom_buttons' )
			btCustom = CustomButtonRecord( 'Errors', r' Error:', None, True )
			btCustom.SetForegroundColor( DEFAULT_COLORS[0] )
			btCustom.Save( node )

			btCustom = CustomButtonRecord( 'Warnings', r' Warning:', None, True )
			btCustom.SetForegroundColor( DEFAULT_COLORS[1] )
			btCustom.Save( node )

			btCustom = CustomButtonRecord( 'Display', r' Display:', None, True )
			btCustom.SetForegroundColor( DEFAULT_COLORS[2] )
			btCustom.Save( node )
			
			btCustom = CustomButtonRecord( 'Verbose', r' Verbose:', None, True )
			btCustom.SetForegroundColor( DEFAULT_COLORS[3] )
			btCustom.Save( node )

			for i in range( MAX_CUSTOM_BUTTONS - 4 ):
				btCustom = CustomButtonRecord()
				btCustom.SetForegroundColor( DEFAULT_COLORS[4+i] )
				btCustom.Save( node )

			root.append( node )


		#splitter = wx.SplitterWindow(self, -1, style=wx.NO_3D|wx.SP_3D)
		win = wx.Panel( self, -1, style=wx.CLIP_CHILDREN )
		win.parent = self
		self.win = win
		#log = self.MakeLogWindow(splitter)

		self.MakeStatusbar()
		self.MakeEditorWindow( win )
		#self.SetUpSplitter(splitter, win, log)
		self.MakeMenus()
		self.MakeMainWindow( win )
		self.RegisterEventHandlers()
		self.InitVariables()

		win.Layout()

##------------- Init Misc

	def RegisterEventHandlers( self ):
		self.Bind( wx.EVT_CLOSE, self.OnCloseWindow )

	def InitVariables( self ):
		self.fileName = None
		#self.edl.UnTouchBuffer()

	def MakeMenus( self ):
		self.MainMenu = wx.MenuBar()
		self.AddMenus( self.MainMenu )
		self.SetMenuBar( self.MainMenu )

##------------- Init Subwindows

	def MakeEditorWindow( self, win ):
		style = wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.TE_DONTWRAP

		self._textCtrl = wx.TextCtrl( win, -1, style = style )
		#self._textCtrl.DragAcceptFiles( True )
		#self.Bind( wx.EVT_DROP_FILES, self.OnFileDropped, id=self._textCtrl.Id )
		dt = FileDropTarget(self)
		self._textCtrl.SetDropTarget(dt)

		fontNode = self.configParams.find( 'font' )
		if fontNode is not None:
			font = wx.Font( fontNode.text )
		else:
			font = wx.Font( DEFAULT_FONT_DESC )
		self._textCtrl.SetFont( font )


	def MakeStatusbar( self ):
		self.sb = CustomStatusBar( self )
		self.SetStatusBar( self.sb )

	def MakeLogWindow( self, container ):
		log = wx.TextCtrl( container, -1,
						 style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL )
		wx.Log_SetActiveTarget( wx.LogTextCtrl( log ) )
		wx.LogMessage( 'window handle: %s' % self.GetHandle() )
		return log

	def SetUpSplitter( self, splitter, win, log ):
		splitter.SplitHorizontally( win, log )
		splitter.SetSashPosition( 360, True )
		splitter.SetMinimumPaneSize( 40 )

	def MakeToolbar( self, win ):
		toolbarBox = wx.BoxSizer( wx.HORIZONTAL )
		self.AddButtons( win, toolbarBox )
		return toolbarBox

	def MakeCustomToolbar( self, win ):
		self.customToolbtoolbarBox = wx.BoxSizer( wx.HORIZONTAL )
		self.SetupCustomButtons( win, self.customToolbtoolbarBox )
		return self.customToolbtoolbarBox

	def MakeMainWindow( self, win ):
		mainBox = wx.BoxSizer( wx.VERTICAL )
		mainBox.Add( self.MakeToolbar( win ) )
		mainBox.Add( self.MakeCustomToolbar( win ) )
		borderWidth = 2
		mainBox.Add( self._textCtrl, 1, wx.ALL|wx.GROW, borderWidth )
		win.SetSizer( mainBox )
		win.SetAutoLayout( True )
		self.mainBox = mainBox

##-------------- Init Menus

	# override this to add more menus
	def AddMenus( self, menu ):
		self.AddFileMenu( menu )
		self.AddViewMenu( menu )
		self.AddHelpMenu( menu )

	def AddMenuItem( self, menu, itemText, itemDescription, itemHandler ):
		menuId = wx.NewId()
		menu.Append( menuId, itemText, itemDescription )
		self.Bind( wx.EVT_MENU, itemHandler, id=menuId )
		return menuId

	def AddFileMenu( self, menu ):
		fileMenu = wx.Menu()
		self.AddMenuItem( fileMenu, 'Reload', 'Reload current file', self.OnReload )
		self.AddMenuItem( fileMenu, 'Open File', 'Open File', self.OnOpenFile )
		#self.AddMenuItem( fileMenu, '&Save File\tCtrl-S', 'Save File', self.OnSaveFile )
		self.AddMenuItem( fileMenu, 'Save View As', 'Save File As', self.OnSaveFileAs )
		self.AddMenuItem( fileMenu, 'Exit', 'Exit', self.OnFileExit )
		menu.Append( fileMenu, 'File' )

	def AddViewMenu( self, menu ):
		viewMenu = wx.Menu()
		self.AddMenuItem( viewMenu, 'Select font', 'View area font selection', self.OnSetFont )
		self.AddMenuItem( viewMenu, 'Buttons Config', 'Configure custom buttons', self.OnConfigureCustomButtons )
		viewMenu.AppendSeparator();

		menuId = wx.NewId()
		viewMenu.Append( menuId, "Show line numbers", "Toggle showing line numbers", wx.ITEM_CHECK )
		viewMenu.Check( menuId, self.showLineNumbers )
		self.Bind( wx.EVT_MENU, self.OnToggleLineNumbers, id=menuId )

		#enuId = wx.NewId()
		#iewMenu.Append( menuId, "Append tabbed lines", "Toggle appending tabbed lines occuring just after matching lines", wx.ITEM_CHECK )
		#iewMenu.Check( menuId, self.appendTabbedLines )
		#elf.Bind( wx.EVT_MENU, self.OnToggleAppendTabbedLines, id=menuId )

		menu.Append( viewMenu, 'View' )

	def AddHelpMenu( self, menu ):
		helpMenu = wx.Menu()
		self.AddMenuItem( helpMenu, 'About', 'About the program', self.OnHelpAbout )
		menu.Append( helpMenu, 'Help' )

##---------------- Init Buttons

	def SetTooltip( self, button, dataKey ):
		if dataKey in self.buttonData:
			button.SetToolTip( self.buttonData[ dataKey ] )

	def NewButton( self, window, container, name, pos, size, handler ):
		buttonId = wx.NewId()
		button = None
		if pos == None or size == None:
			button = wx.Button( window, buttonId, name )
		else:
			button = wx.Button( window, buttonId, name, pos, size )

		container.Add( button, 0, 0 )
		self.Bind( wx.EVT_BUTTON, handler, id=buttonId )

		self.SetTooltip( button, name )

		return buttonId, button

	def NewCustomButton( self, window, container, name, pos, size, handler ):
		buttonId = wx.NewId()
		button = None
		if pos == None or size == None:
			button = wx.Button( window, buttonId, name )
		else:
			button = wx.Button( window, buttonId, name, pos, size )

		container.Add( button, 0, 0 )
		self.Bind( wx.EVT_BUTTON, handler, id=buttonId )
		return buttonId, button

	# override this to make more buttons
	def AddButtons( self, window, container ):
		buttonPos = None
		buttonSize = None

		buttonId = wx.NewId()
		button = wx.BitmapButton( window, buttonId, self.reloadBitmap )
		self.SetTooltip( button, 'Reload' )
		#wx.Button( window, buttonId,  )
		container.Add( button, 0, 0 )
		self.Bind( wx.EVT_BUTTON, self.OnReload, id=buttonId )

		self.NewButton( window, container, "Clear", buttonPos, buttonSize, self.OnClear )

		buttonId = wx.NewId()
		self.customPatternCtrl = wx.ComboBox( window, buttonId, style = wx.CB_DROPDOWN )
		self.customPatternCtrl.SetInitialSize( ( 170, 25 ) )
		container.Add( self.customPatternCtrl, 0, 0 )
		self.customPatternCtrl.Bind( wx.EVT_TEXT_ENTER, self.OnCustomPattern )
		id, button = self.NewButton( window, container, "Execute pattern", buttonPos, buttonSize, self.OnCustomPattern )
		button.SetForegroundColour( CUSTOM_EXPRESSION_BUTTON_COLOR )

		container.Add( ( 6, 10 ) )

		buttonId = wx.NewId()
		self.btBxclution = wx.CheckBox( window, buttonId, 'Exclusion' )
		self.btBxclution.SetMinSize( ( -1, 23 ) )
		self.SetTooltip( self.btBxclution, 'Exclusion' )
		self.btBxclution.SetValue( self.exclusion );
		container.Add( self.btBxclution, 0, 0 )
		self.Bind( wx.EVT_CHECKBOX, self.OnExclusion, id=buttonId )

		buttonId = wx.NewId()
		button = wx.CheckBox( window, buttonId, 'Show only matching lines' )
		button.SetMinSize( ( -1, 23 ) )
		self.SetTooltip( button, 'Show only matching lines' )
		button.SetValue( self.showOnlyMatching );
		container.Add( button, 0, 0 )
		self.Bind( wx.EVT_CHECKBOX, self.OnShowOnlyMatching, id=buttonId )

		# loading previously saved custom patterns
		customPatternNode = self.configParams.find( 'custom_patterns' )
		if customPatternNode is not None:
			items = []
			for child in customPatternNode:
				if child.text is not None:
					items.append( child.text )

			if len( items ) > 0:
				self.customPatterns.extend( items )
				self.customPatternCtrl.AppendItems( items )

		#self.customPatternCtrl.

	def SetupCustomButtons( self, window, container ):
		buttonPos = None
		buttonSize = None

		if len( self.customButtons ) == 0:
			customButtons = self.configParams.find( 'custom_buttons' )
			for childNode in customButtons:
				customButton = CustomButtonRecord()
				customButton.Load( childNode )

				buttonId = self.CreateCustomButtonFromDesc( window, container, customButton )
				self.customButtons[ str( buttonId ) ] = customButton
				self.customButtonsOrdered.append( customButton )
		else:
			for customButton in self.customButtons.values():
				self.CreateCustomButtonFromDesc( window, container, customButton )


	def CreateCustomButtonFromDesc( self, window, container, customButton ):
		buttonId = wx.NewId()
		customButton.button = wx.Button( window, buttonId, customButton.name )
		customButton.button.SetToolTip( customButton.GetToolTip() )
		self.Bind( wx.EVT_BUTTON, self.OnCustomButton, id=buttonId )

		if customButton.enabled is False:
			customButton.button.Enable( False )

		container.Add( customButton.button, 0, 0 )
		return buttonId

##-------------- Init Dialogs

	def MessageDialog( self, text, title ):
		messageDialog = wx.MessageDialog( self, text, title, wx.OK | wx.ICON_INFORMATION )
		messageDialog.ShowModal()
		messageDialog.Destroy()

	def OkCancelDialog( self, text, title ):
		dialog = wx.MessageDialog( self, text, title, wx.OK | wx.CANCEL | wx.ICON_INFORMATION )
		result = dialog.ShowModal()
		dialog.Destroy()
		if result == wx.ID_OK:
			return True
		else:
			return False

	def SelectFileDialog( self, defaultDir=None, defaultFile=None, wildCard=None ):
		if defaultDir == None:
			defaultDir = "."
		if defaultFile == None:
			defaultFile = ""
		if wildCard == None:
			wildCard = "*.*"
		fileName = None
		fileDialog = wx.FileDialog( self, "Choose a file", defaultDir, defaultFile, wildCard, wx.FD_OPEN|wx.FD_MULTIPLE )
		result = fileDialog.ShowModal()
		if result == wx.ID_OK:
			fileName = fileDialog.GetPath()
			#wx.LogMessage('You selected: %s\n' % fileName)
		fileDialog.Destroy()
		return fileName

	def OpenFileError( self, fileName ):
		#wx.LogMessage( 'Open file error.' )
		self.MessageDialog( "Error opening file '%s'!" % fileName, "Error" )


	def SaveFileError( self, fileName ):
		wx.LogMessage( 'Save file error.' )
		self.MessageDialog( "Error saving file '%s'!" % fileName, "Error" )

##---------------- Utility functions


	def SetControlFuncs( self, action ):
		"for overriding editor's keys"
		"""FrogEditor.SetControlFuncs(self.edl, action)
		action['a'] = self.OnSaveFileAs
		action['o'] = self.OnOpenFile
		action['n'] = self.OnNewFile
		action['s'] = self.OnSaveFile
		"""
		pass

	def SetAltFuncs( self, action ):
		#FrogEditor.SetAltFuncs(self.edl, action)
		#action['x'] = self.OnFileExit
		pass

	def GetCurrentDir( self ):
		if self.fileName is not None:
			return os.path.split( self.fileName )[0]
		return "."

	def GetFileName( self ):
		if self.fileName is not None:
			return os.path.split( self.fileName )[1]
		return ""

	def GetTextCtrl(self):
		return self._textCtrl

	def NewFile( self ):
		self._textCtrl.SetValue( "" )
		self.fileName = None
		self.sb.setFileName( "" )

	def SaveFile( self, fileName ):
		try:
			#contents = string.join(self._textCtrl.GetValue(), '\n')
			contents = self._textCtrl.GetValue()
			f = open( fileName, 'w' )
			f.write( contents )
			f.close()
			#self.edl.UnTouchBuffer()
			self.sb.setFileName( fileName )
			return True
		except:
			return False

	def OpenFile( self, fileName ):
		wx.BeginBusyCursor()
		try:
			f = open( fileName, 'r' )
			contents = f.readlines()
			f.close()
			contents = [chomp( line ) for line in contents]
			self.contents = contents
			if len( contents ) == 0:
				contents = [""]
				text = ""
			elif self.showLineNumbers:
				contentsWithNumbers = []
				lineNumber = 0
				for line in contents:
					lineNumber = lineNumber + 1
					contentsWithNumbers.append( self.lineFormatString % ( lineNumber, line ) )
				text = string.join( contentsWithNumbers, '\n' )
			else:
				text = string.join( contents, '\n' )

			self._textCtrl.SetValue( text )
			self.fileName = fileName
			self.sb.setFileName( fileName )

			self.ClearParsing()
			wx.EndBusyCursor()
			return True
		except:
			wx.EndBusyCursor()
			return False

	def ClearParsing(self):
		self.patterns = {}
		self.specialStyling = []
		self._textCtrl.SetDefaultStyle( self._textCtrl.GetDefaultStyle() )

		for customButton in self.customButtonsOrdered:
			customButton.button.SetForegroundColour( wx.NullColour )
			customButton.button.SetBackgroundColour( wx.NullColour )

##---------------- Event handlers

	def SaveValue(self, root, name, value):
		node = ET.Element( name )
		if isinstance( value, str ):
			node.text = value
		else:
			node.text = str(value)
		root.append( node )

	def OnCloseWindow( self, event ):
		root = ET.Element( 'LogViewerConfig' )
		self.configParams = ET.ElementTree( root )

		node = ET.Element( 'font' )
		font = self._textCtrl.GetFont()
		node.text = font.GetNativeFontInfoDesc()
		root.append( node )

		self.SaveValue( root, 'show_line_numbers', self.showLineNumbers )
		#elf.SaveValue( root, 'append_tabbed_lines', self.appendTabbedLines )
		self.SaveValue( root, 'line_numebers_format_string', self.lineFormatString )
		self.SaveValue( root, 'last_file', self.fileName )
		self.SaveValue( root, 'exclusion', self.exclusion )
		self.SaveValue( root, 'only_matching', self.showOnlyMatching )

		node = ET.Element( 'custom_buttons' )
		for i in range( len( node )-1, -1, -1 ):
			del node[i]
		for customButton in self.customButtonsOrdered:
			customButton.Save( node )
		root.append( node )

		#saving last 10 patterns
		customPatternNode = ET.Element( 'custom_patterns' )
		root.append( customPatternNode )

		items = self.customPatternCtrl.GetItems()
		i = 0
		for item in items:
			node = ET.Element( 'pattern' )
			node.text = item
			customPatternNode.append( node )
			i = i+1
			if i >= CUSTOM_PATTERNS_LIMIT:
				break

		#self.edl.OnCloseWindow(event)
		self.configParams.write( CONFIG_FILE_NAME )
		self.Destroy()

	def OnReload( self, event ):
		if self.fileName is None:
			return

		if self.OpenFile( self.fileName ) is False:
			self.OpenFileError( self.fileName )

	def OnFileDropped( self, event ):
		i = 1
		return

	def OnOpenFile( self, event ):
		"""if self.edl.BufferWasTouched():
			if not self.OkCancelDialog("Open file - abandon changes?", "Open File"):
				return
		"""
		fileName = self.SelectFileDialog( self.GetCurrentDir() )
		if fileName is not None:
			if self.OpenFile( fileName ) is False:
				self.OpenFileError( fileName )
		self._textCtrl.SetFocus()

		#attr = wx.TextAttr( "#000000","#C9FFEE" )#, alignment = wx.TEXT_ALIGNMENT_RIGHT )
		#self._textCtrl.SetStyle( 0, 300, attr )

	def OnSaveFile( self, event ):
		if self.fileName is None:
			return self.OnSaveFileAs( event )
		wx.LogMessage( "Saving %s..." % self.fileName )
		if self.SaveFile( self.fileName ) is not True:
			self.SaveFileError( self.fileName )
		self._textCtrl.SetFocus()

	def OnSaveFileAs( self, event ):
		fileName = self.SelectFileDialog( self.GetCurrentDir(), self.GetFileName() )
		if fileName is not None:
			#self.fileName = fileName
			wx.LogMessage( "Saving %s..." % 	fileName )
			if self.SaveFile( fileName ) is not True:
				self.SaveFileError( fileName )
		self._textCtrl.SetFocus()

	def OnFileExit( self, event ):
		"""if self.edl.BufferWasTouched():
			if not self.OkCancelDialog("Exit program - abandon changes?", "Exit"):
				return
		"""
		self.OnCloseWindow( event )

	def OnEditPreferences( self, event ):
		self.MessageDialog( "Edit preferences is not implemented yet.", "Not implemented." )
		pass

	def OnHelpAbout( self, event ):
		# First we create and fill the info object
		info = wx.adv.AboutDialogInfo()
		info.Name = "Log File Viewer"
		info.Version = "0.8"
		info.Description = wordwrap(
			"\nApplication created to help code people read editor and game log "
			"files.",
			350, wx.ClientDC( self ) )
		info.Developers = [ "Mieszko Zielinski (MieszkoZ @github) Copyright 2008", ]

		# Then we call wx.AboutBox giving it that info object
		wx.adv.AboutBox( info )

	def OnSetFont( self, event ):
		dlg = wx.FontDialog( self, wx.FontData() )
		dlg.GetFontData().SetInitialFont( self._textCtrl.GetFont() )
		if dlg.ShowModal() == wx.ID_OK:
			font = dlg.GetFontData().GetChosenFont()
			self._textCtrl.SetFont( font )

		dlg.Destroy()

	def OnConfigureCustomButtons( self, event ):
		dlg = ConfigDlg( self, self.customButtonsOrdered )
		if dlg.ShowModal() == wx.ID_OK:

			for customButton in self.customButtons.values():
				customButton.button.SetLabel( customButton.name )
				customButton.button.Enable( customButton.enabled )
				#customButton.button.Show( customButton.enabled )
				customButton.button.SetToolTip( customButton.GetToolTip() )

		dlg.Destroy()

	def Show( self, show ):
		wx.Frame.Show( self, show )
		self._textCtrl.SetFocus()

##------------- Startup stuff

	def LoadInitialFile( self, fileName ):
		if fileName is None:
			lastFileNode = self.configParams.find( 'last_file' )
			fileName = lastFileNode.text
			if fileName == None or len( fileName ) == 0:
				return

		if self.OpenFile( fileName ) is False:
			self.OpenFileError( fileName )


##------------- Parsing stuff

	def ParseContent( self ):

		wx.BeginBusyCursor()

		self.specialStyling = []

		tabbedLine = re.compile( "^[(?:\s\s\s\s)\t]" )
		joined = ""

		if len( self.patterns ) > 0:
			lines = self.contents
			lineNumber = 0
			parsedLines = []

			if self.exclusion == False:
				length = 0
				mached = False

				for line in lines:
					lineNumber = lineNumber + 1
					for patternName in self.patterns:
						pattern, button = self.patterns[ patternName ]
						if re.search( pattern, line ):
							if self.showLineNumbers:
								line = self.lineFormatString % ( lineNumber, line )
							parsedLines.append( line )
							end = length + len( line ) + 1
							self.specialStyling.append( (length, end, button.textAttr ) )
							length = end
							mached = True
							break

					if self.showOnlyMatching == False and mached == False:
						if self.showLineNumbers:
							line = self.lineFormatString % ( lineNumber, line )
						length = length + len( line ) + 1
						parsedLines.append( line )

					mached = False

			else: #exclusion == True
				for line in lines:
					lineNumber = lineNumber + 1
					matched = False
					for patternName in self.patterns:
						pattern, button = self.patterns[ patternName ]
						if re.search( pattern, line ):
							matched = True
							break
					if not matched:
						if self.showLineNumbers:
							line = self.lineFormatString % ( lineNumber, line )
						parsedLines.append( line )

			if len( parsedLines ) > 0:
				joined = string.join( parsedLines, '\n' )

		elif len( self.contents ) > 0:
			if self.showLineNumbers:
				contentsWithNumbers = []
				lineNumber = 0
				for line in self.contents:
					lineNumber = lineNumber + 1
					contentsWithNumbers.append( self.lineFormatString % ( lineNumber, line ) )
				joined = string.join( contentsWithNumbers, '\n' )
			else:
				joined = string.join( self.contents, '\n' )

		self._textCtrl.SetValue( joined )
		if len( self.specialStyling ) > 0 :
			for start, end, textAttr in self.specialStyling:
				self._textCtrl.SetStyle( start, end, textAttr )
		else:
			self._textCtrl.SetDefaultStyle( self._textCtrl.GetDefaultStyle() )

		wx.EndBusyCursor()

	def OnExclusion( self, event ):
		self.exclusion = ( self.btBxclution.GetValue() != 0 )
		self.ParseContent()

	def OnShowOnlyMatching( self, event ):
		self.showOnlyMatching = ( event.EventObject.GetValue() != 0 )
		self.ParseContent()

	def OnClear( self, event ):
		self.ClearParsing()
		self.ParseContent()

	def XorPatternToList( self, name, pattern, button = None ):
		""" returns True if pattern was added, False otherwise"""
		bAdded = False
		if name in self.patterns:
			del self.patterns[ name ]
		elif pattern is not None and len(pattern) > 0:
		 	self.patterns[ name ] = ( re.compile( pattern ), button )
		 	bAdded = True

		self.ParseContent()

		return bAdded

	def OnCustomPattern( self, event ):
		pattern = self.customPatternCtrl.GetValue()
		#rawPat = raw( self.customPatternCtrl.GetValue() )
		if pattern not in self.customPatterns:
			self.customPatternCtrl.Insert( pattern, 0 )
			self.customPatterns.append( pattern )

		# at this moment it's possible to have several instances of the same
		# pattern used. It doesn't influence parsing results, but it does influence
		# efficiency.
		self.patterns[ pattern ] = ( re.compile( pattern ), self.customExpresionButton )

		self.ParseContent()

	def OnCustomButton( self, event ):
		key = str( event.Id )
		if key in self.customButtons:
			customButton = self.customButtons[ key ]

			customButton.pushed = self.XorPatternToList( customButton.name, customButton.pattern, customButton )
			if customButton.pushed:
				customButton.PushButton()
			else:
				customButton.button.SetBackgroundColour( wx.NullColour )
				customButton.button.SetForegroundColour( wx.NullColour )

	def OnToggleLineNumbers( self, event ):
		self.showLineNumbers = ( event.Selection != 0 )
		self.ParseContent()

	def OnToggleAppendTabbedLines( self, event ):
		self.appendTabbedLines = ( event.Selection != 0 )
		self.ParseContent()

##-------------- Application Launcher utility class

class LogViewerLauncher:

	def MakeAppFrame( self ):
		return LogViewerFrame( None, -1, "LogViewer", size=( 640, 480 ),
							 style=wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE )

	def GetArgvFilename( self ):
		if len( sys.argv ) > 1:
			return sys.argv[1]
		else:
			return None

	def Main( self ):
		app = wx.App()
		win = self.MakeAppFrame()
		win.SetSize( ( 758, 500 ) )
		win.SetSizeHints( minSize = ( 758, 150 ) )
		win.Show( True )
		win.LoadInitialFile( self.GetArgvFilename() )
		app.MainLoop()


##-------------- Main program


if __name__ == '__main__':

	launcher = LogViewerLauncher()
	launcher.Main()
