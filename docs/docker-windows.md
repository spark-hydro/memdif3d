# Docker on Windows: step by step

This page takes you from a Windows computer without any tools to a finished model run and its pictures. You need no programming, no compiler and no Fortran. Everything runs inside a Docker container that holds the program and the plotting tools, and a small helper file, `memdif.cmd`, turns the long Docker commands into short ones such as `memdif run`. It takes about 30 minutes the first time, most of it downloads.

What you do, in order:

1. install Docker Desktop
2. get the memdif3d image
3. install the helper (once)
4. give the path of your model and set it up
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

You should see the banner with the version number. The image holds the program, the example model and all plotting tools. To update later, run the `pull` command again (or `memdif update` after step 3, which also refreshes the helper).

## 3. Install the helper

The helper `memdif.cmd` is a small file inside the image. You install it once, in a folder of its own, and then the command `memdif` works in every folder. In PowerShell:

```powershell
mkdir $HOME\memdif3d
```

```powershell
docker run --rm -v "$HOME\memdif3d:/work" ghcr.io/spark-hydro/memdif3d cp /opt/memdif3d/scripts/memdif.cmd /work/
```

`$HOME` is your user folder, `C:\Users\<your name>`. The second command copies `memdif.cmd` from the image into the new folder `memdif3d`. Docker Desktop may ask to share the folder the first time: allow it. Now add that folder to your `PATH` (once), so that Windows finds `memdif` wherever you are:

```powershell
[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";$HOME\memdif3d", "User")
```

**Close PowerShell and open a new one** (the change is seen by new windows only). Test:

```powershell
memdif help
```

It lists the commands: `run`, `view`, `domain`, `anim3d`, `gif`, `tool`, `newmodel`, `update` and `version`. Every command prints the long Docker command it runs, so you can see what happens (section *Under the hood*). If Windows does not find `memdif`, call it by its whole path, `& $HOME\memdif3d\memdif.cmd help`, and check section *When something goes wrong*.

That is all the setup. Your models and results stay wherever you like; there is no fixed folder layout.

## 4. Set up the model

### 4.1 Give the path of your model

The model is a folder with the input files (`rm.nam`, `rm.dis`, ...); see [Input files](INPUT_SPEC.md). It can be anywhere. Tell `memdif` where it is, either with `-m` in front of the command:

```powershell
memdif -m D:\projects\my_model domain
```

or once for the PowerShell window, so that the commands below stay short:

```powershell
$env:MEMDIF_MODEL = "D:\projects\my_model"
```

The path may be the model folder or the path of the main name file, `D:\projects\my_model\case2.nam`. Give the file when the folder holds several `.nam` files; with a folder `memdif` takes the only `.nam` file in it. Always give the **whole model folder** (or a name file inside it): the name file lists the other input files relative to its own folder, so they must be next to it. The model is only read, never changed.

To keep the setting for every new window, store it once: `setx MEMDIF_MODEL "D:\projects\my_model"` (it is valid from the next window on).

The **results** go into the folder you are in when you give the command. Use a folder of its own for each run, for example next to the model:

```powershell
mkdir D:\projects\my_model_runs\run1
```

```powershell
cd D:\projects\my_model_runs\run1
```

!!! tip "No model yet?"
    `memdif newmodel` copies the example model (the Reduced_Matrix case) to a folder `mymodel` in the folder you are in, and `memdif newmodel name` uses the name you give. Use that folder as a starting point for your own model.

### 4.2 Check the model before you run it

```powershell
memdif domain
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
memdif tool make_holes.py /model /work/holes --pitch 3 --size 2 --closed
```

Move the folder `holes` to where you keep your models and point `MEMDIF_MODEL` at it (section 4.1).

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

## 5. Run the model

Go to the run folder (section 4.1) and run:

```powershell
memdif run
```

The screen shows the banner, the model size, the stability check and one line for every finished day, ending with *Normal termination*. The 28 days of the example take a few seconds. The run folder now holds the results: a `field_NNN.csv` and a `probes_NNN.csv` for every day and the restart files `restart.dat.1` and `restart.dat.2`.

Options of the program go after `run`:

| Option | Meaning |
|---|---|
| `--nperiods 2` | run only 2 days |
| `--steps-per-period 10` | 10 steps per day (a quick test: `--nperiods 1 --steps-per-period 10`) |
| `--fresh` | start again from the initial state and ignore the restart files |
| `--snapshot-every 60` | also write the whole box every 60 steps (one `snap_*.csv` file each) |

For example `memdif run --nperiods 2 --fresh`. If a run is interrupted, give the same command again in the same run folder: it continues after the last finished day. To start over, add `--fresh`, or use a new run folder.

## 6. Look at the results

Start the tools from the run folder. Each command writes one file into it; open the file from Windows Explorer.

### Interactive viewer: the domain, and any layer, row or column

```powershell
memdif view
```

