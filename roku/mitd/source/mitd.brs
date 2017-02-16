' *********************************************************
' **  Dark Matter / MITD Roku Channel
' **  Charles Toepfer, 2016
' **  charles.toepfer@gmail.com
' *********************************************************

' *********************************************************
' **  Main, Show main menu screen
' *********************************************************
Sub Main()

  menuOptions = [
    {
      Title:"Listen LIVE",
      ShortDescriptionLine1:"Listen LIVE FREE",
      SDBackgroundImageUrl: "pkg:/images/listen_live_sd.jpg",
      HDBackgroundImageUrl: "pkg:/images/listen_live_hd.jpg",
    },
    {
      Title:"Show Archives",
      ShortDescriptionLine1:"Show Archives (Members)",
      SDBackgroundImageUrl: "pkg:/images/show_archives_sd.jpg",
      HDBackgroundImageUrl: "pkg:/images/show_archives_hd.jpg",
    },
    {
      Title:"Login Settings",
      ShortDescriptionLine1:"Setup User / Password",
      SDBackgroundImageUrl: "pkg:/images/login_settings_sd.png",
      HDBackgroundImageUrl: "pkg:/images/login_settings_hd.png",
    },
  ]

  screen = CreateObject("roListScreen")
  screen.SetContent(menuOptions)

  screen.SetHeader("Options")
  screen.SetTitle("Midnight in the Desert")
  screen.setBreadcrumbText("Main Menu", "")

  port = CreateObject("roMessagePort")
  screen.SetMessagePort(port)

  screen.show()

  While(true)

    msg = wait(0,port)

    If msg.isScreenClosed() Then
      Exit While
    Else if (type(msg) = "roListScreenEvent")

      If(msg.isListItemFocused())
        screen.setBreadcrumbText("Main Menu", menuOptions[msg.GetIndex()].Title)
      End If

      If(msg.isListItemSelected())

        If msg.GetIndex() = 2' Login Settings
          username = ShowKeyboardScreen("Enter your username")
          RegWrite("username", username)
          If username <> "" then
            password = ShowKeyboardScreen("Enter your password", true)
            RegWrite("password", password)
          End If
        End If

        If msg.GetIndex() = 0' Live Feed
          o = AudioLoadLiveFeed()
          AudioPlayScreen(o)
        End If

        If msg.GetIndex() = 1' Show Archives
          up = GetUserPass()

          If up.username <> "" and up.password <> ""
            username = up.username
            password = up.password
            o = AudioLoadFeed(username, password)
          End If

        End If

      End If

    End If

  End While

End Sub

' *********************************************************
' **  Return Saved User / Pass
' *********************************************************
Function GetUserPass() As Object

  up = CreateObject("roAssociativeArray")

  up.username = RegRead("username")
  up.password = RegRead("password")

  If up.username <> "" and up.password <> ""
    Return up
  Else

    port = CreateObject("roMessagePort")
    dialog = CreateObject("roMessageDialog")
    dialog.SetMessagePort(port)
    dialog.SetTitle("Missing Login Settings")
    dialog.SetText("Please enter a username / passoword in the login settings before using the show archives.")

    dialog.AddButton(1, "OK")
    dialog.EnableBackButton(true)
    dialog.Show()
    While True
      dlgMsg = wait(0, dialog.GetMessagePort())
      If dlgMsg.isScreenClosed()
        Exit While
      Else If type(dlgMsg) = "roMessageDialogEvent"
        If dlgMsg.isButtonPressed()
          If dlgMsg.GetIndex() = 1
            Exit While
          End If
        End If
      End If
    End While
    Return up
  End If

End Function


