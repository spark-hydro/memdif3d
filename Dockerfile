# memdif3d in a container: the model (fast and debug builds), the example input sets and the Python tools
# (plots, animations, converters). The image is small: the Python packages of the tools are installed the
# first time a tool is used (see docker/entrypoint.sh).
#
#   docker build -t memdif3d --build-arg VERSION=$(git describe --tags --always) .
#   docker run --rm memdif3d memdif3d --version
#
# Run a model and make an animation, in the current folder (output files belong to you with --user):
#   docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work memdif3d \
#          memdif3d /opt/memdif3d/data/reduced_matrix/memdif3d.nam
#   docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work -v memdif3d-py:/opt/pyenv memdif3d \
#          animate_3d.py . --nam /opt/memdif3d/data/reduced_matrix/memdif3d.nam --log --out solute3d.html
# The volume memdif3d-py keeps the installed Python packages, so they are downloaded only once.
# Your own input set: mount its folder too, e.g. -v /path/to/mycase:/mycase and use /mycase/memdif3d.nam.
# The debug build (array bounds checks, floating-point traps) is `memdif3d-debug`.

# ---- stage 1: build the program (release and debug) ----
FROM ubuntu:24.04 AS build
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends gfortran cmake ninja-build \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY CMakeLists.txt .
COPY src ./src
# .git is not copied into the image: the version is passed in
ARG VERSION=unknown
RUN cmake -S . -B /build-release -G Ninja -D CMAKE_BUILD_TYPE=Release -D BUILD_TESTING=OFF -D MEMDIF3D_GIT_TAG="${VERSION}" \
 && cmake --build /build-release \
 && cp /build-release/memdif3d /memdif3d-release \
 && cmake -S . -B /build-debug -G Ninja -D CMAKE_BUILD_TYPE=Debug -D BUILD_TESTING=OFF -D MEMDIF3D_GIT_TAG="${VERSION}" \
 && cmake --build /build-debug \
 && cp /build-debug/memdif3d /memdif3d-debug

# ---- stage 2: small runtime image (Python only to create the package folder on first use) ----
FROM ubuntu:24.04
LABEL org.opencontainers.image.source="https://github.com/spark-hydro/memdif3d"
LABEL org.opencontainers.image.description="memdif3d: membrane diffusion in 3D, with the Python tools for plots and animations"
LABEL org.opencontainers.image.licenses="MIT"
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends libgfortran5 python3 python3-venv \
 && rm -rf /var/lib/apt/lists/*
COPY --from=build /memdif3d-release /usr/local/bin/memdif3d
COPY --from=build /memdif3d-debug /usr/local/bin/memdif3d-debug
COPY tools /opt/memdif3d/tools
COPY data /opt/memdif3d/data
COPY docker/requirements.txt /opt/memdif3d/requirements.txt
COPY docker/entrypoint.sh /usr/local/bin/memdif3d-entrypoint
# /opt/pyenv gets the Python packages on first use; it is writable for any user, and a volume mounted there keeps them
RUN chmod +x /opt/memdif3d/tools/*.py /usr/local/bin/memdif3d-entrypoint \
 && mkdir -p /opt/pyenv /work \
 && chmod 777 /opt/pyenv /work
# the tools are on the PATH (animate_3d.py, plot_domain.py, ...); matplotlib needs a folder it may write to
ENV PATH="/opt/memdif3d/tools:${PATH}" \
    MPLCONFIGDIR=/tmp/matplotlib \
    MPLBACKEND=Agg \
    MEMDIF3D_PYENV=/opt/pyenv
# runs are made in a mounted folder; outputs go to the current directory
WORKDIR /work
ENTRYPOINT ["memdif3d-entrypoint"]
CMD ["memdif3d"]
