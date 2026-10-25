# Run with Docker

A ready-made image holds everything: the model (a fast build and a debug build), the example input sets, and the Python tools for plots and animations, with their packages installed. The only thing you need on your computer is Docker. It is useful on a server or cluster, on Windows or macOS, and whenever you want the same results on every machine (a run in the image is byte-identical to a native build).

## Get the image
```bash
docker pull ghcr.io/spark-hydro/memdif3d:latest
```

Images are published for every release. To build it yourself from the repository:

```bash
docker build -t memdif3d --build-arg VERSION=$(git describe --tags --always) .
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
| `/opt/venv` | Python with numpy, matplotlib, Pillow and plotly (versions in `docker/requirements.txt`) |
| `/work` | the working directory; mount your folder here |