' *********************************************************
' **  Load the MITD RSS Feed, return Audio object
' *********************************************************
Function AudioLoadFeed(username, password) As Object

  xfer = CreateObject("roURLTransfer")
  url = "http://rss.darkmatterdigitalnetwork.com/mitd/"
  xfer.SetURL(url)
  ba = CreateObject("roByteArray")
  ba.FromAsciiString(username + ":" + password)
  xfer.AddHeader("Authorization", "Basic " + ba.ToBase64String())
  response = xfer.GetToString()
  xml = CreateObject("roXMLElement")

  If xml.Parse(response)

    items = CreateObject("roArray", 10, true)
    n=xml.channel.item.Count()-1

    For i = 0 to n

      item = CreateObject("roAssociativeArray")
      item.Url = xml.channel.item[i].enclosure@url
      item.Title = xml.channel.item[i].title.gettext()
      item.Description = xml.channel.item[i].description.gettext()
      'item.HDPosterUrl = xml.channel.image[1]@href 'Wrong size
      'item.SDPosterUrl = xml.channel.image[1]@href 'Wrong size
      item.HDPosterUrl = "pkg:/images/art_tt_podcast_188.jpg"
      item.SDPosterUrl = "pkg:/images/art_tt_podcast_124.jpg"
      item.Artist = xml.channel.author[0].gettext()
      item.ReleaseDate = StdPubDate(xml.channel.item[i].pubDate.gettext())
      item.StreamFormat = "mp3"
      item.CurrentPosition = 0
      items[i] = item

    End For

    ArchiveSelectionScreen(items)

  End If

End Function

' *********************************************************
' **  Return audio object for live feed
' *********************************************************
Function AudioLoadLiveFeed() As Object

  o = CreateObject("roAssociativeArray")
  o.HDPosterUrl = "pkg:/images/art_mitd_podcast_188.jpg"
  o.SDPosterUrl = "pkg:/images/art_mitd_podcast_124.jpg"

  o.Title = "Live Feed"
  o.Album = "Dark Matter Digital Network"

  o.Rating = "NR"
  date = CreateObject("roDateTime")
  o.ReleaseDate = date.AsDateString("long-date")

  o.Url = "http://live.darkmatterradio.net:8303/stream?type=.mp3"
  o.StreamFormat = "mp3"
  o.CurrentPosition = 0

  Return o

End Function

' *********************************************************
' **  Play audio, show basic audio screen w/ controls
' *********************************************************
Function AudioPlayScreen(o As Object) As Integer

  port = CreateObject("roMessagePort")
  screen = CreateObject("roSpringboardScreen")
  screen.SetMessagePort(port)
  screen.SetDescriptionStyle("audio")
  screen.SetContent({ContentType: "audio"})

  screen.SetStaticRatingEnabled(false)
  screen.SetProgressIndicatorEnabled(true)
  screen.AllowUpdates(true)
  screen.AllowNavRight(true)
  screen.AllowNavLeft(true)
  screen.AllowNavRewind(true)
  screen.AllowNavFastForward(true)

  screen.ClearButtons()
  screen.AddButton(2, "Pause")
  screen.AddButton(6, "Back")

  audioPlayer = CreateObject("roAudioPlayer")
  audioPlayer.SetMessagePort(port)

  screen.SetContent(o)

  screen.Show()

  playbackTimer = CreateObject( "roDateTime" )
  isPlaying = False
  isPaused = False
  isBuffering = False

  audioPlayer.SetContentList( [ o ] )

  audioPlayer.setloop(false)
  audioPlayer.play()

  timer=createobject("rotimespan")
  timer.mark()

  screen.setProgressIndicator(timer.totalseconds(), 60)

  While True
    msg = wait(0, port)
    If msg.isScreenClosed() Then
      Exit While
    Else if msg.isButtonPressed()

      if msg.GetIndex() = 2' Pause Button
        audioPlayer.Pause()
        screen.ClearButtons()
        screen.AddButton(3, "Resume")
        screen.AddButton(6, "Back")
      End If

      if msg.GetIndex() = 3' Pause Button
        audioPlayer.Resume()
        screen.ClearButtons()
        screen.AddButton(2, "Pause")
        screen.AddButton(6, "Back")
      End If

      if msg.GetIndex() = 6' Back Button
        screen.Close()
      End If

    Endif
  End While

  return 1

