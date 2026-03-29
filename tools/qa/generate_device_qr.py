from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def load_payload(args: argparse.Namespace) -> str:
    if args.payload:
        return args.payload.strip()

    if args.input:
        return Path(args.input).read_text(encoding="utf-8-sig").strip()

    if not sys.stdin.isatty():
        return sys.stdin.read().strip()

    raise SystemExit("Provide --payload, --input, or pipe the ALICE_DEVICE_QR JSON into stdin.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a scannable QR PNG from an Alice device payload.")
    parser.add_argument("--payload", help="Raw Alice device QR JSON payload.")
    parser.add_argument("--input", help="Path to a text file containing the raw payload.")
    parser.add_argument("--output", default="output/device-qr.png", help="PNG output path.")
    args = parser.parse_args()

    payload = load_payload(args)
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Payload is not valid JSON: {exc}") from exc

    if not parsed.get("bootstrap_id") or not parsed.get("setup_code"):
        raise SystemExit("Payload must include bootstrap_id and setup_code.")

    import qrcode

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    image = qrcode.make(payload)
    image.save(output_path)

    print(f"QR PNG written to {output_path.resolve()}")
    print(payload)


if __name__ == "__main__":
    main()
