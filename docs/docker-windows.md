# Docker on Windows: step by step

This page takes you from a Windows computer without any tools to a finished model run and its pictures. You need no programming, no compiler and no Fortran. Everything runs inside a Docker container that holds the program and the plotting tools, and a small helper file, `memdif.cmd`, turns the long Docker commands into short ones such as `memdif run`. It takes about 30 minutes the first time, most of it downloads.

What you do, in order:

1. install Docker Desktop
2. get the memdif3d image
3. make folders and get the helper
4. set up the model (the input files)
5. run it
6. look at the results (an interactive viewer, 3D pages and GIFs)

!!! note "Native program instead"
    If you only want to run the model and do not need the plotting tools, the release page has a Windows program, `memdif3d.exe`, that needs no Docker. This page is for the full set: the model, the viewer, the plots and the animations in one image. The general description of the image is on the page [Run with Docker](docker.md).

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

!!! tip "Linux containers (usually nothing to do)"
    The memdif3d image is a Linux image, so Docker Desktop must be in **Linux containers** mode. This is the default, and it is the only mode when Docker uses WSL 2 (step 1), so most people have nothing to do here. To check, type in PowerShell:

    ```powershell
    docker info --format "{{.OSType}}"
    ```

    If it prints `linux`, you are done. Only if it prints `windows`, right-click the whale icon in the taskbar (it may be hidden behind the small arrow `^` near the clock) and choose **Switch to Linux containers**. If the menu says *Switch to Windows containers* instead, Docker is already in Linux mode, so do not click it.

## 2. Get memdif3d

Download the image once (about 530 MB):

```powershell
docker pull ghcr.io/spark-hydro/memdif3d:latest
```

Check it:

```powershell
docker run --rm ghcr.io/spark-hydro/memdif3d --version
```

You should see the banner with the version number. The image holds the program, the example model and all plotting tools. To update later, run the `pull` command again (or `..\memdif.cmd update` after step 3).

## 3. Make folders and get the helper

Make one folder that holds everything, with one folder for the model (input files) and one for each run (output files). The program writes its output into the folder where it is started, so a folder per run keeps the results apart:

```text
C:\Users\<your name>\memdif3d\        (in PowerShell: $HOME\memdif3d)
    memdif.cmd    the helper with the short commands
    mymodel\      the input files of your model (rm.nam, rm.dis, ...)
    run1\         the output of the first run
    run2\         the output of the next run
```

`$HOME` is your user folder, `C:\Users\<your name>` (type `echo $HOME` to see it). A folder there is your own, is not synced by OneDrive and does not clutter the drive root. In PowerShell:

```powershell
mkdir $HOME\memdif3d\run1
```

```powershell
cd $HOME\memdif3d
```

The helper is inside the image. Copy it into your `memdif3d` folder:

```powershell
docker run --rm -v "${PWD}:/work" ghcr.io/spark-hydro/memdif3d cp /opt/memdif3d/scripts/memdif.cmd /work/
```

Docker Desktop may ask to share the folder the first time: allow it. The part `-v "${PWD}:/work"` links the folder you are in (`${PWD}`) into the container as `/work`, so a file the container writes there is a normal Windows file. In the older `cmd` window write `%cd%` instead of `${PWD}`.

From now on you work in a run folder and call the helper one level up. Try it:

```powershell
cd $HOME\memdif3d\run1
```

```powershell
..\memdif.cmd help
```

It lists the commands: `run`, `view`, `domain`, `anim3d`, `gif`, `tool`, `newmodel`, `update` and `version`. Every command prints the long Docker command it runs, so you can see what happens (section *Under the hood*).

## 4. Set up the model

### 4.1 Start from the example

```powershell
..\memdif.cmd newmodel
```

This copies the example model (the Reduced_Matrix case) from the image to `$HOME\memdif3d\mymodel`. `dir $HOME\memdif3d\mymodel` lists ten files: `rm.nam`, `rm.tdis`, `rm.dis`, `rm.ic`, `rm.dsp`, `rm.mst`, `rm.src`, `rm.adv`, `rm.bnd` and `rm.oc`.

### 4.2 Check the model before you run it

```powershell
..\memdif.cmd domain
```

writes `domain.html` into the run folder. Double-click it: it shows the 3D box, the source, the membrane faces and the start state (see section 6 for how to use the page). This is the quickest way to see that a change in the input files did what you meant.