Double-click `viewer.html`. The 3D model is on the left and the concentration on a plane of your choice on the right. In the bar on top choose **Plane**: *Layer* (the top view, rows × columns), *Row* (a section, layers × columns) or *Column* (a plane at one distance from the membrane, rows × layers), then the **number** of the layer, row or column with the slider. The chosen plane is drawn inside the 3D box. Use the **Time** slider or **Play** to animate the plane. Nothing runs again when you change the plane; the page holds the data. The frames are the day files of the run (`field_001.csv`, `field_002.csv`, ...). Under the 3D box you find the **probes**: the concentration of the source and of the probe cells against time, a line for each probe with a dot at every frame and a dotted line at the time shown. The **Probes** menu in the bar picks one probe or all, and the **Scale** menu switches between logarithmic and linear. The probe cells are marked in the 3D box and on the plane picture, with their names, in the colour of their line. The probes come from the `probes_NNN.csv` files in the run folder, which every run writes.

For finer time steps use the minutes output (section 4.4) and choose a window. The page grows with the number of frames:

```powershell
memdif view --pattern "day_*.csv" --every 5 --from 0 --to 120 --out first2h.html
```

### 3D animation in the browser

```powershell
memdif anim3d
```

writes `solute3d.html`: drag to rotate while the animation plays, scroll to zoom. It uses a logarithmic colour scale, so the small concentrations far from the membrane stay visible. To show only part of the box, add `--ilay 15` (one layer through the middle of the source), `--icol 3` (the plane 3 mm from the membrane) or a range such as `--ilay 15-29`.

### GIF with a top view and a column plane

```powershell
memdif gif --ilay 15 --icol 3
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

Each `memdif` command is one `docker run`. It links two folders into the container: the model folder, read-only, as `/model`, and the run folder as `/work`, where the output goes. For instance `memdif run --nperiods 2` is the same as

```powershell
docker run --rm -v "${PWD}:/work" -v "D:\projects\my_model:/model:ro" ghcr.io/spark-hydro/memdif3d /model/rm.nam --nperiods 2
```

The helper prints that line for every command. `memdif tool script.py ...` runs any tool of the image the same way; the scripts are listed in [Tools](tools.md). `-m` (or `MEMDIF_MODEL`) sets the model folder and `MEMDIF_IMAGE` another image. The image, the model and the results stay apart: the image never changes, and all your files are ordinary Windows folders.

## When something goes wrong

| Message or problem | What to do |
|---|---|
| `error during connect` or `cannot connect to the Docker daemon` | Docker Desktop is not running. Start it and wait for *Engine running*. |
| `no matching manifest for windows/amd64` | Docker Desktop is in Windows containers mode. Check with `docker info --format "{{.OSType}}"`; if it says `windows`, right-click the whale icon and choose *Switch to Linux containers*. |
| `'memdif' is not recognized` | Open a **new** PowerShell window after the `PATH` command of step 3, and check that `memdif.cmd` is in `$HOME\memdif3d` (`dir $HOME\memdif3d`). Until then call it as `& $HOME\memdif3d\memdif.cmd`. |
| `memdif: no model given` | Give the path of the model: `memdif -m D:\projects\my_model run`, or `$env:MEMDIF_MODEL = "..."` (section 4.1). |
| `memdif: no .nam file in ...` | The folder you gave holds no `.nam` file: check the path, or give the path of the `.nam` file itself. |
| `[memdif3d] cannot find the model file` | The model folder has no `.nam` file of that name; check the model folder with `dir`, or give the `.nam` file with `-m`. |
| the output folder is empty | Output goes to the folder you start the command in. Start it in the run folder. |
| `${PWD}` is not understood | You are in the old `cmd` window. Use PowerShell, or write `%cd%` instead of `${PWD}`. |
| a path with spaces fails | Keep the quotes around the `-v` arguments, as in the commands of this page: `-v "${PWD}:/work"`. The helper `memdif.cmd` already does this. |
| Docker asks to share a drive or folder | Allow it. In Docker Desktop: *Settings, Resources, File sharing*. |
| the first start takes minutes | The first pull downloads about 530 MB and Docker Desktop starts its Linux engine. Later runs start in a second. |
| the minutes output is slow | Writing hundreds of megabytes through a linked Windows folder is slower than a native disk. Use a time window (`FROM`, `TO`) or fewer layers (`LAYERS`). |

## Updating and cleaning up

```powershell
memdif update
```

fetches the newest image and then replaces `memdif.cmd` in `$HOME\memdif3d` by the helper of that image, so one command updates both. (If a helper from before 0.4.5 is installed, `memdif update` only pulls the image; copy the helper once with the `docker run ... cp` command of step 3, and later `memdif update` does both.) `docker images` lists the images on your computer and `docker image rm ghcr.io/spark-hydro/memdif3d:latest` deletes one. Your model and result folders are ordinary Windows folders and are not touched.

On Linux or macOS use `memdif.sh` (in `/opt/memdif3d/scripts` of the image) the same way: copy it to a folder on your `PATH` as `memdif` (for example `~/bin/memdif`) and run `memdif -m ~/projects/my_model run`.
