Option Explicit

Dim messageText
Dim titleText

If WScript.Arguments.Count > 0 Then
    messageText = WScript.Arguments.Item(0)
Else
    messageText = "Gravity a rencontre une erreur."
End If

If WScript.Arguments.Count > 1 Then
    titleText = WScript.Arguments.Item(1)
Else
    titleText = "Gravity"
End If

MsgBox messageText, vbCritical + vbOKOnly, titleText
