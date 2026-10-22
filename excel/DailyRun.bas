Attribute VB_Name = "DailyRun"
Option Explicit
'=======================================================================
' Daily run of the 3D finite-difference diffusion model.
'
' Workbook layout (Reduced_Matrix.xlsx):
'   rows 6:48   state at time t        (numbers)     -> STATE_ADDR
'   rows 50:92  state at time t+1      (formulas that read rows 6:48) -> NEXT_ADDR
'
' One model step (1 minute) = recalculate, then paste the t+1 numbers over t.
' After STEPS_PER_DAY steps the state is written to its own file
' (daily_output\Day_001.xlsx, Day_002.xlsx, ...) with the same cell layout,
' and the loop carries on with the next day until TOTAL_DAYS.
'
' Restart: if Day_NNN.xlsx files already exist, the run loads the newest one
' back into the state block and continues from the following day.
' Stop:    press Esc; the current day is lost, completed days are kept.
'=======================================================================

Private Const SHEET_NAME As String = "Sheet1"
Private Const STATE_ADDR As String = "A6:ACT48"
Private Const NEXT_ADDR As String = "A50:ACT92"
Private Const STEPS_PER_DAY As Long = 1440      ' 1-minute time step
Private Const TOTAL_DAYS As Long = 28
Private Const OUT_SUBFOLDER As String = "daily_output"
' Leave "" to use the workbook's own folder (or Documents if it is on OneDrive/SharePoint).
' Or set a local folder, e.g. "C:\Sim\Andrew".
Private Const OUT_BASE_OVERRIDE As String = ""

' --- minutely output -------------------------------------------------
' 1) Probe cells: value of these cells every minute, saved on a "Minutes"
'    sheet inside each Day file (1440 rows per day). Comma separated, cells of STATE_ADDR.
Private Const PROBE_CELLS As String = "GA17"
' 2) Full field: the whole STATE_ADDR block every FULL_EVERY minutes, appended to
'    Day_NNN_field.csv (0 = off, 1 = every minute: ~100+ MB per day, so use with care).
Private Const FULL_EVERY As Long = 0

Private mStage As String

Public Sub RunDailySimulation()
    Dim ws As Worksheet, st As Range, nx As Range
    Dim outDir As String, lastDone As Long, d As Long, s As Long
    Dim oldCalc As XlCalculation, t0 As Double
    Dim probes() As String, nProbe As Long, pv() As Variant, k As Long
    Dim csvNo As Integer, v As Variant

    On Error GoTo Failed
    Set ws = ThisWorkbook.Worksheets(SHEET_NAME)
    Set st = ws.Range(STATE_ADDR)
    Set nx = ws.Range(NEXT_ADDR)
    If st.Rows.Count <> nx.Rows.Count Or st.Columns.Count <> nx.Columns.Count Then
        Err.Raise vbObjectError + 1, , "STATE_ADDR and NEXT_ADDR must be the same size."
    End If

    mStage = "output folder"
    outDir = OutputDir()
    If Dir(outDir, vbDirectory) = "" Then MkDir outDir
    mStage = "setup"
    probes = Split(Replace(PROBE_CELLS, " ", ""), ",")
    nProbe = 0
    If Len(PROBE_CELLS) > 0 Then nProbe = UBound(probes) + 1

    oldCalc = Application.Calculation
    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.Calculation = xlCalculationManual
    Application.EnableCancelKey = xlErrorHandler

    lastDone = LastCompletedDay(outDir)
    If lastDone >= TOTAL_DAYS Then
        MsgBox "All " & TOTAL_DAYS & " days already exist in " & outDir, vbInformation
        GoTo Cleanup
    End If
    If lastDone > 0 Then mStage = "loading day " & lastDone: LoadState st, outDir, lastDone

    For d = lastDone + 1 To TOTAL_DAYS
        mStage = "running day " & d
        t0 = Timer
        If nProbe > 0 Then ReDim pv(1 To STEPS_PER_DAY, 1 To nProbe + 1)
        csvNo = 0
        If FULL_EVERY > 0 Then
            csvNo = FreeFile
            Open DayFile(outDir, d) & ".csv.tmp" For Output As #csvNo
        End If
        For s = 1 To STEPS_PER_DAY
            ws.Calculate                 ' compute t+1 from t
            st.Value2 = nx.Value2        ' paste numbers only: t+1 becomes t
            If nProbe > 0 Then
                pv(s, 1) = (d - 1) * STEPS_PER_DAY + s
                For k = 1 To nProbe
                    pv(s, k + 1) = ws.Range(probes(k - 1)).Value2
                Next k
            End If
            If FULL_EVERY > 0 Then
                If s Mod FULL_EVERY = 0 Then WriteField csvNo, st, (d - 1) * STEPS_PER_DAY + s
            End If
            If s Mod 60 = 0 Then
                Application.StatusBar = "Day " & d & " of " & TOTAL_DAYS & _
                    "  -  minute " & s & " of " & STEPS_PER_DAY
                DoEvents
            End If
        Next s
        mStage = "saving day " & d
        If csvNo <> 0 Then
            Close #csvNo
            csvNo = 0
            Name DayFile(outDir, d) & ".csv.tmp" As Left$(DayFile(outDir, d), Len(DayFile(outDir, d)) - 5) & "_field.csv"
        End If
        SaveDay st, outDir, d, pv, probes, nProbe
        mStage = "writing log"
        AppendLog outDir, "Day " & d & " done, " & Format(Timer - t0, "0") & " s"
    Next d

    MsgBox "Simulation finished: " & TOTAL_DAYS & " days in " & outDir, vbInformation
    GoTo Cleanup

