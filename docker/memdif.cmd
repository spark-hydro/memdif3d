@echo off
rem memdif: short commands for the memdif3d Docker image (Windows; docker\memdif.sh is the Linux/macOS version).
rem
rem Put this file in a folder that is on your PATH (the guide shows how), then, in the folder where the results should go:
rem    memdif -m D:\projects\mymodel run
rem -m is the model: a folder (the .nam file in it is used) or the path of the .nam file itself. Instead of -m you can
rem set MEMDIF_MODEL once per window. The model is linked read-only as /model, the current folder as /work.
rem MEMDIF_NAM chooses the name file when a model folder holds several .nam files, MEMDIF_IMAGE uses another image.
rem Every command prints the long docker command it runs. Works in PowerShell and in cmd.
setlocal EnableExtensions
set "SELF=%~f0"
set "HERE=%~dp0"
if "%MEMDIF_IMAGE%"=="" (set "IMG=ghcr.io/spark-hydro/memdif3d:latest") else (set "IMG=%MEMDIF_IMAGE%")
:opts
if /i "%~1"=="-m" goto setmodel
if /i "%~1"=="--model" goto setmodel
goto opts_done
:nopath
echo memdif: -m needs a path
exit /b 2
:setmodel
if "%~2"=="" goto nopath
set "MEMDIF_MODEL=%~2"
shift
shift
goto opts
:opts_done
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
set "WORK=%CD%"
if "%WORK:~-1%"=="\" set "WORK=%WORK:~0,-1%"
set "MODEL="
set "NAM=%MEMDIF_NAM%"
if "%MEMDIF_MODEL%"=="" goto modeldone
set "MODEL=%MEMDIF_MODEL%"
if "%MODEL:~-1%"=="\" set "MODEL=%MODEL:~0,-1%"
if /i not "%MODEL:~-4%"==".nam" goto modeldone
for %%f in ("%MODEL%") do set "NAM=%%~nxf"
for %%f in ("%MODEL%") do set "MODEL=%%~dpf"
call :stripslash
:modeldone
if /i "%CMD%"=="update" goto update
if /i "%CMD%"=="newmodel" goto newmodel
if /i "%CMD%"=="tool" goto tool
if /i "%CMD%"=="version" goto version
if not defined MODEL goto nomodel
if not exist "%MODEL%\" goto nofolder
if defined NAM goto havenam
for %%f in ("%MODEL%\*.nam") do if not defined NAM set "NAM=%%~nxf"
:havenam
if not defined NAM goto nonam
if /i "%CMD%"=="run" goto run
if /i "%CMD%"=="view" goto view
if /i "%CMD%"=="domain" goto domain
if /i "%CMD%"=="anim3d" goto anim3d
if /i "%CMD%"=="gif" goto gif
echo memdif: unknown command "%CMD%"
goto help

:stripslash
if "%MODEL:~-1%"=="\" set "MODEL=%MODEL:~0,-1%"
exit /b 0

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
rem memdif update: pull the newest image, then replace this helper file by the one inside the image.
rem The copy and the exit are on ONE line: cmd reads a whole line before it runs it, so it never reads on in the new file.
docker pull %IMG%
if errorlevel 1 exit /b 1
docker run --rm -v "%HERE%.":/work %IMG% cp /opt/memdif3d/scripts/memdif.cmd /work/memdif.cmd.new
if errorlevel 1 (echo memdif: image updated, but the helper could not be refreshed & exit /b 1)
copy /y "%HERE%memdif.cmd.new" "%SELF%" >nul & del "%HERE%memdif.cmd.new" & echo memdif: image and helper are up to date & exit /b 0
:newmodel
rem memdif newmodel [name]: copy the example model to the folder [name] (default mymodel) in the current folder
set "NEWNAME=%~1"
if "%NEWNAME%"=="" set "NEWNAME=mymodel"
if exist "%WORK%\%NEWNAME%" goto exists
docker run --rm -v "%WORK%":/work %IMG% cp -r /opt/memdif3d/data/reduced_matrix /work/%NEWNAME%
echo model copied to %WORK%\%NEWNAME%
exit /b %errorlevel%
:exists
echo memdif: %WORK%\%NEWNAME% exists already
exit /b 2
:nomodel
echo memdif: no model given. Use  memdif -m PATH %CMD%  (PATH = model folder or .nam file),
echo or set it once for this window:  $env:MEMDIF_MODEL = "PATH"
exit /b 2
:nofolder
echo memdif: the model folder %MODEL% does not exist
exit /b 2
:nonam
echo memdif: no .nam file in %MODEL%
exit /b 2

:dock
set "MNT="
if defined MODEL set "MNT=-v "%MODEL%":/model:ro"
echo + docker run --rm -v "%WORK%":/work %MNT% %IMG% %*
docker run --rm -v "%WORK%":/work %MNT% %IMG% %*
exit /b %errorlevel%

:help
echo memdif [-m MODEL] COMMAND [options]    run it in the folder where the results should go
echo.
echo   -m MODEL            the model: a folder with the input files, or the path of its .nam file
echo                       (or set MEMDIF_MODEL once per window)
echo   run [options]       run the model (options: --nperiods 2, --fresh, --snapshot-every 60, ...)
echo   view [options]      interactive viewer: viewer.html (3D domain and any layer, row or column)
echo   domain [options]    viewer of the model only, before a run: domain.html
echo   anim3d [options]    3D animation: solute3d.html
echo   gif [options]       GIF with a top view and a column plane: views.gif
echo   tool script.py ...  any tool of the image, for example: tool make_holes.py /model /work/holes --pitch 3 --size 2
echo   newmodel [name]     copy the example model to a new folder (default mymodel) in the current folder
echo   update              download the newest image and refresh this helper file
echo   version             show the version of the program
echo.
echo The options after the command are those of the program or tool (see the manual), for example:
echo   memdif -m D:\projects\mymodel view --pattern "day_*.txt" --every 60 --from 0 --to 360
exit /b 0
