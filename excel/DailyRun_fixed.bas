Attribute VB_Name = "DailyRun"
Option Explicit
'=======================================================================
' Daily run of the 3D finite-difference diffusion model.
'
' Version for the corrected workbook Reduced_Matrix_fixed.xlsx (tools/fix_reduced_matrix_xlsx.py): the last tile
' moved one column to the right, so the blocks end at column ACU instead of ACT. Use DailyRun.bas for the original.
'
' Workbook layout (Reduced_Matrix_fixed.xlsx):
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
'
' HOW TO USE (details: docs/how-macro.md in the repository)
'   1. Work on a COPY of the workbook, saved as macro-enabled (.xlsm). The macro overwrites the
'      state block (STATE_ADDR) while it runs, so keep a clean copy of the initial state.
'   2. Alt+F11 > File > Import File > this file. Check the settings below.
'   3. First test: STEPS_PER_DAY = 10, TOTAL_DAYS = 1, then compare Day_001.xlsx with the Fortran program.
'   4. Run RunDailySimulation (Alt+F8). Press Esc to stop; run it again to continue.
'   5. To start again from day 1, delete the folder daily_output (otherwise the run continues
'      after the newest Day file).
'
' STRUCTURE OF THIS FILE
'   RunDailySimulation  the main routine: setup, restart, day loop, minute loop, error handling
'   OutputDir           where the files go
'   DayFile             the file name of one day
'   LastCompletedDay    restart: the newest finished day
'   LoadState           restart: copy a Day file back into the state block
'   SaveDay             write the state (and the Minutes sheet) of one day
'   WriteField          append the state block to a csv file (optional output)
'   AppendLog           add one line to run_log.txt
'
' This file must keep Windows line ends (CR+LF) and plain ASCII text, or the VBA editor refuses it.
'=======================================================================

' ---- settings: change only these constants --------------------------------------------------------

' The worksheet that holds the model (parameters in rows 1 to 4, the two blocks below them).
Private Const SHEET_NAME As String = "Sheet1"
' The two blocks. Both must have exactly the same size (the macro checks this at the start).
'   STATE_ADDR : the concentrations at time t, plain numbers. The macro overwrites them every minute.
'   NEXT_ADDR  : the formulas for time t+1. They read only STATE_ADDR and the parameter cells.
' Columns A to ACU are 29 layers of 25 columns, 27 columns apart, plus the source column of each tile.
Private Const STATE_ADDR As String = "A6:ACU48"
Private Const NEXT_ADDR As String = "A50:ACU92"
Private Const STEPS_PER_DAY As Long = 1440      ' 1-minute time step
Private Const TOTAL_DAYS As Long = 28
' Name of the output folder, created next to the workbook.
Private Const OUT_SUBFOLDER As String = "daily_output"
' Leave "" to use the workbook's own folder (or Documents if it is on OneDrive/SharePoint).
' Or set a local folder, e.g. "C:\Sim\Andrew".
Private Const OUT_BASE_OVERRIDE As String = ""

' --- minutely output -------------------------------------------------
' 1) Probe cells: value of these cells every minute, saved on a "Minutes"
'    sheet inside each Day file (1440 rows per day). Comma separated, cells of STATE_ADDR.
'    GA17 is the source cell: it holds the source MASS (volume x concentration, volume = 5625).
'    The Fortran program writes the concentration, so divide this value by 5625 to compare.
Private Const PROBE_CELLS As String = "GA17"
' 2) Full field: the whole STATE_ADDR block every FULL_EVERY minutes, appended to
'    Day_NNN_field.csv (0 = off, 1 = every minute: ~100+ MB per day, so use with care).
Private Const FULL_EVERY As Long = 0

' The step the macro is working on ("setup", "running day 3", "saving day 3" ...). The error message
' shows it, so you can see where the macro stopped. It is module-level so that the error handler can read it.
Private mStage As String

