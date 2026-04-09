import asyncio
import os
import platform
import subprocess
import time
from datetime import datetime

from zentra.config import PSUTIL_AVAILABLE
from zentra.logger import log
from zentra.memory import persist_memory
from zentra.utils.seen_emails import persist_seen_emails
from zentra.utils.formatting import fmt_bytes, fmt_uptime, gpu_info_sync

if PSUTIL_AVAILABLE:
    import psutil


def handle_system_stats(_data: dict) -> str:
    if not PSUTIL_AVAILABLE:
        return (
            "`psutil` is not installed.\n"
            "Run: `pip install psutil` then restart ZENTRA."
        )

    lines: list[str] = []

    boot_time  = datetime.fromtimestamp(psutil.boot_time())
    uptime_sec = time.time() - psutil.boot_time()
    lines.append(
        f"**System Stats** — {platform.node()}  |  "
        f"{platform.system()} {platform.release()}\n"
        f"Uptime: **{fmt_uptime(uptime_sec)}**  "
        f"(booted {boot_time.strftime('%d %b %Y %H:%M')})"
    )

    cpu_pct_overall = psutil.cpu_percent(interval=0.5)
    cpu_pct_per     = psutil.cpu_percent(interval=None, percpu=True)
    cpu_freq        = psutil.cpu_freq()
    cpu_count_phys  = psutil.cpu_count(logical=False) or "?"
    cpu_count_logic = psutil.cpu_count(logical=True)  or "?"

    freq_str = ""
    if cpu_freq:
        freq_str = f"  |  {cpu_freq.current:.0f} MHz"

    core_bar_parts = []
    for i, pct in enumerate(cpu_pct_per):
        bar_len  = int(pct / 10)
        bar      = "█" * bar_len + "░" * (10 - bar_len)
        core_bar_parts.append(f"    Core {i:<2} [{bar}] {pct:5.1f}%")

    lines.append(
        f"\n**CPU** — {platform.processor() or 'Unknown'}\n"
        f"  Overall : **{cpu_pct_overall:.1f}%**{freq_str}\n"
        f"  Cores   : {cpu_count_phys} physical / {cpu_count_logic} logical\n"
        + "\n".join(core_bar_parts)
    )

    ram  = psutil.virtual_memory()
    swap = psutil.swap_memory()
    ram_bar_len = int(ram.percent / 10)
    ram_bar     = "█" * ram_bar_len + "░" * (10 - ram_bar_len)

    lines.append(
        f"\n**Memory**\n"
        f"  RAM  [{ram_bar}] **{ram.percent:.1f}%**\n"
        f"       Used : {fmt_bytes(ram.used)} / {fmt_bytes(ram.total)}"
        f"  (available: {fmt_bytes(ram.available)})\n"
        f"  Swap : {fmt_bytes(swap.used)} / {fmt_bytes(swap.total)}"
        + (f"  ({swap.percent:.1f}%)" if swap.total else "  (no swap)")
    )

    disk_lines = ["**Disk**"]
    try:
        io_before = psutil.disk_io_counters()
        time.sleep(0.3)
        io_after  = psutil.disk_io_counters()
        read_spd  = (io_after.read_bytes  - io_before.read_bytes)  / 0.3
        write_spd = (io_after.write_bytes - io_before.write_bytes) / 0.3
        disk_lines.append(
            f"  I/O  : {fmt_bytes(read_spd)}/s read  |  {fmt_bytes(write_spd)}/s write"
        )
    except Exception:
        pass

    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            bar_len = int(usage.percent / 10)
            bar     = "█" * bar_len + "░" * (10 - bar_len)
            disk_lines.append(
                f"  {part.mountpoint:<12} [{bar}] {usage.percent:.1f}%  "
                f"{fmt_bytes(usage.used)} / {fmt_bytes(usage.total)}"
            )
        except PermissionError:
            disk_lines.append(f"  {part.mountpoint:<12} (permission denied)")
    lines.append("\n" + "\n".join(disk_lines))

    gpu_str = gpu_info_sync()
    if gpu_str:
        lines.append(f"\n**GPU**\n{gpu_str}")

    try:
        net_before = psutil.net_io_counters(pernic=False)
        time.sleep(0.3)
        net_after  = psutil.net_io_counters(pernic=False)
        net_sent   = (net_after.bytes_sent - net_before.bytes_sent) / 0.3
        net_recv   = (net_after.bytes_recv - net_before.bytes_recv) / 0.3

        net_lines = [
            "**Network**",
            f"  Live  : Up {fmt_bytes(net_sent)}/s  |  Down {fmt_bytes(net_recv)}/s",
            f"  Total : Sent {fmt_bytes(net_after.bytes_sent)}  |  "
            f"Recv {fmt_bytes(net_after.bytes_recv)}",
        ]

        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        active_ifaces = []
        for iface, stat in stats.items():
            if stat.isup and iface in addrs:
                for addr in addrs[iface]:
                    if addr.family.name in ("AF_INET", "2"):
                        active_ifaces.append(f"    {iface}: {addr.address}")
        if active_ifaces:
            net_lines.append("  Interfaces:")
            net_lines.extend(active_ifaces)

        lines.append("\n" + "\n".join(net_lines))
    except Exception as exc:
        log.warning(f"Network stats error: {exc}")

    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]):
            try:
                if p.info["status"] != "zombie":
                    procs.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        psutil.cpu_percent(interval=0.2)

        top_cpu = sorted(procs, key=lambda x: x.get("cpu_percent") or 0, reverse=True)[:5]
        top_ram = sorted(procs, key=lambda x: (x.get("memory_info") or psutil._common.pmem(0, 0)).rss, reverse=True)[:5]

        cpu_proc_lines = ["**Top 5 by CPU**"]
        for p in top_cpu:
            cpu_pct = p.get("cpu_percent") or 0
            mem_mb  = ((p.get("memory_info") or psutil._common.pmem(0, 0)).rss) / (1024 ** 2)
            cpu_proc_lines.append(
                f"  [{p['pid']:>6}] {p['name'][:28]:<28}  CPU {cpu_pct:5.1f}%  RAM {mem_mb:6.1f} MB"
            )

        ram_proc_lines = ["**Top 5 by RAM**"]
        for p in top_ram:
            cpu_pct = p.get("cpu_percent") or 0
            mem_mb  = ((p.get("memory_info") or psutil._common.pmem(0, 0)).rss) / (1024 ** 2)
            ram_proc_lines.append(
                f"  [{p['pid']:>6}] {p['name'][:28]:<28}  RAM {mem_mb:6.1f} MB  CPU {cpu_pct:5.1f}%"
            )

        lines.append("\n" + "\n".join(cpu_proc_lines))
        lines.append("\n" + "\n".join(ram_proc_lines))
    except Exception as exc:
        log.warning(f"Process stats error: {exc}")

    return "\n".join(lines)


