# Output files

All output goes to the current directory, with the file names set in the OC package (`DAILY_FIELD`, `PROBES`, `RESTART`, `SNAPSHOT`, see [Input files](INPUT_SPEC.md)). A period is one day (1440 steps in the example). `{period}` in a name becomes the period number with three digits.

## Screen log
The program prints a banner, the grid size (`lay row col`), the number of fluid and boundary cells, the number of source faces, the coefficients, and the stability check. Then one line per period with the time and the source concentration `CM`:

```
period 1/28  t = 1440.0 min  CM =  0.8866237   elapsed     0.2 s
```

## Field files: `field_001.csv`, ...
The whole concentration field at the end of each period, as comma-separated text. The first line is a header with the period, the step, the time and the source concentration:

```text
# memdif3d field, period 1, step 1440, minutes 1440.000, CM  8.866236657285997E-001
# ILAY 1
 0.000000000000000E+000, 0.000000000000000E+000, ...
```

After it come the layers. Each `# ILAY n` line starts a block with one line per row (`IROW` 1 to NROW) and the values along the columns (`ICOL` 1 to NCOL, from the membrane outward) in each line. Solid and boundary cells are included (solid cells are 0). The layout is the same as the `.dis` file, so an `IDOMAIN` tile and a concentration tile line up.

To read a field in Python:

```python
import numpy as np
def read_field(path):
    blocks, cur = [], None
    for line in open(path):
        if line.startswith("# ILAY"):
            cur = []; blocks.append(cur)
        elif not line.startswith("#") and line.strip():
            cur.append([float(t) for t in line.split(",")])
    return np.array(blocks)          # shape (NLAY, NROW, NCOL)
```

`tools/animate_field.py` and `tools/animate_3d.py` do this for you.

## Snapshot files: `snap_0000060.csv`, ...
The same format as a field file, written every N steps inside a run (`SNAPSHOT FILEOUT snap_{step}.csv EVERY 60` in the OC file, or `--snapshot-every 60`). The step number in the name has seven digits, so the files sort in time order. A snapshot is about 0.75 MB for the Reduced_Matrix grid. Use them for finer animations (`--pattern 'snap_*.csv'`).

## Probe files: `probes_001.csv`, ...
One row per time step with the columns `step,time,SOURCE,<cells...>`; `time` is in minutes. The cells are listed in the `probes` block of the OC file, either `SOURCE` or a cell id `ilay irow icol`, and a cell column is named `ilay_irow_icol`:

```text
step,time,SOURCE,15_22_1,15_22_6
1,1.000, 9.996666666666667E-001, 2.777777777777778E-002, 0.0
2,2.000, 9.993427037037037E-001, 5.338580246913581E-002, 0.0
```

With `{period}` in the name a new file starts every period; without it, one file is kept and appended to after a restart. The source column is the concentration of the source cell \(C_M\).

## Restart files: `restart.dat.1`, `restart.dat.2`
At the end of every period the complete state is written (the concentration of every cell and the source cell, with the period and step). The files are text, so they can move between computers, and the program alternates between the two names so that an interruption during writing never destroys the previous state.

When you start again in the same folder, the newest valid file is used and the run continues with the next period (the log says `restart: continuing after period N`). `--fresh` deletes both files and starts from the initial state. A run whose periods are all finished does nothing. A restart file of an older format version is refused.
