import psutil
import time
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel

def generate_layout() -> Layout:
    """Creates a clean, two-row grid layout for the terminal."""
    layout = Layout()

    # Split the main screen into a top header and a bottom body
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body")
    )

    # Split the header horizontally into two panels
    layout["header"].split_row(
        Layout(name="cpu_panel"),
        Layout(name="mem_panel")
    )
    return layout

def threshold_color(pct: float) -> str:
    """Maps a usage percentage to a severity color: green -> yellow -> red."""
    if pct > 85:
        return "red"
    if pct > 60:
        return "yellow"
    return "green"

def get_cpu_info() -> Panel:
    """Fetches CPU usage and returns a stylized UI panel."""
    cpu_percent = psutil.cpu_percent(interval=None)
    cores = psutil.cpu_count(logical=True)
    color = threshold_color(cpu_percent)

    return Panel(
        f"Usage: [{color}]{cpu_percent}%[/{color}] | Logical Cores: {cores}",
        title="CPU Monitor",
        border_style=color
    )

def get_mem_info() -> Panel:
    """Fetches overall system Memory usage and returns a UI panel."""
    mem = psutil.virtual_memory()
    total_gb = mem.total / (1024**3)
    used_gb = mem.used / (1024**3)
    color = threshold_color(mem.percent)

    return Panel(
        f"Usage: [{color}]{mem.percent}%[/{color}] | {used_gb:.1f} GB / {total_gb:.1f} GB",
        title="Memory Monitor",
        border_style=color
    )

def get_process_table() -> Table:
    """Fetches top running processes and returns a formatted table."""
    # show_edge=False keeps the interface realistic and prevents visual clutter
    table = Table(expand=True, show_edge=False)

    table.add_column("PID", justify="right", style="cyan")
    table.add_column("Process Name", style="magenta")
    table.add_column("CPU %", justify="right", style="green")
    table.add_column("Physical RAM (MB)", justify="right", style="yellow")
    table.add_column("Status", justify="center")

    processes = []

    # Iterate through currently running processes, pulling specific attributes
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
        try:
            info = proc.info
            # Convert physical memory (RSS) from bytes to Megabytes
            mem_mb = info['memory_info'].rss / (1024 * 1024) if info['memory_info'] else 0

            processes.append((
                info['pid'],
                info['name'] or "Unknown",
                info['cpu_percent'] or 0.0,
                mem_mb,
                info['status'] or "Unknown"
            ))

        # OS safety measure: Ignore processes that close while we read them,
        # or system processes we don't have permission to access.
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Sort processes by CPU usage descending and grab the top 15
    processes = sorted(processes, key=lambda p: p[2], reverse=True)[:15]

    for pid, name, cpu, mem, status in processes:
        table.add_row(str(pid), name, f"{cpu:.1f}", f"{mem:.1f}", status)

    return table

def prime_process_cpu_baselines() -> None:
    """
    psutil.Process.cpu_percent() always returns 0.0 on the very first call for
    a given process, since there's no earlier CPU-time snapshot to diff
    against. process_iter() caches Process objects across calls, so calling
    this once here (the same trick already used for the system-wide gauge
    below) means the very first rendered table shows real numbers instead of
    a wall of zeros.
    """
    for proc in psutil.process_iter():
        try:
            proc.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def main():
    # Initialize CPU percentage baseline so the first reading isn't 0.0
    psutil.cpu_percent(interval=0.1)
    prime_process_cpu_baselines()

    layout = generate_layout()

    # Run the live display, updating twice per second. screen=True makes it full terminal.
    with Live(layout, refresh_per_second=2, screen=True) as live:
        try:
            while True:
                layout["cpu_panel"].update(get_cpu_info())
                layout["mem_panel"].update(get_mem_info())
                layout["body"].update(get_process_table())
                time.sleep(0.5)
        except KeyboardInterrupt:
            # Allow the user to quit gracefully without throwing Python errors
            pass

if __name__ == "__main__":
    main()