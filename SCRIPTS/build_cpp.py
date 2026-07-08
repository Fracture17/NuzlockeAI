# Build script for the nuzlocke_engine_cpp pybind11 extension.
# Configures+builds via CMake into engine/build/, then copies the .so into the venv site-packages.
import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CPP_DIR = REPO_ROOT / "engine"
BUILD_DIR = CPP_DIR / "build"
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"


def _run(cmd: list[str], **kwargs) -> None:
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"ERROR: command failed (exit {result.returncode}): {' '.join(str(c) for c in cmd)}")
        sys.exit(result.returncode)


def _pybind11_cmake_dir() -> str:
    out = subprocess.check_output(
        [str(VENV_PYTHON), "-c", "import pybind11; print(pybind11.get_cmake_dir())"],
        text=True,
    )
    return out.strip()


def _ext_suffix() -> str:
    out = subprocess.check_output(
        [str(VENV_PYTHON), "-c", "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX'))"],
        text=True,
    )
    return out.strip()


def _site_packages() -> Path:
    out = subprocess.check_output(
        [str(VENV_PYTHON), "-c",
         "import sysconfig; print(sysconfig.get_path('purelib'))"],
        text=True,
    )
    return Path(out.strip())


def main() -> None:
    print(f"Repo root : {REPO_ROOT}")
    print(f"Build dir : {BUILD_DIR}")

    pybind11_cmake_dir = _pybind11_cmake_dir()
    print(f"pybind11  : {pybind11_cmake_dir}")

    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    # Configure — source dir is engine/ (CMakeLists.txt lives there; include paths
    # are relative to CMAKE_CURRENT_SOURCE_DIR = engine/).
    _run(
        [
            "cmake",
            str(CPP_DIR),
            f"-DCMAKE_PREFIX_PATH={pybind11_cmake_dir}",
            f"-Dpybind11_DIR={pybind11_cmake_dir}",
            f"-DCMAKE_BUILD_TYPE=Release",
        ],
        cwd=BUILD_DIR,
    )

    # Build.
    cpu_count = os.cpu_count() or 1
    _run(["cmake", "--build", ".", "--", f"-j{cpu_count}"], cwd=BUILD_DIR)

    # Locate the built .so.
    ext_suffix = _ext_suffix()
    so_name = f"nuzlocke_engine_cpp{ext_suffix}"
    built_so = BUILD_DIR / so_name
    if not built_so.exists():
        # CMake may nest it inside a subdir; search one level.
        candidates = list(BUILD_DIR.rglob(so_name))
        if not candidates:
            print(f"ERROR: built shared library '{so_name}' not found under {BUILD_DIR}")
            sys.exit(1)
        built_so = candidates[0]

    # Install into venv site-packages. Atomic replace (copy to temp + os.replace): a plain
    # copy2 over the existing .so truncates in place, which SIGBUSes every live process that
    # has the module mapped (observed 2026-07-04: rebuild mid-sweep killed all 8 pool workers).
    site_pkg = _site_packages()
    dest = site_pkg / so_name
    tmp_dest = site_pkg / (so_name + ".tmp")
    shutil.copy2(built_so, tmp_dest)
    os.replace(tmp_dest, dest)
    print(f"Installed : {dest}")
    print("SUCCESS: nuzlocke_engine_cpp built and installed.")


if __name__ == "__main__":
    main()
