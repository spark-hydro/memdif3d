# Docker on Windows: step by step

This page takes you from a Windows computer without any tools to a finished model run and its pictures. You need no programming, no compiler and no Fortran. Everything runs inside a Docker container that holds the program and the plotting tools. It takes about 30 minutes the first time, most of it downloads.

What you do, in order:

1. install Docker Desktop
2. get the memdif3d image
3. make a folder for your model and for your runs
4. set up the model (the input files)
5. run it
6. look at the results

!!! note "Native program instead"
    If you only want to run the model and do not need the plotting tools, the release page has a Windows program, `memdif3d.exe`, that needs no Docker. This page is for the full set: the model, the plots and the animations in one image. The general description of the image is on the page [Run with Docker](docker.md).

## 1. Install Docker Desktop

You need Windows 10 (version 22H2 or newer) or Windows 11, 64 bit, with virtualization switched on (it is on by default on most computers) and administrator rights for the installation.

1. Download **Docker Desktop for Windows** from <https://www.docker.com/products/docker-desktop/> and start the installer.
2. Keep the option **Use WSL 2 instead of Hyper-V** ticked. Restart the computer when the installer asks.
3. Start **Docker Desktop** from the start menu and accept the terms. Check that the licence conditions of Docker Desktop fit your institution; for education and personal use it is free.
4. Wait until the whale icon in the taskbar shows that the engine is running (the Docker Desktop window says *Engine running*).

Check the installation. Open **PowerShell** (start menu, type *PowerShell*) and type:

```powershell
docker --version
```

```powershell
docker run --rm hello-world
```

The second command downloads a tiny test image and prints *Hello from Docker!*. If it does, Docker works.

!!! tip "Linux containers"
    Docker Desktop must be in **Linux containers** mode (the default). Right-click the whale icon: if the menu says *Switch to Linux containers*, click it. The memdif3d image is a Linux image.

## 2. Get memdif3d

Download the image once (about 530 MB):

```powershell
docker pull ghcr.io/spark-hydro/memdif3d:latest
```

Check it:

```powershell
docker run --rm ghcr.io/spark-hydro/memdif3d --version
```

You should see the banner with the version number. The image holds the program, the example model and all plotting tools. To update later, run the `pull` command again.

## 3. Make folders for your model and your runs

Make one folder that holds everything, with one folder for the model (input files) and one for each run (output files). The program writes its output into the folder where it is started, so a folder per run keeps the results apart:

```text
C:\memdif3d\
    mymodel\      the input files of your model (rm.nam, rm.dis, ...)
    run1\         the output of the first run
    run2\         the output of the next run
```

In PowerShell:

```powershell
mkdir C:\memdif3d\run1
```

## 4. Set up the model

### 4.1 Start from the example

The image contains the example model (the Reduced_Matrix case). Copy it into your folder:

```powershell
cd C:\memdif3d
```

```powershell
docker run --rm -v ${PWD}:/work ghcr.io/spark-hydro/memdif3d cp -r /opt/memdif3d/data/reduced_matrix /work/mymodel
```

`dir C:\memdif3d\mymodel` now lists ten files, `rm.nam`, `rm.tdis`, `rm.dis`, `rm.ic`, `rm.dsp`, `rm.mst`, `rm.src`, `rm.adv`, `rm.bnd` and `rm.oc`. Docker Desktop may ask to share the folder with Docker the first time: allow it.

This command shows how Docker links a folder. The part `-v ${PWD}:/work` means: *the folder I am in now (`${PWD}`) appears inside the container as `/work`*. Everything the container writes into `/work` lands in that Windows folder, and it stays there after the container has ended (`--rm` only deletes the container itself). In the older `cmd` window use `%cd%` instead of `${PWD}`.

### 4.2 Change the model

The input files are small text files. Open them with **Notepad** or **Visual Studio Code**, not with Word. The most common changes:

| File | What to change |
|---|---|
| `rm.tdis` | `NPERIODS` (days), `STEPS_PER_PERIOD` (steps per day), `STEP_LENGTH` (minutes) |
| `rm.dsp`, `rm.mst` | diffusion, tortuosity, porosity, length, bulk density, sorption Kd |
| `rm.src` | source volume and start concentration, the `FACES` map (membrane, holes) |
| `rm.bnd` | the rules of the outer boundary |
| `rm.oc` | which files to write, the probe cells, the minutes output |

Every file is described in [Input files](INPUT_SPEC.md), and [Build your own model](build-your-model.md) goes through the changes one by one. Windows line endings in these files are fine.

A membrane with holes can be made by a script. This copies the model and punches holes:

```powershell
docker run --rm -v ${PWD}:/work ghcr.io/spark-hydro/memdif3d make_holes.py /work/mymodel /work/mymodel_holes --pitch 3 --size 2 --closed
```

### 4.3 Write every minute of a time window (optional)

To write the concentration of the whole box at every minute, add this block at the end of `rm.oc`:

```text
BEGIN MINUTES
  DIGITS 6
  FROM 0
  TO 120
  FORMAT CSV
END MINUTES
```

This gives `day_001.csv` with the first two hours. A whole day of the whole box is about 640 MB, so choose a window. The format is described in [Output files](outputs.md).

## 5. Run the model

Go to the run folder and start the program. The model folder is linked **read-only** as `/model`, and the run folder as `/work`, where the output goes:

```powershell
cd C:\memdif3d\run1
```

