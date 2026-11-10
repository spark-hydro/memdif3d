#!/bin/sh
# memdif: short commands for the memdif3d Docker image (Linux and macOS; docker/memdif.cmd is the Windows version).
#
# Put this file in a folder on your PATH (for example ~/bin, named memdif) and run it in the folder where the
# results should go:
#   memdif -m ~/projects/mymodel run
# -m is the model: a folder (the .nam file in it is used) or the path of the .nam file itself. Instead of -m you
# can export MEMDIF_MODEL. The model is linked read-only as /model, the current folder as /work.
# MEMDIF_NAM chooses the name file when a model folder holds several .nam files, MEMDIF_IMAGE uses another image.
# Every command prints the long docker command it runs.
IMG="${MEMDIF_IMAGE:-ghcr.io/spark-hydro/memdif3d:latest}"
while [ "$1" = "-m" ] || [ "$1" = "--model" ]; do
  [ -n "$2" ] || { echo "memdif: -m needs a path" >&2; exit 2; }
  MEMDIF_MODEL="$2"; shift 2
done
MODEL="${MEMDIF_MODEL%/}"
NAMEFILE="$MEMDIF_NAM"
case "$MODEL" in
  *.nam) NAMEFILE="$(basename "$MODEL")"; MODEL="$(dirname "$MODEL")" ;;
esac
[ -n "$MODEL" ] && MODEL="$(cd "$MODEL" 2>/dev/null && pwd)"

usage() {
  cat <<'TXT'
memdif [-m MODEL] <command> [options]    run it in the folder where the results should go

  -m MODEL            the model: a folder with the input files, or the path of its .nam file
                      (or export MEMDIF_MODEL)
  run [options]       run the model (options: --nperiods 2, --fresh, --snapshot-every 60, ...)
  view [options]      interactive viewer: viewer.html (3D domain + any layer, row or column)
  domain [options]    viewer of the model only, before a run: domain.html
  anim3d [options]    3D animation: solute3d.html
  gif [options]       GIF with a top view and a column plane: views.gif
  tool script.py ...  any tool of the image, for example: tool make_holes.py /model /work/holes --pitch 3 --size 2
  newmodel [name]     copy the example model to a new folder (default mymodel) in the current folder
  update              download the newest image
  version             show the version of the program

The options after the command are those of the program or tool (see the manual, pages Tools and Input files),
for example:  memdif -m ~/projects/mymodel view --pattern "day_*.txt" --every 60 --from 0 --to 360
TXT
}

dock() {
  mnt=""; [ -n "$MODEL" ] && mnt="-v $MODEL:/model:ro"
  echo "+ docker run --rm -v $PWD:/work $mnt $IMG $*" >&2
  if [ -n "$MODEL" ]; then
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work -v "$MODEL":/model:ro "$IMG" "$@"
  else
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work "$IMG" "$@"
  fi
}

nam() {
  if [ -z "$MODEL" ]; then
    echo "memdif: no model given. Use: memdif -m PATH $cmd   (PATH = model folder or .nam file), or export MEMDIF_MODEL" >&2
    exit 2
  fi
  if [ -n "$NAMEFILE" ]; then NAM="$MODEL/$NAMEFILE"; else NAM=$(ls "$MODEL"/*.nam 2>/dev/null | head -n 1); fi
  if [ -z "$NAM" ] || [ ! -f "$NAM" ]; then
    echo "memdif: no name file found in $MODEL (give the .nam file with -m, or set MEMDIF_NAM)" >&2
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
    name="${1:-mymodel}"
    if [ -e "$PWD/$name" ]; then echo "memdif: $PWD/$name exists already" >&2; exit 2; fi
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work "$IMG" cp -r /opt/memdif3d/data/reduced_matrix "/work/$name"
    echo "model copied to $PWD/$name" ;;
  update)  docker pull "$IMG" ;;
  version) dock --version ;;
  *) echo "memdif: unknown command '$cmd'" >&2; usage >&2; exit 2 ;;
esac
