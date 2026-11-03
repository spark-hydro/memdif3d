#!/bin/sh
# memdif: short commands for the memdif3d Docker image (Linux and macOS; docker/memdif.cmd is the Windows version).
#
# Put this file next to your model folder (default: ./mymodel next to this script) and run it from the run folder:
#   cd run1 && ../memdif.sh run
# The model folder is linked read-only as /model, the current folder as /work (the output goes there).
# Set MEMDIF_MODEL to use another model folder, MEMDIF_IMAGE to use another image.
# Every command prints the long docker command it runs.
IMG="${MEMDIF_IMAGE:-ghcr.io/spark-hydro/memdif3d:latest}"
HERE="$(cd "$(dirname "$0")" && pwd)"
MODEL="${MEMDIF_MODEL:-$HERE/mymodel}"

usage() {
  cat <<'TXT'
memdif <command> [options]      run it in the folder where the results should go

  run [options]       run the model (options: --nperiods 2, --fresh, --snapshot-every 60, ...)
  view [options]      interactive viewer: viewer.html (3D domain + any layer, row or column)
  domain [options]    viewer of the model only, before a run: domain.html
  anim3d [options]    3D animation: solute3d.html
  gif [options]       GIF with a top view and a column plane: views.gif
  tool script.py ...  any tool of the image, for example: tool make_holes.py /model /work/holes --pitch 3 --size 2
  newmodel            copy the example model to ./mymodel next to this script
  update              download the newest image
  version             show the version of the program

The options after the command are those of the program or tool (see the manual, pages Tools and Input files),
for example:  memdif view --pattern "day_*.txt" --every 60 --from 0 --to 360
TXT
}

dock() {
  echo "+ docker run --rm -v $PWD:/work -v $MODEL:/model:ro $IMG $*" >&2
  docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work -v "$MODEL":/model:ro "$IMG" "$@"
}

nam() {
  NAM=$(ls "$MODEL"/*.nam 2>/dev/null | head -n 1)
  if [ -z "$NAM" ]; then
    echo "memdif: no .nam file in $MODEL (set MEMDIF_MODEL, or run: memdif newmodel)" >&2
    exit 2
  fi
  NAM=/model/$(basename "$NAM")
}

cmd="$1"
[ $# -gt 0 ] && shift
case "$cmd" in
  ""|help|-h|--help) usage ;;
  run)     nam; dock "$NAM" "$@" ;;
  view)    nam; dock make_viewer.py . --nam "$NAM" --out viewer.html "$@" ;;
  domain)  nam; dock make_viewer.py --nam "$NAM" --out domain.html "$@" ;;
  anim3d)  nam; dock animate_3d.py . --nam "$NAM" --log --out solute3d.html "$@" ;;
  gif)     nam; dock animate_field.py . --nam "$NAM" --out views.gif "$@" ;;
  tool)    dock "$@" ;;
  newmodel)
    if [ -e "$HERE/mymodel" ]; then echo "memdif: $HERE/mymodel exists already" >&2; exit 2; fi
    docker run --rm --user "$(id -u):$(id -g)" -v "$HERE":/work "$IMG" cp -r /opt/memdif3d/data/reduced_matrix /work/mymodel
    echo "model copied to $HERE/mymodel" ;;
  update)  docker pull "$IMG" ;;
  version) dock --version ;;
  *) echo "memdif: unknown command '$cmd'" >&2; usage >&2; exit 2 ;;
esac
