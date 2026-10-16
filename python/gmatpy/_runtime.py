"""Locate bundled scientific inputs and initialize GMAT without changing cwd."""

from contextlib import contextmanager
import atexit
import os
from pathlib import Path
import tempfile
import threading

lock = threading.Lock()
_thread = threading.local()
_pid = os.getpid()
_directory = None
_engine = None


def _cleanup_runtime(gmat, directory, process_id):
    """Close the native log before Windows removes the owned runtime folder."""
    if os.getpid() != process_id:
        return
    # Use the existing API to close engine.log and redirect later native
    # shutdown messages to the OS null device. Keeping logging merely disabled
    # leaves the file handle open on Windows.
    if (Path(directory.name) / "engine.log").exists():
        gmat.UseLogFile(os.path.abspath(os.devnull))
    directory.cleanup()


def check_process():
    if os.getpid() != _pid:
        raise RuntimeError("GMAT cannot be used after fork; use multiprocessing's spawn context")


def engine():
    """Called under lock. Runtime outputs never go into site-packages."""
    global _engine, _directory
    check_process()
    if _engine is not None:
        return _engine
    from ._native import gmat_py as gmat

    root = Path(__file__).resolve().parent
    data = root / "data"
    _directory = tempfile.TemporaryDirectory(prefix="gmatpy-")
    # Register after TemporaryDirectory creates its weakref finalizer: atexit
    # runs in reverse order, so the native log must close first.
    atexit.register(_cleanup_runtime, gmat, _directory, _pid)
    output = Path(_directory.name)
    # FileManager validates even paths unused by headless propagation. Route those
    # to the private runtime directory rather than require a GMAT install layout.
    paths = {
        "ROOT_PATH": root,
        "DATA_PATH": data,
        "TIME_PATH": data / "time",
        "PLANETARY_COEFF_PATH": data / "planetary_coeff",
        "PLANETARY_EPHEM_DE_PATH": data / "planetary_ephem/de",
        "PLANETARY_EPHEM_SPK_PATH": data / "planetary_ephem/spk",
        "EARTH_POT_PATH": data / "gravity/earth",
        "ATMOSPHERE_PATH": data / "atmosphere/earth",
    }
    unused = ("VEHICLE_EPHEM_PATH VEHICLE_EPHEM_SPK_PATH "
              "VEHICLE_EPHEM_CCSDS_PATH LUNA_POT_PATH VENUS_POT_PATH MARS_POT_PATH "
              "OTHER_POT_PATH TEXTURE_PATH BODY_3D_MODEL_PATH MEASUREMENT_PATH "
              "GUI_CONFIG_PATH SPLASH_PATH ICON_PATH STAR_PATH VEHICLE_MODEL_PATH "
              "SPAD_PATH IONOSPHERE_PATH MARS_ATMOSPHERE_PATH FILE_UPDATE_PATH "
              "HELP_PATH OUTPUT_PATH").split()
    paths.update(dict.fromkeys(unused, output))
    files = {
        "DE405_FILE": "planetary_ephem/de/gmatpy_de405_1941_2201.405",
        "PLANETARY_SPK_FILE": "planetary_ephem/spk/gmatpy_de405_all_planets.bsp",
        "EOP_FILE": "planetary_coeff/eopc04_08.62-now",
        "NUTATION_COEFF_FILE": "planetary_coeff/NUTATION.DAT",
        "PLANETARY_PCK_FILE": "planetary_coeff/SPICEPlanetaryConstantsKernel.tpc",
        "EARTH_LATEST_PCK_FILE": "planetary_coeff/earth_latest_high_prec.bpc",
        "EARTH_PCK_PREDICTED_FILE": "planetary_coeff/SPICEEarthPredictedKernel.bpc",
        "EARTH_PCK_CURRENT_FILE": "planetary_coeff/SPICEEarthCurrentKernel.bpc",
        "LUNA_PCK_CURRENT_FILE": "planetary_coeff/SPICELunaCurrentKernel.bpc",
        "LUNA_FRAME_KERNEL_FILE": "planetary_coeff/SPICELunaFrameKernel.tf",
        "LEAP_SECS_FILE": "time/tai-utc.dat",
        "LSK_FILE": "time/SPICELeapSecondKernel.tls",
        "EGM96_FILE": "gravity/earth/EGM96.cof",
        "JGM2_FILE": "gravity/earth/JGM2.cof",
        "JGM3_FILE": "gravity/earth/JGM3.cof",
        "EARTH_EXPONENTIAL_FILE": "atmosphere/earth/EarthExponentialAtmosphereData.txt",
        "ICRF_FILE": "icrf/ICRF_Table.txt",
    }
    missing = [str(data / value) for value in files.values() if not (data / value).is_file()]
    if missing:
        raise RuntimeError("GMAT scientific data missing: " + ", ".join(missing))
    startup = output / "startup.txt"
    lines = ["MATLAB_MODE = NO_MATLAB", "RUN_MODE = TESTING_NO_PLOTS",
             "WRITE_PERSONALIZATION_FILE = OFF", f"LOG_FILE = {output / 'engine.log'}"]
    lines += [f"{key} = {value.as_posix()}/" for key, value in paths.items()]
    lines += [f"{key} = {(data / value).as_posix()}" for key, value in files.items()]
    # Optional weather datasets are deliberately absent from the distribution.
    # GMAT requires configured names even for constant-flux drag, but only reads
    # these files when a caller selects a file-based weather source. Native callers
    # may set CSSISpaceWeatherFile/SchattenFile to their own licensed inputs.
    lines += [f"CSSI_FLUX_FILE = {output / 'unbundled-space-weather.txt'}",
              f"SCHATTEN_FILE = {output / 'unbundled-schatten.txt'}"]
    startup.write_text("\n".join(lines) + "\n", encoding="utf-8")
    gmat.FileManager.Instance().SetBinDirectory("startup.txt", str(output) + os.sep)
    gmat.EchoLogFile(False)
    gmat.Setup(str(startup))
    if not gmat.Moderator.Instance().IsInitialized():
        raise RuntimeError(f"GMAT initialization failed; inspect {output / 'engine.log'}")
    _engine = gmat
    return gmat


@contextmanager
def operation(*, clear=False):
    """Serialize engine access, reject nesting, and optionally reset owned objects."""
    check_process()
    if getattr(_thread, "active", False):
        raise RuntimeError("GMAT calls cannot be nested; exit the native session first")
    with lock:
        _thread.active = True
        try:
            gmat = engine()
            if clear:
                gmat.Clear()
            try:
                yield gmat
            finally:
                if clear:
                    gmat.Clear()
        finally:
            _thread.active = False
