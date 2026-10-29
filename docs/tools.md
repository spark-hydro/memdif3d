# Tools

Python scripts in `tools/`. The environment in `environment.yml` (`conda env create -f environment.yml`) has everything they need; the converters and the prototype use only the standard library.

## Input
| Script | What it does |
|---|---|
| `xlsx2memdif.py` | extracts a complete input set from the spreadsheet model (`python tools/xlsx2memdif.py Reduced_Matrix.xlsx data/reduced_matrix`) |
| `fix_reduced_matrix_xlsx.py` | writes a corrected copy of `Reduced_Matrix.xlsx` (the last tile one column further right, the typed zeros replaced by formulas); the original is not changed |
| `make_holes.py` | copies a set and punches holes in the membrane (`--pitch`, `--size`, `--offset`, `--closed`) |
| `make_intended_set.py` | makes the Reduced_Matrix set without the two spreadsheet irregularities |
| `convert_input.py` | converts the older list formats of faces and boundary to the faces map and boundary rules |
| `make_test_case.py` | writes the small synthetic sets used by the tests |

## Pictures and animations
| Script | What it does |
|---|---|
| `plot_domain.py` | to-scale side view, zoom at the membrane and plan view of the geometry |
| `plot_domain_3d.py` | the geometry as an interactive 3D page (HTML) |
| `animate_3d.py` | interactive 3D animation of the field files (one HTML file; drag to rotate while it plays) |
| `animate_field.py` | animated GIF with a face view and a side view, each switched on or off |
| `animate_compare.py` | GIF with two runs side by side and their difference, for example without and with holes |

```bash
python tools/animate_3d.py run1 --nam data/reduced_matrix/memdif3d.nam --log --out solute3d.html
python tools/animate_field.py run1 --nam data/reduced_matrix/memdif3d.nam --side off --out face.gif
python tools/animate_compare.py runA runB --nam-a A/memdif3d.nam --nam-b B/memdif3d.nam --pattern 'snap_*.csv' --out compare.gif
```

For finer frames than one per day, run with `--snapshot-every 60` and animate the `snap_*.csv` files with `--pattern`.

## Checking
| Script | What it does |
|---|---|
| `memdif_proto.py` | prototype solver that reads the input files; run as a script, it compares one step with the reference step |
| `expand_formulas.py`, `ref_step.py`, `test_vs_excel.py` | the reference rule and its check against the formulas of the spreadsheet (`expand_formulas.py Reduced_Matrix.xlsx` writes the `cells.json` that `test_vs_excel.py` reads; see `tools/README.md`) |
| `compare_excel_block.py` | compares a field file with a block of values in a spreadsheet |

```bash
memdif3d data/reduced_matrix/memdif3d.nam --nperiods 1 --steps-per-period 576 --fresh
python tools/compare_excel_block.py 3d_nonzeroboundry.xlsx field_001.csv --first-row 50694 --nam data/reduced_matrix/memdif3d.nam
```

`--first-row` is the first sheet row of the 43-row block; for a `Day_NNN.xlsx` file of the daily macro it is 6. For files made from the corrected workbook add `--fixed-layout`.