```powershell
docker run --rm -v ${PWD}:/work -v C:\memdif3d\mymodel:/model:ro ghcr.io/spark-hydro/memdif3d /model/rm.nam
```

The screen shows the banner, the model size, the stability check and one line for every finished day, ending with *Normal termination*. The 28 days of the example take a few seconds. `C:\memdif3d\run1` now holds the results: a `field_NNN.csv` and a `probes_NNN.csv` for every day and the restart files `restart.dat.1` and `restart.dat.2`.

Useful options go after the path of the name file:

| Option | Meaning |
|---|---|
| `--nperiods 2` | run only 2 days |
| `--steps-per-period 10` | 10 steps per day (a quick test: `--nperiods 1 --steps-per-period 10`) |
| `--fresh` | start again from the initial state and ignore the restart files |
| `--snapshot-every 60` | also write the whole box every 60 steps (one `snap_*.csv` file each) |

If a run is interrupted, give the same command again in the same run folder: it continues after the last finished day. To start over, add `--fresh`, or use a new run folder.

!!! tip "Shorter commands"
    In PowerShell you can store the long parts in variables for the session and reuse them:

    ```powershell
    $img = "ghcr.io/spark-hydro/memdif3d"
    $model = "C:\memdif3d\mymodel"
    docker run --rm -v ${PWD}:/work -v ${model}:/model:ro $img /model/rm.nam --nperiods 2
    ```

    A command that does not fit one line can be continued on the next line with a backtick (`` ` ``) at the end of the line.

## 6. Look at the results

The plotting tools run in the same image. Start them from the run folder, with the same two links. The result files are written into the run folder; open them from Windows Explorer.

### 3D animation in the browser

```powershell
docker run --rm -v ${PWD}:/work -v C:\memdif3d\mymodel:/model:ro ghcr.io/spark-hydro/memdif3d animate_3d.py . --nam /model/rm.nam --log --out solute3d.html
```

Double-click `solute3d.html` in the run folder. It opens in your browser: drag to rotate while the animation plays, scroll to zoom, and use the Play button and the slider. `--log` uses a logarithmic colour scale, so the small concentrations far from the membrane stay visible.

### GIF with a top view and a column plane

```powershell
docker run --rm -v ${PWD}:/work -v C:\memdif3d\mymodel:/model:ro ghcr.io/spark-hydro/memdif3d animate_field.py . --nam /model/rm.nam --ilay 15 --icol 3 --out views.gif
```

`--ilay 15` is the top view of layer 15, the middle of the source (rows × columns). `--icol 3` is the plane 3 mm from the membrane (rows × layers). `--irow 22` would give the section through row 22 (layers × columns). Without these options you get two default views. Open `views.gif` in the browser or in any picture viewer.

### Pictures of the model itself

```powershell
docker run --rm -v ${PWD}:/work -v C:\memdif3d\mymodel:/model:ro ghcr.io/spark-hydro/memdif3d plot_domain_3d.py /model/rm.nam --out domain3d.html
```

This draws the grid, the membrane and the source from the input files only, before you run anything.

### Animating the minutes output

If you wrote day files (section 4.3), use them as frames and choose a time window:

```powershell
docker run --rm -v ${PWD}:/work -v C:\memdif3d\mymodel:/model:ro ghcr.io/spark-hydro/memdif3d animate_3d.py . --nam /model/rm.nam --log --pattern "day_*.csv" --every 5 --from 0 --to 120 --out first2h.html
```

`--every 5` keeps every fifth minute, `--from` and `--to` give the time window in minutes (1 day = 1440). Keep `probes_NNN.csv` next to the day files: the concentration of the source is read from it. The options of all tools are in [Tools](tools.md).

## When something goes wrong

| Message or problem | What to do |
|---|---|
| `error during connect` or `cannot connect to the Docker daemon` | Docker Desktop is not running. Start it and wait for *Engine running*. |
| `no matching manifest for windows/amd64` | Docker Desktop is in Windows containers mode. Right-click the whale icon, *Switch to Linux containers*. |
| `[memdif3d] cannot find the model file 'x.nam'` | The path or the link is wrong. The path of the name file is read **inside** the container: `/model/rm.nam` when the model folder is linked as `/model`. Check that the folder after `-v` exists and holds `rm.nam`. |
| the output folder is empty | The folder linked as `/work` is not where you look. Output goes to the folder that is linked as `/work`; check `-v ${PWD}:/work` and which folder you started in. |
| `${PWD}` is not understood | You are in the old `cmd` window. Use PowerShell, or write `%cd%` instead of `${PWD}`. |
| a path with spaces fails | Put the whole `-v` argument in double quotes, for example `-v "C:\my models\run1:/work"`. |
| Docker asks to share a drive or folder | Allow it. In Docker Desktop: *Settings, Resources, File sharing*. |
| the first start takes minutes | The first pull downloads about 530 MB and Docker Desktop starts its Linux engine. Later runs start in a second. |
| the minutes output is slow | Writing hundreds of megabytes through a linked Windows folder is slower than a native disk. Use a time window (`FROM`, `TO`) or fewer layers (`LAYERS`). |

## Updating and cleaning up

```powershell
docker pull ghcr.io/spark-hydro/memdif3d:latest
```

fetches the newest version. `docker images` lists the images on your computer and `docker image rm ghcr.io/spark-hydro/memdif3d:latest` deletes one. Your model and result folders are ordinary Windows folders and are not touched.