'-----------------------------------------------------------------------
' The main routine. Run this one (Alt+F8 > RunDailySimulation).
'-----------------------------------------------------------------------
Public Sub RunDailySimulation()
    ' ws: the model sheet; st: the state block (time t); nx: the next-state block (time t+1)
    Dim ws As Worksheet, st As Range, nx As Range
    ' outDir: output folder; lastDone: newest finished day; d: day counter; s: minute counter
    Dim outDir As String, lastDone As Long, d As Long, s As Long
    ' oldCalc: the user's calculation mode, restored at the end; t0: start time of the day (seconds)
    Dim oldCalc As XlCalculation, t0 As Double
    ' probes: the probe cell addresses; nProbe: how many; pv: the table of probe values of one day
    ' (row = minute of the day, column 1 = global minute number, columns 2.. = the probe cells)
    Dim probes() As String, nProbe As Long, pv() As Variant, k As Long
    ' csvNo: file number of the open csv file (0 = none open); v: not used
    Dim csvNo As Integer, v As Variant

    ' Any run-time error (and the Esc key, see EnableCancelKey below) jumps to the label Failed.
    On Error GoTo Failed
    Set ws = ThisWorkbook.Worksheets(SHEET_NAME)
    Set st = ws.Range(STATE_ADDR)
    Set nx = ws.Range(NEXT_ADDR)
    ' The two blocks are compared cell by cell in the paste below, so they must have the same shape.
    If st.Rows.Count <> nx.Rows.Count Or st.Columns.Count <> nx.Columns.Count Then
        Err.Raise vbObjectError + 1, , "STATE_ADDR and NEXT_ADDR must be the same size."
    End If

    ' Find (and create if needed) the output folder.
    mStage = "output folder"
    outDir = OutputDir()
    If Dir(outDir, vbDirectory) = "" Then MkDir outDir
    mStage = "setup"
    ' PROBE_CELLS "GA17,GB20" becomes the array ("GA17", "GB20"); blanks are removed first.
    probes = Split(Replace(PROBE_CELLS, " ", ""), ",")
    nProbe = 0
    If Len(PROBE_CELLS) > 0 Then nProbe = UBound(probes) + 1

    ' Speed and safety settings, undone in Cleanup:
    '   - manual calculation: Excel recalculates only when the macro calls ws.Calculate (once per minute),
    '     not after each pasted cell. This is the most important setting.
    '   - no screen updating and no events: the sheet is not redrawn 1440 times a day
    '   - EnableCancelKey: pressing Esc raises error 18 (handled below) instead of an unrecoverable stop
    oldCalc = Application.Calculation
    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.Calculation = xlCalculationManual
    Application.EnableCancelKey = xlErrorHandler

    ' Restart: look for finished days. If all days exist there is nothing to do.
    lastDone = LastCompletedDay(outDir)
    If lastDone >= TOTAL_DAYS Then
        MsgBox "All " & TOTAL_DAYS & " days already exist in " & outDir, vbInformation
        GoTo Cleanup
    End If
    ' Otherwise copy the newest Day file into the state block: the run continues from there.
    If lastDone > 0 Then mStage = "loading day " & lastDone: LoadState st, outDir, lastDone

    ' ---- DAY LOOP: every day that is not finished yet -------------------------------------------
    For d = lastDone + 1 To TOTAL_DAYS
        mStage = "running day " & d
        t0 = Timer
        ' pv holds the probe values of this day until SaveDay writes them to the "Minutes" sheet
        If nProbe > 0 Then ReDim pv(1 To STEPS_PER_DAY, 1 To nProbe + 1)
        csvNo = 0
        ' Optional csv file: written under a temporary name and renamed when the day is complete.
        If FULL_EVERY > 0 Then
            csvNo = FreeFile
            Open DayFile(outDir, d) & ".csv.tmp" For Output As #csvNo
        End If
        ' ---- MINUTE LOOP: one pass = one time step of the model ---------------------------------
        For s = 1 To STEPS_PER_DAY
            ' Excel evaluates the formulas of NEXT_ADDR. They read STATE_ADDR (time t) and the
            ' parameter cells (rows 1 to 4), so the result is the state one minute later.
            ws.Calculate                 ' compute t+1 from t
            ' Value2 copies numbers only (not formulas or formats) and is the fastest way. The formulas
            ' of NEXT_ADDR stay untouched. Now the lower block is the new "old state": t+1 becomes t.
            st.Value2 = nx.Value2        ' paste numbers only: t+1 becomes t
            ' Record the probe cells for this minute (global minute number, then the values).
            If nProbe > 0 Then
                pv(s, 1) = (d - 1) * STEPS_PER_DAY + s
                For k = 1 To nProbe
                    pv(s, k + 1) = ws.Range(probes(k - 1)).Value2
                Next k
            End If
            ' Optional: append the whole state block to the csv file every FULL_EVERY minutes.
            If FULL_EVERY > 0 Then
                If s Mod FULL_EVERY = 0 Then WriteField csvNo, st, (d - 1) * STEPS_PER_DAY + s
            End If
            ' Every 60 minutes: show progress in the status bar. DoEvents lets Excel react,
            ' which is also how it sees the Esc key.
            If s Mod 60 = 0 Then
                Application.StatusBar = "Day " & d & " of " & TOTAL_DAYS & _
                    "  -  minute " & s & " of " & STEPS_PER_DAY
                DoEvents
            End If
        Next s
        ' ---- end of the day: close the csv file, save the day, write the log line ---------------
        mStage = "saving day " & d
        If csvNo <> 0 Then
            Close #csvNo
            csvNo = 0
            ' ".../Day_001.xlsx.csv.tmp" becomes ".../Day_001_field.csv" (5 characters ".xlsx" are cut off)
            Name DayFile(outDir, d) & ".csv.tmp" As Left$(DayFile(outDir, d), Len(DayFile(outDir, d)) - 5) & "_field.csv"
        End If
        SaveDay st, outDir, d, pv, probes, nProbe
        mStage = "writing log"
        AppendLog outDir, "Day " & d & " done, " & Format(Timer - t0, "0") & " s"
    Next d

    MsgBox "Simulation finished: " & TOTAL_DAYS & " days in " & outDir, vbInformation
    GoTo Cleanup

    ' ---- error handler: reached by any error and by Esc ----------------------------------------