End Function

' *********************************************************
' **  Archived shows screen, select / play
' *********************************************************
Function ArchiveSelectionScreen(items As Object) As Integer

  n = items.Count() - 1

  menuOptions = CreateObject("roArray", 10, true)

  For i = 0 to n
    title = items[i].title
    item = CreateObject("roAssociativeArray")
    menuOptions[i] = { Title: title }
  End For

  screen = CreateObject("roListScreen")
  screen.SetContent(menuOptions)

  screen.SetHeader("Options")
  screen.SetTitle("Archives")
  screen.setBreadcrumbText("Archives", "")

  port = CreateObject("roMessagePort")
  screen.SetMessagePort(port)

  screen.show()

  While(true)
    msg = wait(0,port)

    If(msg.isListItemFocused())
      screen.setBreadcrumbText("Archives", menuOptions[msg.GetIndex()].Title)
    End If

    If msg.isScreenClosed() Then
      Exit While
    Else If (type(msg) = "roListScreenEvent")
      If(msg.isListItemSelected())
        o = items[msg.GetIndex()]
        AudioPlayScreen(o)
      End If
    End If

  End While

End Function

' *********************************************************
' **  Keyboard prompt
' *********************************************************
function ShowKeyboardScreen(prompt = "", secure = false)
  result = ""

  port = CreateObject("roMessagePort")
  screen = CreateObject("roKeyboardScreen")
  screen.SetMessagePort(port)

  screen.SetDisplayText(prompt)

  screen.AddButton(1, "Okay")
  screen.AddButton(2, "Cancel")

  screen.SetSecureText(secure)

  screen.Show()

  While True
    ' wait for an event from the screen
    msg = wait(0, port)

    If msg.isScreenClosed() Then
      Exit While
    Else If type(msg) = "roKeyboardScreenEvent" then
      If msg.isButtonPressed()
        If msg.GetIndex() = 1
          result = screen.GetText()
          Exit While
        Else If msg.GetIndex() = 2
          result = ""
          Exit While
        End If
      End If
    End If

  End While

  screen.Close()
  Return result

End Function

' *********************************************************
' **  Save val pair to app registry
' *********************************************************
Function RegWrite(key as String, val as String, section = invalid) as Void
  If section = invalid Then section = "Default"
  sec = CreateObject("roRegistrySection", section)
  sec.Write(key, val)
  sec.Flush() ' commit it
End Function

' *********************************************************
' **  Read val pair to app registry
' *********************************************************
Function RegRead(key, section = invalid)
  If section = invalid Then section = "Default"
  reg = CreateObject("roRegistry")
  sec = CreateObject("roRegistrySection", section)
  If sec.Exists(key) Then return sec.Read(key)
  Return invalid
End Function

' *********************************************************
' **  Fix Date format in RSS to YYYY/MM/DD
' *********************************************************
Function StdPubDate(X$ as String) as String

  month$="00"

  If Mid(X$,9,3) ="Jan" then month$="01"
  If Mid(X$,9,3) ="Feb" then month$="02"
  If Mid(X$,9,3) ="Mar" then month$="03"
  If Mid(X$,9,3) ="Apr" then month$="04"
  If Mid(X$,9,3) ="May" then month$="05"
  If Mid(X$,9,3) ="Jun" then month$="06"
  If Mid(X$,9,3) ="Jul" then month$="07"
  If Mid(X$,9,3) ="Aug" then month$="08"
  If Mid(X$,9,3) ="Sep" then month$="09"
  If Mid(X$,9,3) ="Oct" then month$="10"
  If Mid(X$,9,3) ="Nov" then month$="11"
  If Mid(X$,9,3) ="Dec" then month$="12"

  date$=  Mid(X$,13,4) + "/" + month$ + "/" +Mid(X$,6,2)

  Return date$

End Function
