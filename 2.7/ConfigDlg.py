import  wx

class ConfigDlg( wx.Dialog ):
	def __init__(
			self, parent, data, title='Configure custom buttons', size=wx.DefaultSize, pos=wx.DefaultPosition,
			style=wx.DEFAULT_DIALOG_STYLE,
			useMetal=False, ):

		ID = wx.NewId()

		self.data = data

		wx.Dialog.__init__(self)   
		self.SetExtraStyle(wx.FRAME_EX_CONTEXTHELP)
		self.Create( parent, ID, title, pos, size, style )

		# This extra style can be set after the UI object has been created.
		if 'wxMac' in wx.PlatformInfo and useMetal:
			self.SetExtraStyle( wx.DIALOG_EX_METAL )


		# Now continue with the normal construction of the dialog
		# contents
		sizer = wx.BoxSizer( wx.VERTICAL )
		self.sets = [ wx.BoxSizer( wx.HORIZONTAL ) for  i in range( len( data ) ) ]

		self.foregrounds = {}
		self.backgrounds = {}

		spacing = 8
		index = 0
		for box in self.sets:
			buttonData = data[ index ]

			button = self.AddControl( box, wx.CheckBox, ( -1, 20 ) )
			button.SetValue( buttonData.enabled )

			button = self.AddControl( box, wx.TextCtrl, ( 100, -1 ) )
			button.SetValue( buttonData.name )

			button = self.AddControl( box, wx.TextCtrl, ( 200, -1 ) )
			if buttonData.pattern is not None:
				button.SetValue( buttonData.pattern )

			button = self.AddControl( box, wx.Button, ( -1, -1 ) )
			button.SetLabel( 'Foreground' )
			if buttonData.foregroundColor is not None:
				button.SetBackgroundColour( buttonData.foregroundColor )
			self.Bind( wx.EVT_BUTTON, self.OnColorButton, id=button.Id )
			self.foregrounds[ str( button.Id ) ] = buttonData

			button = self.AddControl( box, wx.Button, ( -1, -1 ) )
			button.SetLabel( 'Background' )
			if buttonData.backgroundColor is not None:
				button.SetBackgroundColour( buttonData.backgroundColor )
			self.Bind( wx.EVT_BUTTON, self.OnColorButton, id=button.Id )
			self.backgrounds[ str( button.Id ) ] = buttonData

			sizer.Add( box, 0, wx.ALIGN_CENTRE|wx.ALL|wx.EXPAND, 2 )

			index = index+1

		btnsizer = wx.StdDialogButtonSizer()

		if wx.Platform != "__WXMSW__":
			btn = wx.ContextHelpButton( self )
			btnsizer.AddButton( btn )

		btn = wx.Button( self, wx.ID_OK )
		btn.SetDefault()
		self.Bind( wx.EVT_BUTTON, self.OnOK, id=wx.ID_OK )
		btnsizer.AddButton( btn )

		btn = wx.Button( self, wx.ID_CANCEL )
		btnsizer.AddButton( btn )
		btnsizer.Realize()

		sizer.Add( btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )

		self.SetSizer( sizer )
		sizer.Fit( self )

	def AddControl( self, container, controlType, minSize ):
		buttonId = wx.NewId()
		button = None

		button = controlType( self, buttonId )
		button.SetMinSize( minSize )

		container.Add( button, 0, 0 )

		return button

	def OnOK( self, event ):
		i = 0
		for box in self.sets:
			items = box.GetChildren()
			customButton = self.data[ i ]
			customButton.enabled = items[0].Window.GetValue()
			customButton.name = items[1].Window.GetValue()
			customButton.pattern = items[2].Window.GetValue()
			i = i + 1

		self.Unbind( wx.EVT_BUTTON, id=wx.ID_OK )
		wx.Dialog.ProcessEvent( self, event )

	def OnColorButton( self, event ):
		dlg = wx.ColourDialog( self )

		# Ensure the full colour dialog is displayed,
		# not the abbreviated version.
		dlg.GetColourData().SetChooseFull( True )

		strId = str( event.Id )
		if strId in self.foregrounds:
			customButton = self.foregrounds[ strId ]
			dlg.GetColourData().SetColour( customButton.foregroundColor )
		elif strId in self.backgrounds:
			customButton = self.backgrounds[ strId ]
			dlg.GetColourData().SetColour( customButton.backgroundColor )

		if dlg.ShowModal() == wx.ID_OK:

			# If the user selected OK, then the dialog's wx.ColourData will
			# contain valid information. Fetch the data ...
			data = dlg.GetColourData()

			# ... then do something with it. The actual colour data will be
			# returned as a three-tuple (r, g, b) in this particular case.
			if strId in self.foregrounds:
				customButton.SetForegroundColor( data.GetColour().GetAsString() )
				event.EventObject.SetBackgroundColour( customButton.foregroundColor )
			elif strId in self.backgrounds:
				customButton.SetBackgroundColor( data.GetColour().GetAsString() )
				event.EventObject.SetBackgroundColour( customButton.backgroundColor )

		# Once the dialog is destroyed, Mr. wx.ColourData is no longer your
		# friend. Don't use it again!
		dlg.Destroy()