### 4.3 Change the model

The input files are small text files. Open them with **Notepad** or **Visual Studio Code**, not with Word. The most common changes:

| File | What to change |
|---|---|
| `rm.tdis` | `NPERIODS` (days), `STEPS_PER_PERIOD` (steps per day), `STEP_LENGTH` (minutes) |
| `rm.dsp`, `rm.mst` | diffusion, tortuosity, porosity, length, bulk density, sorption Kd |
| `rm.src` | source volume and start concentration, the `FACES` map (membrane, holes) |
| `rm.bnd` | the rules of the outer boundary |
| `rm.oc` | which files to write, the probe cells, the minutes output |

Every file is described in [Input files](INPUT_SPEC.md), and [Build your own model](build-your-model.md) goes through the changes one by one. Windows line endings in these files are fine.

A membrane with holes can be made by a script. This copies the model and punches holes into the copy `holes`, which appears in the run folder:

```powershell
..\memdif.cmd tool make_holes.py /model /work/holes --pitch 3 --size 2 --closed
```

Move the folder `holes` to `$HOME\memdif3d\holes`. To run the copy instead of `mymodel`, give its folder once for the PowerShell window:

```powershell
$env:MEMDIF_MODEL = "$HOME\memdif3d\holes"
```

### 4.4 Write every minute of a time window (optional)

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

### 4.5 Use a model that is somewhere else

The model does not have to be in `mymodel`. Point the helper at any folder, and name the main name file if the folder holds several `.nam` files. For one PowerShell window:

```powershell
$env:MEMDIF_MODEL = "D:\projects\my_other_model"
$env:MEMDIF_NAM = "case2.nam"
```

Then `..\memdif.cmd run` runs `case2.nam` from that folder. Without `MEMDIF_NAM` the helper takes the only `.nam` file of the folder (or the first one). Give the **whole model folder**, not only the name file: the name file lists the other input files relative to its own folder, so they must be next to it. The results still go to the run folder you are in.

Without the helper the same thing is one `docker run`, with the folder linked as `/model` and the path of the name file inside the container:

```powershell
docker run --rm -v "${PWD}:/work" -v "D:\projects\my_other_model:/model:ro" ghcr.io/spark-hydro/memdif3d /model/case2.nam
```

## 5. Run the model

Go to the run folder and run:

```powershell
cd $HOME\memdif3d\run1
```

```powershell
..\memdif.cmd run
```

The screen shows the banner, the model size, the stability check and one line for every finished day, ending with *Normal termination*. The 28 days of the example take a few seconds. The run folder now holds the results: a `field_NNN.csv` and a `probes_NNN.csv` for every day and the restart files `restart.dat.1` and `restart.dat.2`.

Options of the program go after `run`:

| Option | Meaning |
|---|---|
| `--nperiods 2` | run only 2 days |
| `--steps-per-period 10` | 10 steps per day (a quick test: `--nperiods 1 --steps-per-period 10`) |
| `--fresh` | start again from the initial state and ignore the restart files |
| `--snapshot-every 60` | also write the whole box every 60 steps (one `snap_*.csv` file each) |

For example `..\memdif.cmd run --nperiods 2 --fresh`. If a run is interrupted, give the same command again in the same run folder: it continues after the last finished day. To start over, add `--fresh`, or use a new run folder.

## 6. Look at the results

Start the tools from the run folder. Each command writes one file into it; open the file from Windows Explorer.

### Interactive viewer: the domain, and any layer, row or column

```powershell
..\memdif.cmd view
```

Double-click `viewer.html`. The 3D model is on the left and the concentration on a plane of your choice on the right. In the bar on top choose **Plane**: *Layer* (the top view, rows × columns), *Row* (a section, layers × columns) or *Column* (a plane at one distance from the membrane, rows × layers), then the **number** of the layer, row or column with the slider. The chosen plane is drawn inside the 3D box. Use the **Time** slider or **Play** to animate the plane. Nothing runs again when you change the plane; the page holds the data. The frames are the day files of the run (`field_001.csv`, `field_002.csv`, ...).

For finer time steps use the minutes output (section 4.4) and choose a window. The page grows with the number of frames:

```powershell
..\memdif.cmd view --pattern "day_*.csv" --every 5 --from 0 --to 120 --out first2h.html
```

