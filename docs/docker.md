# Run with Docker

Ready-made images hold the model (a fast build and a debug build), the example input sets and the Python tools for plots and animations. The only thing you need on your computer is Docker. It is useful on a server or cluster, on Windows or macOS, and whenever you want the same results on every machine (a run in the image is byte-identical to a native build).

There are two images from the same Dockerfile:

| Image | Size | Python packages | For |
|---|---|---|---|
| `ghcr.io/spark-hydro/memdif3d:latest` (**full**) | about 530 MB | installed in the image (numpy, matplotlib, Pillow, plotly) | everyone; works offline, nothing to install later |
| `ghcr.io/spark-hydro/memdif3d:slim` | about 190 MB | installed on first use of a plotting tool | running only the model on a server, or when size matters |

Start with the full image. Everything below works with it; the slim image has one extra option (see the end).

## Get the image
```bash
docker pull ghcr.io/spark-hydro/memdif3d:latest
```

Images are published for every release (`0.1.1` and `latest` for the full image, `0.1.1-slim` and `slim` for the slim one). To build them yourself from the repository:

```bash
docker build -t memdif3d --build-arg VERSION=$(git describe --tags --always) .                    # full
docker build -t memdif3d:slim --target slim --build-arg VERSION=$(git describe --tags --always) . # slim
```

## Run a model
Mount the folder where the output should go. The program writes its files to the current directory, which is `/work` in the container. `--user` makes the output files belong to you.

```bash
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work ghcr.io/spark-hydro/memdif3d \
    memdif3d /opt/memdif3d/data/reduced_matrix/memdif3d.nam
```

The example input sets (`reduced_matrix` and `reduced_matrix_intended`) are in `/opt/memdif3d/data`. For your own input set, mount its folder as well:

```bash
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work -v /path/to/mycase:/mycase \
    ghcr.io/spark-hydro/memdif3d memdif3d /mycase/memdif3d.nam
```

All options of the program work the same (`--fresh`, `--nperiods`, `--snapshot-every`, ...). Running without arguments prints the usage.

## Make pictures and animations
The scripts of `tools/` are on the `PATH` of the image. Run them in the folder with your output:

```bash
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work ghcr.io/spark-hydro/memdif3d \
    animate_3d.py . --nam /opt/memdif3d/data/reduced_matrix/memdif3d.nam --log --out solute3d.html
```

The page `solute3d.html` opens in a browser on your own computer. The other tools work the same way: `plot_domain.py`, `plot_domain_3d.py`, `animate_field.py`, `animate_compare.py`, `compare_excel_block.py`, `make_holes.py`. See [Tools](tools.md). Nothing in the image needs a screen.

## Debug build
If a run stops with an error you do not understand, use the debug build. It checks array bounds, traps floating-point errors and names the line of a problem, and it is several times slower:

```bash
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work ghcr.io/spark-hydro/memdif3d \
    memdif3d-debug /opt/memdif3d/data/reduced_matrix/memdif3d.nam --nperiods 1 --steps-per-period 10
```

## What is inside
| Path | Content |
|---|---|
| `/usr/local/bin/memdif3d` | the fast build (`-O3`) |
| `/usr/local/bin/memdif3d-debug` | the debug build |
| `/opt/memdif3d/tools` | the Python scripts, on the `PATH` |
| `/opt/memdif3d/data` | the example input sets |
| `/opt/pyenv` | the Python packages of the tools (full image: already installed; slim image: filled on first use) |
| `/work` | the working directory; mount your folder here |

## The slim image: Python packages on first use
The slim image does not contain numpy, matplotlib, Pillow and plotly. The first time you start a plotting tool (or `python`), the container installs them into `/opt/pyenv`, using the pinned versions in `docker/requirements.txt`. That needs an internet connection and takes about 20 seconds (a download of about 240 MB). The model itself and the tools that use only the standard library (`make_holes.py`, `convert_input.py`, `xlsx2memdif.py`, ...) never install anything.

With `--rm` a container is deleted when it ends, and the installed packages would go with it, so without more they are installed again on every run. Add a Docker *volume* to keep them:

```bash
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work -v memdif3d-py:/opt/pyenv \
    ghcr.io/spark-hydro/memdif3d:slim animate_3d.py . --nam /opt/memdif3d/data/reduced_matrix/memdif3d.nam --out solute3d.html
```

Docker creates the volume `memdif3d-py` the first time it is named. Later runs find the packages there and start in about two seconds. `docker volume ls` lists your volumes and `docker volume rm memdif3d-py` deletes it.

!!! note "Offline use of the slim image"
    On a computer without internet, run a plotting tool once with the volume while you are online. After that the volume has everything. Or use the full image.
