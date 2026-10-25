import os
import time
import ctypes
import subprocess
import csv
import io
from typing import Any
import psutil

# Prime CPU counter on module load so the first call returns real elapsed delta
psutil.cpu_percent(interval=None)


class GpuMonitor:
    """Robust multi-tier GPU usage monitor for Windows.
    Tier 1: Direct in-process NVML via ctypes (NVIDIA GPUs, microsecond latency).
    Tier 2: nvidia-smi CLI fallback.
    Tier 3: Windows Performance Counter (typeperf) for Intel Iris/Arc & AMD Radeon.
    """

    def __init__(self):
        self._backend: str | None = None
        self._nvml = None
        self._nvml_devices: list[Any] = []
        self._gpu_name: str = ""
        self._last_poll: float = 0.0
        self._cached_gpu: int = 0
        self._poll_ttl: float = 0.5  # Cache for 500ms
        self._init_backend()

    def _init_backend(self):
        # Tier 1: NVML via ctypes (NVIDIA)
        try:
            nvml = ctypes.CDLL("nvml.dll")
            if nvml.nvmlInit_v2() == 0:
                cnt = ctypes.c_uint()
                if nvml.nvmlDeviceGetCount_v2(ctypes.byref(cnt)) == 0 and cnt.value > 0:
                    for i in range(cnt.value):
                        dev = ctypes.c_void_p()
                        if nvml.nvmlDeviceGetHandleByIndex_v2(i, ctypes.byref(dev)) == 0:
                            self._nvml_devices.append(dev)

                    if self._nvml_devices:
                        self._nvml = nvml
                        self._backend = "nvml"
                        buf = ctypes.create_string_buffer(96)
                        if nvml.nvmlDeviceGetName(self._nvml_devices[0], buf, 96) == 0:
                            self._gpu_name = buf.value.decode("utf-8", errors="ignore").strip()
                        return
        except Exception:
            pass

        # Tier 2: nvidia-smi CLI
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=1.5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if res.returncode == 0 and res.stdout.strip():
                self._backend = "nvidia-smi"
                self._gpu_name = res.stdout.strip().split("\n")[0].strip()
                return
        except Exception:
            pass

        # Tier 3: Windows Performance Counters (Intel Iris/Arc, AMD Radeon)
        try:
            res = subprocess.run(
                ["typeperf", r"\GPU Engine(*engtype_3D)\Utilization Percentage", "-sc", "1"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=2.0,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if res.returncode == 0:
                self._backend = "typeperf"
                self._gpu_name = "DirectX 3D GPU"
                return
        except Exception:
            pass

    def get_gpu_percent(self) -> int:
        now = time.time()
        if now - self._last_poll < self._poll_ttl:
            return self._cached_gpu

        self._last_poll = now

        # Tier 1: NVML
        if self._backend == "nvml" and self._nvml and self._nvml_devices:
            try:
                class nvmlUtilization_t(ctypes.Structure):
                    _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]

                max_gpu = 0
                for dev in self._nvml_devices:
                    util = nvmlUtilization_t()
                    if self._nvml.nvmlDeviceGetUtilizationRates(dev, ctypes.byref(util)) == 0:
                        if util.gpu > max_gpu:
                            max_gpu = util.gpu

                self._cached_gpu = min(100, max(0, int(max_gpu)))
                return self._cached_gpu
            except Exception:
                pass

        # Tier 2: nvidia-smi CLI
        if self._backend == "nvidia-smi":
            try:
                res = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=1.5,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if res.returncode == 0:
                    vals = [int(v.strip()) for v in res.stdout.strip().split("\n") if v.strip().isdigit()]
                    if vals:
                        self._cached_gpu = min(100, max(0, max(vals)))
                        return self._cached_gpu
            except Exception:
                pass

        # Tier 3: typeperf Windows Performance Counter
        if self._backend == "typeperf":
            try:
                res = subprocess.run(
                    ["typeperf", r"\GPU Engine(*engtype_3D)\Utilization Percentage", "-sc", "1"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=2.0,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                reader = list(csv.reader(io.StringIO(res.stdout)))
                data_rows = [r for r in reader if len(r) > 1 and not r[0].startswith("(PDH")]
                if data_rows:
                    vals = []
                    for x in data_rows[0][1:]:
                        try:
                            vals.append(float(x.strip()))
                        except ValueError:
                            pass
                    self._cached_gpu = min(100, max(0, round(sum(vals))))
                    return self._cached_gpu
            except Exception:
                pass

        return self._cached_gpu

    @property
    def gpu_name(self) -> str:
        return self._gpu_name


_gpu_monitor = GpuMonitor()


def get_system_stats() -> dict[str, Any]:
    return {
        "cpu": round(psutil.cpu_percent(interval=None)),
        "ram": round(psutil.virtual_memory().percent),
        "gpu": _gpu_monitor.get_gpu_percent(),
        "gpu_name": _gpu_monitor.gpu_name,
    }
