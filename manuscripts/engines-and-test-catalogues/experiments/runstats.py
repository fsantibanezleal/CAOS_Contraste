"""Cost of one run of an experiment script: wall time and peak resident memory, written into its results file under ``run``.

    import runstats
    t0 = runstats.start()
    ...
    result["run"] = runstats.stats(t0)

The manuscript's reproducibility section reads these figures from the JSON files; nothing is typed by hand.
"""
from __future__ import annotations

import platform
import sys
import time


def start() -> float:
    return time.time()


def peak_working_set_mb() -> int | None:
    """Peak resident memory of this process in MB (Windows ``PeakWorkingSetSize`` or POSIX ``ru_maxrss``); None when unavailable."""
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class Counters(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                            ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                            ("PeakPagefileUsage", ctypes.c_size_t)]

            c = Counters()
            c.cb = ctypes.sizeof(c)
            k32 = ctypes.WinDLL("kernel32")
            k32.GetCurrentProcess.restype = wintypes.HANDLE
            ps = ctypes.WinDLL("psapi")
            ps.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
            ok = ps.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
            return round(c.PeakWorkingSetSize / 2 ** 20) if ok else None
        import resource
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
    except Exception:  # a measurement of the run, never a reason to stop it
        return None


def stats(t0: float) -> dict:
    return {"seconds": round(time.time() - t0), "peak_working_set_mb": peak_working_set_mb(), "python": platform.python_version(),
            "platform": platform.platform()}
