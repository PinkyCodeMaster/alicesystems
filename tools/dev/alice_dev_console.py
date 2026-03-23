from __future__ import annotations

import argparse
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import time

import serial
from serial import SerialException


RESET = "\x1b[0m"
COLORS = {
    "api": "\x1b[36m",
    "hub": "\x1b[32m",
    "esp": "\x1b[35m",
    "broker": "\x1b[33m",
    "system": "\x1b[37m",
    "error": "\x1b[31m",
}


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    hub_api_dir = repo_root / "apps" / "hub-api"

    parser = argparse.ArgumentParser(description="Alice Systems one-window local dev console")
    parser.add_argument("--hub-api-dir", type=Path, default=hub_api_dir)
    parser.add_argument("--hub-log-file", type=Path, default=hub_api_dir / "logs" / "hub-api.log")
    parser.add_argument("--hub-python", type=Path, default=hub_api_dir / ".alice" / "Scripts" / "python.exe")
    parser.add_argument("--serial-port", default=None, help="ESP32 serial port, for example COM5")
    parser.add_argument("--serial-baud", type=int, default=115200)
    parser.add_argument(
        "--serial-retry",
        action="store_true",
        help="Keep retrying when the serial port is unavailable. Default is to log once and stop watching the port.",
    )
    parser.add_argument("--broker-logs", action="store_true", help="Also stream docker logs from alice-mosquitto")
    parser.add_argument("--no-api", action="store_true", help="Do not start hub-api")
    parser.add_argument("--no-hub-log", action="store_true", help="Do not tail hub-api.log")
    return parser.parse_args()


def emit(prefix: str, message: str, *, stream: str = "system") -> None:
    color = COLORS.get(stream, "")
    lines = message.rstrip("\n").splitlines() or [""]
    for line in lines:
        print(f"{color}[{prefix}]{RESET} {line}", flush=True)


def stream_process_output(name: str, process: subprocess.Popen[str], output_queue: queue.Queue[tuple[str, str, str]]) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        output_queue.put((name, line.rstrip("\n"), name))


def start_hub_api(hub_api_dir: Path, hub_python: Path, output_queue: queue.Queue[tuple[str, str, str]]) -> subprocess.Popen[str]:
    python_executable = hub_python if hub_python.exists() else Path(sys.executable)
    cmd = [str(python_executable), "-m", "uvicorn", "app.main:app", "--reload"]
    output_queue.put(("system", f"starting hub-api with {' '.join(cmd)}", "system"))
    process = subprocess.Popen(
        cmd,
        cwd=hub_api_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    threading.Thread(target=stream_process_output, args=("api", process, output_queue), daemon=True).start()
    return process


def tail_file(prefix: str, path: Path, output_queue: queue.Queue[tuple[str, str, str]], stop_event: threading.Event) -> None:
    last_size = 0
    while not stop_event.is_set():
        if not path.exists():
            time.sleep(0.5)
            continue

        size = path.stat().st_size
        if size < last_size:
            last_size = 0

        if size == last_size:
            time.sleep(0.3)
            continue

        with path.open("r", encoding="utf-8") as handle:
            handle.seek(last_size)
            for line in handle:
                output_queue.put((prefix, line.rstrip("\n"), prefix))
            last_size = handle.tell()
        time.sleep(0.1)


def stream_serial(
    port: str,
    baud: int,
    output_queue: queue.Queue[tuple[str, str, str]],
    stop_event: threading.Event,
    *,
    retry: bool,
) -> None:
    label = f"esp:{port}"
    has_connected = False
    while not stop_event.is_set():
        try:
            with serial.Serial(port, baudrate=baud, timeout=1) as ser:
                has_connected = True
                output_queue.put((label, f"connected at {baud} baud", "esp"))
                while not stop_event.is_set():
                    raw = ser.readline()
                    if not raw:
                        continue
                    line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                    output_queue.put((label, line, "esp"))
        except SerialException as exc:
            output_queue.put((label, f"serial unavailable: {exc}", "error"))
            if not retry:
                if has_connected:
                    output_queue.put((label, "stopping serial watch until you restart the dev console", "system"))
                else:
                    output_queue.put((label, "no serial device present; not retrying", "system"))
                return
            time.sleep(2)


def stream_broker_logs(output_queue: queue.Queue[tuple[str, str, str]]) -> subprocess.Popen[str]:
    cmd = ["docker", "logs", "-f", "alice-mosquitto", "--tail", "20"]
    output_queue.put(("system", f"starting broker log stream with {' '.join(cmd)}", "system"))
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    threading.Thread(target=stream_process_output, args=("broker", process, output_queue), daemon=True).start()
    return process


def terminate_process(process: subprocess.Popen[str] | None, name: str, output_queue: queue.Queue[tuple[str, str, str]]) -> None:
    if process is None or process.poll() is not None:
        return
    output_queue.put(("system", f"stopping {name}", "system"))
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> int:
    args = parse_args()
    output_queue: queue.Queue[tuple[str, str, str]] = queue.Queue()
    stop_event = threading.Event()
    processes: list[tuple[str, subprocess.Popen[str] | None]] = []

    if os.name == "nt":
        os.system("")

    if not args.no_api:
        processes.append(("hub-api", start_hub_api(args.hub_api_dir, args.hub_python, output_queue)))

    if not args.no_hub_log:
        threading.Thread(
            target=tail_file,
            args=("hub", args.hub_log_file, output_queue, stop_event),
            daemon=True,
        ).start()
        output_queue.put(("system", f"tailing {args.hub_log_file}", "system"))

    if args.serial_port:
        threading.Thread(
            target=stream_serial,
            args=(args.serial_port, args.serial_baud, output_queue, stop_event),
            kwargs={"retry": args.serial_retry},
            daemon=True,
        ).start()
    else:
        output_queue.put(("system", "no serial port supplied", "system"))

    if args.broker_logs:
        processes.append(("broker-logs", stream_broker_logs(output_queue)))

    output_queue.put(
        (
            "system",
            "dev console ready; press Ctrl+C to stop everything",
            "system",
        )
    )

    try:
        while True:
            try:
                prefix, message, stream = output_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            emit(prefix, message, stream=stream)
    except KeyboardInterrupt:
        stop_event.set()
        for name, process in reversed(processes):
            terminate_process(process, name, output_queue)
        while not output_queue.empty():
            prefix, message, stream = output_queue.get_nowait()
            emit(prefix, message, stream=stream)
        emit("system", "dev console stopped", stream="system")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
