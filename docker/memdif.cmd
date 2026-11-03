@echo off
rem memdif: short commands for the memdif3d Docker image (Windows; docker\memdif.sh is the Linux/macOS version).
rem
rem Put this file next to your model folder (default: mymodel next to this file) and run it from the run folder:
rem    cd C:\memdif3d\run1
rem    ..\memdif run
rem The model folder is linked read-only as /model, the current folder as /work (the output goes there).
rem Set MEMDIF_MODEL to use another model folder, MEMDIF_IMAGE to use another image.
rem Every command prints the long docker command it runs. Works in PowerShell and in cmd.
setlocal EnableExtensions
if "%MEMDIF_IMAGE%"=="" (set "IMG=ghcr.io/spark-hydro/memdif3d:latest") else (set "IMG=%MEMDIF_IMAGE%")
if "%MEMDIF_MODEL%"=="" (set "MODEL=%~dp0mymodel") else (set "MODEL=%MEMDIF_MODEL%")
set "CMD=%~1"
if "%CMD%"=="" goto help
if /i "%CMD%"=="help" goto help
if /i "%CMD%"=="-h" goto help
if /i "%CMD%"=="--help" goto help
shift
set "REST="
:collect
if "%~1"=="" goto collected
set REST=%REST% %1
shift
goto collect
:collected
if /i "%CMD%"=="update" goto update
if /i "%CMD%"=="newmodel" goto newmodel
if /i "%CMD%"=="tool" goto tool
if /i "%CMD%"=="version" goto version
set "NAM="
for %%f in ("%MODEL%\*.nam") do if not defined NAM set "NAM=%%~nxf"
if not defined NAM goto nonam
if /i "%CMD%"=="run" goto run
if /i "%CMD%"=="view" goto view
if /i "%CMD%"=="domain" goto domain
if /i "%CMD%"=="anim3d" goto anim3d
if /i "%CMD%"=="gif" goto gif
echo memdif: unknown command "%CMD%"
goto help

:run
call :dock /model/%NAM%%REST%
exit /b %errorlevel%
:view
call :dock make_viewer.py . --nam /model/%NAM% --out viewer.html%REST%
exit /b %errorlevel%
:domain
call :dock make_viewer.py --nam /model/%NAM% --out domain.html%REST%
exit /b %errorlevel%
:anim3d
call :dock animate_3d.py . --nam /model/%NAM% --log --out solute3d.html%REST%
exit /b %errorlevel%
:gif
call :dock animate_field.py . --nam /model/%NAM% --out views.gif%REST%
exit /b %errorlevel%
:tool
call :dock%REST%
exit /b %errorlevel%
:version
call :dock --version
exit /b %errorlevel%
:update
docker pull %IMG%
exit /b %errorlevel%
:newmodel
if exist "%~dp0mymodel" goto exists
docker run --rm -v "%~dp0.":/work %IMG% cp -r /opt/memdif3d/data/reduced_matrix /work/mymodel
echo model copied to %~dp0mymodel
exit /b %errorlevel%
:exists
echo memdif: %~dp0mymodel exists already
exit /b 2
:nonam
echo memdif: no .nam file in %MODEL%
echo (set MEMDIF_MODEL to your model folder, or run: memdif newmodel)
exit /b 2

:dock
echo + docker run --rm -v "%CD%":/work -v "%MODEL%":/model:ro %IMG% %*
docker run --rm -v "%CD%":/work -v "%MODEL%":/model:ro %IMG% %*
exit /b %errorlevel%

:help
echo memdif COMMAND [options]      run it in the folder where the results should go
echo.
echo   run [options]       run the model (options: --nperiods 2, --fresh, --snapshot-every 60, ...)
echo   view [options]      interactive viewer: viewer.html (3D domain and any layer, row or column)
echo   domain [options]    viewer of the model only, before a run: domain.html
echo   anim3d [options]    3D animation: solute3d.html
echo   gif [options]       GIF with a top view and a column plane: views.gif
echo   tool script.py ...  any tool of the image, for example: tool make_holes.py /model /work/holes --pitch 3 --size 2
echo   newmodel            copy the example model to mymodel next to this file
echo   update              download the newest image
echo   version             show the version of the program
echo.
echo The options after the command are those of the program or tool (see the manual), for example:
echo   memdif view --pattern "day_*.txt" --every 60 --from 0 --to 360
exit /b 0
