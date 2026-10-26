#!/bin/sh
# Starts the command given to the container.
# The Python packages of the tools (numpy, matplotlib, Pillow, plotly) are not part of the image. The first
# time a tool that needs them is started (or python / python3), they are installed into $MEMDIF3D_PYENV
# (needs internet). Keep them between runs with a volume:  -v memdif3d-py:/opt/pyenv
# Running the model (memdif3d, memdif3d-debug) and the tools that use only the standard library
# (make_holes.py, convert_input.py, xlsx2memdif.py, ...) never installs anything.
set -e
PYENV="${MEMDIF3D_PYENV:-/opt/pyenv}"

need=no
case "$1" in
  python|python3)
    need=yes ;;
  *.py)
    f=$(command -v "$1" 2>/dev/null || true)
    if [ -n "$f" ] && grep -q -E '^[[:space:]]*(import|from)[[:space:]]+(numpy|matplotlib|plotly|PIL)' "$f"; then
      need=yes
    fi ;;
esac

if [ "$need" = yes ]; then
  if ! "$PYENV/bin/python" -c "import numpy, matplotlib, PIL, plotly" >/dev/null 2>&1; then
    echo "[memdif3d] first use of the plotting tools: installing numpy, matplotlib, Pillow and plotly into $PYENV" >&2
    echo "[memdif3d] (needs internet, takes about a minute; add -v memdif3d-py:$PYENV to keep them for the next run)" >&2
    python3 -m venv "$PYENV"
    "$PYENV/bin/pip" install --quiet --disable-pip-version-check --no-cache-dir -r /opt/memdif3d/requirements.txt
  fi
  PATH="$PYENV/bin:$PATH"
  export PATH
fi

exec "$@"
