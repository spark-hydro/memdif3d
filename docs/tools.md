# Tools

Python scripts in `tools/`. The environment in `environment.yml` (`conda env create -f environment.yml`) has everything they need; the converters and the prototype use only the standard library.

## Input
| Script | What it does |
|---|---|
| `xlsx2memdif.py` | extracts a complete input set from the spreadsheet model (`python tools/xlsx2memdif.py Reduced_Matrix_fixed.xlsx data/reduced_matrix --name rm`) |
| `make_holes.py` | copies a set and punches holes in the membrane (`--pitch`, `--size`, `--offset`, `--closed`) |
| `convert_input.py` | converts the older list formats of faces and boundary to the faces map and boundary rules |
| `make_test_case.py` | writes the small synthetic sets used by the tests |

## Pictures and animations
| Script | What it does |
|---|---|
| `plot_domain.py` | to-scale side view, zoom at the membrane and plan view of the geometry |
| `plot_domain_3d.py` | the geometry as an interactive 3D page (one HTML file), made from the model input files only (name file and packages; no Excel file, no run output): `python tools/plot_domain_3d.py data/reduced_matrix/rm.nam --out domain3d.html [--ilay 15]`; the orange plane is the layer tile of the `.dis` file at `--ilay`, the purple plane the membrane plane (`ICOL = 1`) |
| `animate_3d.py` | interactive 3D animation of the field files (one HTML file; drag to rotate while it plays) |
| `animate_field.py` | animated GIF with a face view and a side view, each switched on or off |
| `animate_compare.py` | GIF with two runs side by side and their difference, for example without and with holes |

```bash
python tools/animate_3d.py run1 --nam data/reduced_matrix/rm.nam --log --out solute3d.html
python tools/animate_field.py run1 --nam data/reduced_matrix/rm.nam --side off --out face.gif
python tools/animate_compare.py runA runB --nam-a A/rm.nam --nam-b B/rm.nam --pattern 'snap_*.csv' --out compare.gif
```

For finer frames than one per day, run with `--snapshot-every 60` and animate the `snap_*.csv` files with `--pattern`.

The minutes output can be animated directly: `--pattern 'day_*.txt'` (or `'day_*.csv'`) uses every minute of the day files as frames, and `--every N` keeps every N-th minute (`--every 60` is one frame an hour; the whole day at once would make a huge page). The source concentration is not in a day file, so keep `probes_NNN.csv` (with a `SOURCE` line) next to them. The day files must hold all layers. Choose the time period with `--from` and `--to` (minutes of simulated time, both included, 1 day = 1440): `--from 0 --to 120 --every 5` shows the first two hours every five minutes. The initial state is added as the first frame only when the period starts at 0.

To see only part of the box in the 3D page, give a range with `--ilay`, `--irow` or `--icol` (1-based, both ends included): `--ilay 15-29` cuts the cloud open at the middle of the source. A single number draws one plane: `--ilay 15` (the layer through the source centre), `--irow 22`, or `--icol 3` (3 mm from the membrane). Only one of the three may be a single number. The GIF scripts use MODFLOW names for the planes (`animate_field.py`; `animate_compare.py` has `--icol` and `--ilay`):

| Option | View | You see |
|---|---|---|
| `--ilay N` | top view, MODFLOW xy: layer N | rows × columns |
| `--irow N` | row section, MODFLOW xz: row N | layers × columns |
| `--icol N` | column plane, MODFLOW yz: ICOL = N | rows × layers |

Each option switches its own panel on and the others off, so `--ilay 15` gives the top view alone and `--ilay 15 --icol 3` gives both (`--ilay` and `--irow` share one panel). The older options `--face-z`, `--side-plane xz|yz` and `--slice` still work; their `xz` and `yz` are the lab axes, so `--side-plane xz` is the top view.

```bash
python tools/animate_3d.py run1 --nam data/reduced_matrix/rm.nam --log --pattern 'day_*.txt' --every 60 --out solute3d.html
```

## Checking
| Script | What it does |
|---|---|
| `memdif_proto.py` | prototype solver that reads the input files; run as a script, it compares one step with the reference step |
| `expand_formulas.py`, `ref_step.py`, `test_vs_excel.py` | the reference rule and its check against the formulas of the spreadsheet (`expand_formulas.py Reduced_Matrix_fixed.xlsx` writes the `cells.json` that `test_vs_excel.py` reads; see `tools/README.md`) |
| `compare_excel_block.py` | compares a field file with a block of values in a spreadsheet |

```bash
memdif3d data/reduced_matrix/rm.nam --nperiods 1 --steps-per-period 1440 --fresh
python tools/compare_excel_block.py Day_1440.xlsx field_001.csv --first-row 6 --nam data/reduced_matrix/rm.nam --fixed-layout
```

`--first-row` is the first sheet row of the 43-row block; for a `Day_NNN.xlsx` file of the daily macro it is 6. For the workbook `Reduced_Matrix_fixed.xlsx` add `--fixed-layout`.