### 3D animation in the browser

```powershell
..\memdif.cmd anim3d
```

writes `solute3d.html`: drag to rotate while the animation plays, scroll to zoom. It uses a logarithmic colour scale, so the small concentrations far from the membrane stay visible. To show only part of the box, add `--ilay 15` (one layer through the middle of the source), `--icol 3` (the plane 3 mm from the membrane) or a range such as `--ilay 15-29`.

### GIF with a top view and a column plane

```powershell
..\memdif.cmd gif --ilay 15 --icol 3
```

writes `views.gif`: `--ilay 15` is the top view of layer 15 (rows × columns), `--icol 3` the plane 3 mm from the membrane (rows × layers), and `--irow 22` would give the section through row 22. Open it in the browser or a picture viewer.

### The time period and the frames

All animation commands (`view`, `anim3d`, `gif`) take the same selection of frames:

| Option | Meaning |
|---|---|
| `--pattern "day_*.csv"` | use the day files of the minutes output (default `field_*.csv`, one per day) |
| `--every 60` | keep every 60th minute (one frame an hour) |
| `--from 0 --to 120` | only minutes 0 to 120 (1 day = 1440) |
| `--out name.html` | name of the output file |

Keep `probes_NNN.csv` next to the day files: the concentration of the source is read from it. The options of all tools are in [Tools](tools.md).

## Under the hood

Each `memdif` command is one `docker run`. It links two folders into the container: the model folder, read-only, as `/model`, and the run folder as `/work`, where the output goes. For instance `..\memdif.cmd run --nperiods 2` is the same as

```powershell
docker run --rm -v "${PWD}:/work" -v "${HOME}\memdif3d\mymodel:/model:ro" ghcr.io/spark-hydro/memdif3d /model/rm.nam --nperiods 2
```

The helper prints that line for every command. `..\memdif.cmd tool script.py ...` runs any tool of the image the same way; the scripts are listed in [Tools](tools.md). Set `MEMDIF_MODEL` to use another model folder and `MEMDIF_IMAGE` to use another image. The image, the model and the results stay apart: the image never changes, and all your files are ordinary Windows folders.

## When something goes wrong

| Message or problem | What to do |
|---|---|
| `error during connect` or `cannot connect to the Docker daemon` | Docker Desktop is not running. Start it and wait for *Engine running*. |
| `no matching manifest for windows/amd64` | Docker Desktop is in Windows containers mode. Check with `docker info --format "{{.OSType}}"`; if it says `windows`, right-click the whale icon and choose *Switch to Linux containers*. |
| `'..\memdif.cmd' is not recognized` | Check the folder you are in (`pwd`) and that `memdif.cmd` is in your `memdif3d` folder (step 3). |
| `memdif: no .nam file in ...` | The model folder is empty or elsewhere: run `..\memdif.cmd newmodel`, or set `MEMDIF_MODEL`. |
| `[memdif3d] cannot find the model file` | The model folder has no `.nam` file of that name; check `dir $HOME\memdif3d\mymodel`. |
| the output folder is empty | Output goes to the folder you start the command in. Start it in the run folder. |
| `${PWD}` is not understood | You are in the old `cmd` window. Use PowerShell, or write `%cd%` instead of `${PWD}`. |
| a path with spaces fails | Keep the quotes around the `-v` arguments, as in the commands of this page: `-v "${PWD}:/work"`. The helper `memdif.cmd` already does this. |
| Docker asks to share a drive or folder | Allow it. In Docker Desktop: *Settings, Resources, File sharing*. |
| the first start takes minutes | The first pull downloads about 530 MB and Docker Desktop starts its Linux engine. Later runs start in a second. |
| the minutes output is slow | Writing hundreds of megabytes through a linked Windows folder is slower than a native disk. Use a time window (`FROM`, `TO`) or fewer layers (`LAYERS`). |

## Updating and cleaning up

```powershell
..\memdif.cmd update
```

fetches the newest image. To get the newest helper too, copy it again with the command of step 3. `docker images` lists the images on your computer and `docker image rm ghcr.io/spark-hydro/memdif3d:latest` deletes one. Your model and result folders are ordinary Windows folders and are not touched.

On Linux or macOS use `memdif.sh` (in `/opt/memdif3d/scripts` of the image) the same way: `../memdif.sh run`.
