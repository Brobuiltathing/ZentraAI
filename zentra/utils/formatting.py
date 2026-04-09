import shutil
import subprocess

from zentra.logger import log


def fmt_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def fmt_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days    = seconds // 86400
    hours   = (seconds % 86400) // 3600
    mins    = (seconds % 3600)  // 60
    parts   = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{mins}m")
    return " ".join(parts)


def gpu_info_sync() -> str:
    if not shutil.which("nvidia-smi"):
        return ""
    try:
        r = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return ""
        lines = []
        for i, row in enumerate(r.stdout.strip().splitlines()):
            parts = [p.strip() for p in row.split(",")]
            if len(parts) < 5:
                continue
            name, util, mem_used, mem_total, temp = parts
            lines.append(
                f"  GPU {i}: {name}\n"
                f"    Utilisation : {util}%\n"
                f"    VRAM        : {mem_used} MB / {mem_total} MB\n"
                f"    Temperature : {temp} C"
            )
        return "\n".join(lines)
    except Exception as exc:
        log.warning(f"nvidia-smi query failed: {exc}")
        return ""