async def handle_shutdown_bot(data: dict, scheduler=None) -> str:
    reply = data.get("reply", "").strip() or "Shutting down ZENTRA. Goodbye!"

    persist_memory()
    persist_seen_emails()

    if scheduler:
        scheduler.stop()

    log.info("Shutdown requested by user — exiting in 1.5 s.")
    asyncio.get_event_loop().call_later(1.5, lambda: os._exit(0))

    return reply


def handle_shutdown_pc(data: dict) -> str:
    mode   = (data.get("app") or "shutdown").strip().lower()
    system = platform.system()

    if system == "Windows":
        cmds = {
            "shutdown": ["shutdown", "/s", "/t", "10", "/c", "ZENTRA: Shutting down..."],
            "restart":  ["shutdown", "/r", "/t", "10", "/c", "ZENTRA: Restarting..."],
            "sleep":    ["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"],
            "cancel":   ["shutdown", "/a"],
        }
    elif system == "Darwin":
        cmds = {
            "shutdown": ["sudo", "shutdown", "-h", "+1"],
            "restart":  ["sudo", "shutdown", "-r", "+1"],
            "sleep":    ["pmset", "sleepnow"],
            "cancel":   ["sudo", "killall", "shutdown"],
        }
    else:
        cmds = {
            "shutdown": ["shutdown", "-h", "+1"],
            "restart":  ["shutdown", "-r", "+1"],
            "sleep":    ["systemctl", "suspend"],
            "cancel":   ["shutdown", "-c"],
        }

    if mode not in cmds:
        return (
            f"Unknown mode `{mode}`.\n"
            f"Use one of: `shutdown`, `restart`, `sleep`, or `cancel`."
        )

    cmd = cmds[mode]
    log.info(f"shutdown_pc: mode={mode} system={system} cmd={cmd}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            err = (result.stderr or result.stdout).strip()
            if mode != "sleep":
                return f"Command failed (exit {result.returncode}):\n```\n{err}\n```"

        if mode == "cancel":
            return "Scheduled shutdown/restart cancelled successfully."

        if mode == "sleep":
            return "Putting your PC to sleep now..."

        delay_note = " in ~1 minute" if system != "Windows" else " in 10 seconds"
        return (
            f"Your PC will **{mode}**{delay_note}.\n"
            f"Say **'cancel shutdown'** to abort."
        )

    except FileNotFoundError:
        return (
            "Shutdown command not found.\n"
            "On Linux/macOS you may need elevated permissions (sudo)."
        )
    except subprocess.TimeoutExpired:
        return "Shutdown command timed out — the system may still respond."
    except Exception as exc:
        log.error(f"shutdown_pc error: {exc}", exc_info=True)
        return f"Unexpected error during shutdown: {exc}"