Failed:
    ' Error 18 is "user interrupt" (Esc). The current day is lost, the finished days stay on disk.
    If Err.Number = 18 Then
        MsgBox "Stopped by user. Completed days are saved; run again to resume.", vbExclamation
    Else
        ' Any other error: show the number, the text, where the macro was (mStage) and the folder.
        MsgBox "Error " & Err.Number & ": " & Err.Description & vbCrLf & _
            "Stage: " & mStage & vbCrLf & "Folder: " & outDir, vbCritical
    End If
    ' ---- cleanup: always runs, after a normal end, after Esc and after an error ----------------
    ' (the error handler continues into Cleanup because there is no GoTo or Exit between them)
Cleanup:
    If csvNo <> 0 Then Close #csvNo      ' do not leave the csv file locked
    Application.Calculation = oldCalc    ' give Excel back to the user as it was
    Application.EnableEvents = True
    Application.ScreenUpdating = True
    Application.StatusBar = False
End Sub

' The folder for the output: <workbook folder>\daily_output.
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

' The path of the file of day dayNo, e.g. C:\...\daily_output\Day_007.xlsx
Private Function DayFile(outDir As String, dayNo As Long) As String
    DayFile = outDir & "\" & "Day_" & Format(dayNo, "000") & ".xlsx"
End Function

' Restart helper: the number of the newest finished day (0 if there is none).
' It counts down from TOTAL_DAYS, so the first file found is the newest. SaveDay renames its
' file only when it is complete, so a half-written day never counts as finished.
Private Function LastCompletedDay(outDir As String) As Long
    Dim d As Long
    For d = TOTAL_DAYS To 1 Step -1
        If Dir(DayFile(outDir, d)) <> "" Then LastCompletedDay = d: Exit Function
    Next d
End Function

' Restart helper: open the Day file read-only, copy its state block into the state block of the
' model sheet, close it without saving. Both ranges have the same address (STATE_ADDR).
Private Sub LoadState(st As Range, outDir As String, dayNo As Long)
    Dim wb As Workbook
    Set wb = Workbooks.Open(DayFile(outDir, dayNo), UpdateLinks:=0, ReadOnly:=True)
    st.Value2 = wb.Worksheets(1).Range(STATE_ADDR).Value2
    wb.Close SaveChanges:=False
End Sub

' Write one finished day to Day_NNN.xlsx:
'   sheet "Day d" : A1:B2 hold the day and minute number, the state block is at its normal addresses
'   sheet "Minutes": one row per minute: minute number and the probe cells (only if PROBE_CELLS is set)
' st = the state block, pv = the probe table of the day, probes = their addresses.
Private Sub SaveDay(st As Range, outDir As String, dayNo As Long, pv() As Variant, probes() As String, nProbe As Long)
    Dim wb As Workbook, tmp As String, k As Long
    tmp = DayFile(outDir, dayNo) & ".tmp"      ' rename at the end so a half-written file never counts as done
    ' A new workbook with one sheet. The state is written at the same addresses as in the model sheet,
    ' so the Day file can be compared cell by cell with the Fortran field file.
    Set wb = Workbooks.Add(xlWBATWorksheet)
    With wb.Worksheets(1)
        .Name = "Day " & dayNo
        .Range("A1").Value2 = "Day"
        .Range("B1").Value2 = dayNo
        .Range("A2").Value2 = "Minute"
        .Range("B2").Value2 = dayNo * STEPS_PER_DAY
        .Range(STATE_ADDR).Value2 = st.Value2
    End With
    ' Second sheet: the probe values of every minute of the day (header in row 1, 1440 rows below it).
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
    ' Save under the temporary name (no "overwrite?" question), close, then rename to the final name.
    Application.DisplayAlerts = False
    wb.SaveAs Filename:=tmp, FileFormat:=xlOpenXMLWorkbook
    Application.DisplayAlerts = True
    wb.Close SaveChanges:=False
    Name tmp As DayFile(outDir, dayNo)
End Sub

' Optional output (FULL_EVERY > 0): append the whole state block to an open csv file. A line
' "# minute N" is followed by one text line per sheet row, values separated by commas.
Private Sub WriteField(fileNo As Integer, st As Range, minuteNo As Long)
    Dim v As Variant, r As Long, c As Long, parts() As String
    ' reading the range into an array once is much faster than reading cell by cell
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

' Add one line "date time  message" to run_log.txt (for example: "Day 3 done, 312 s").
Private Sub AppendLog(outDir As String, msg As String)
    Dim f As Integer
    f = FreeFile
    Open outDir & "\" & "run_log.txt" For Append As #f
    Print #f, Format(Now, "yyyy-mm-dd hh:nn:ss") & "  " & msg
    Close #f
End Sub
