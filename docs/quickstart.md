# Quick start

This page runs the example case, the Reduced_Matrix set in `data/reduced_matrix`, and looks at the results. You need the compiled program ([Install and build](install.md)) and, for the pictures, the Python environment from `environment.yml`.

## 1. Run the example
Run each simulation in its own folder, because the output files go to the current directory.

```bash
mkdir -p ~/memdif3d_runs/run1 && cd ~/memdif3d_runs/run1
/path/to/memdif3d/build/release/memdif3d /path/to/memdif3d/data/reduced_matrix/memdif3d.nam
```

The program prints a banner, the grid size, the stability check and one line per day:

```
grid (lay row col): 29 43 25  | fluid 23922 boundary 4481 source faces 225
stability: largest coefficient sum =  0.300 at cell (lay row col) 2 2 5 (limit 1)
period 1/28  t = 1440.0 min  CM =  0.8866237   elapsed     0.2 s
...
```

The `.nam` file is the *name file*: it lists the input packages. Everything else is read from the files it names.

## 2. What you get
In the run folder:

| File | Content |
|---|---|
| `field_001.csv` ... `field_028.csv` | the concentration of every cell at the end of each day |
| `probes_001.csv` ... | the source and chosen cells, one row per minute |
| `restart.dat.1`, `restart.dat.2` | the full state at the end of the last finished day |

See [Output files](outputs.md) for the formats.

## 3. Options
```text
memdif3d <namefile> [--fresh] [--force] [--nperiods N] [--steps-per-period N] [--snapshot-every N]
```

| Option | Effect |
|---|---|
| `--fresh` | delete the restart files and start from the initial state |
| `--nperiods N`, `--steps-per-period N` | override the run length (handy for short tests) |
| `--snapshot-every N` | also write the whole field every N steps (60 gives one file per hour) |
| `--force` | run even if the stability check fails (the results will be meaningless) |

Running the same command again after an interruption continues from the last finished day.

## 4. Look at the results
Time series of the source, from the probe file:

```python
import csv
import matplotlib.pyplot as plt

rows = list(csv.reader(open("probes_001.csv")))
head, data = rows[0], rows[1:]          # head: step, time, SOURCE, then one column per probe cell
t = [float(r[1]) for r in data]
for k in (2, 3):                        # the source and the first probe cell
    plt.plot(t, [float(r[k]) for r in data], label=head[k])
plt.xlabel("time (min)")
plt.legend()
plt.show()
```

Animations and domain pictures use the scripts in `tools/` (see [Tools](tools.md)):

```bash
python tools/animate_3d.py run1 --nam data/reduced_matrix/memdif3d.nam --log --out solute3d.html
```

The HTML file opens in any browser. Drag to rotate while the animation plays.

## 5. Try a short run with a membrane that has holes
```bash
python tools/make_holes.py data/reduced_matrix data/holes_p3 --pitch 3 --size 1
mkdir -p ~/memdif3d_runs/holes && cd ~/memdif3d_runs/holes
/path/to/memdif3d/build/release/memdif3d /path/to/memdif3d/data/holes_p3/memdif3d.nam
```

`make_holes.py` copies the input set and changes only the faces map. The next step is [Build your own model](build-your-model.md).