Failed:
    If Err.Number = 18 Then
        MsgBox "Stopped by user. Completed days are saved; run again to resume.", vbExclamation
    Else
        MsgBox "Error " & Err.Number & ": " & Err.Description & vbCrLf & _
            "Stage: " & mStage & vbCrLf & "Folder: " & outDir, vbCritical
    End If
Cleanup:
    If csvNo <> 0 Then Close #csvNo
    Application.Calculation = oldCalc
    Application.EnableEvents = True
    Application.ScreenUpdating = True
    Application.StatusBar = False
End Sub

Private Function OutputDir() As String
    Dim base As String
    base = OUT_BASE_OVERRIDE
    If base = "" Then base = ThisWorkbook.Path
    ' unsaved workbook or cloud path (OneDrive/SharePoint): Dir/MkDir fail with error 52
    If base = "" Or LCase$(Left$(base, 4)) = "http" Then
        base = Environ$("USERPROFILE") & "\Documents"
    End If
    If Right$(base, 1) = "\" Then base = Left$(base, Len(base) - 1)
    OutputDir = base & "\" & OUT_SUBFOLDER
End Function

Private Function DayFile(outDir As String, dayNo As Long) As String
    DayFile = outDir & "\" & "Day_" & Format(dayNo, "000") & ".xlsx"
End Function

Private Function LastCompletedDay(outDir As String) As Long
    Dim d As Long
    For d = TOTAL_DAYS To 1 Step -1
        If Dir(DayFile(outDir, d)) <> "" Then LastCompletedDay = d: Exit Function
    Next d
End Function

Private Sub LoadState(st As Range, outDir As String, dayNo As Long)
    Dim wb As Workbook
    Set wb = Workbooks.Open(DayFile(outDir, dayNo), UpdateLinks:=0, ReadOnly:=True)
    st.Value2 = wb.Worksheets(1).Range(STATE_ADDR).Value2
    wb.Close SaveChanges:=False
End Sub

Private Sub SaveDay(st As Range, outDir As String, dayNo As Long, pv() As Variant, probes() As String, nProbe As Long)
    Dim wb As Workbook, tmp As String, k As Long
    tmp = DayFile(outDir, dayNo) & ".tmp"      ' rename at the end so a half-written file never counts as done
    Set wb = Workbooks.Add(xlWBATWorksheet)
    With wb.Worksheets(1)
        .Name = "Day " & dayNo
        .Range("A1").Value2 = "Day"
        .Range("B1").Value2 = dayNo
        .Range("A2").Value2 = "Minute"
        .Range("B2").Value2 = dayNo * STEPS_PER_DAY
        .Range(STATE_ADDR).Value2 = st.Value2
    End With
    If nProbe > 0 Then
        wb.Worksheets.Add After:=wb.Worksheets(wb.Worksheets.Count)
        With wb.Worksheets(wb.Worksheets.Count)
            .Name = "Minutes"
            .Range("A1").Value2 = "Minute"
            For k = 1 To nProbe
                .Cells(1, k + 1).Value2 = probes(k - 1)
            Next k
            .Range(.Cells(2, 1), .Cells(STEPS_PER_DAY + 1, nProbe + 1)).Value2 = pv
        End With
        wb.Worksheets(1).Activate
    End If
    Application.DisplayAlerts = False
    wb.SaveAs Filename:=tmp, FileFormat:=xlOpenXMLWorkbook
    Application.DisplayAlerts = True
    wb.Close SaveChanges:=False
    Name tmp As DayFile(outDir, dayNo)
End Sub

Private Sub WriteField(fileNo As Integer, st As Range, minuteNo As Long)
    Dim v As Variant, r As Long, c As Long, parts() As String
    v = st.Value2
    Print #fileNo, "# minute " & minuteNo
    ReDim parts(1 To UBound(v, 2))
    For r = 1 To UBound(v, 1)
        For c = 1 To UBound(v, 2)
            parts(c) = CStr(v(r, c))
        Next c
        Print #fileNo, Join(parts, ",")
    Next r
End Sub

Private Sub AppendLog(outDir As String, msg As String)
    Dim f As Integer
    f = FreeFile
    Open outDir & "\" & "run_log.txt" For Append As #f
    Print #f, Format(Now, "yyyy-mm-dd hh:nn:ss") & "  " & msg
    Close #f
End Sub
