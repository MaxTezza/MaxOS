"""Thin CLI wrapper around the MaxOS orchestrator."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from max_os.core.orchestrator import AIOperatingSystem


def format_payload(payload: Any) -> str:
    try:
        return json.dumps(payload, indent=2, sort_keys=True)
    except TypeError:
        return str(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="MaxOS CLI prototype")
    parser.add_argument(
        "command",
        nargs="*",
        help="Natural language instruction to route through the orchestrator.",
    )
    parser.add_argument("--json", action="store_true", help="Print response payload as JSON only.")
    parser.add_argument(
        "--show-memory",
        action="store_true",
        help="Print the current conversation memory after executing the command.",
    )
    parser.add_argument(
        "--dump-memory",
        type=Path,
        help="Write the conversation transcript to the given file path after running the command.",
    )
    args = parser.parse_args()

    if not args.command:
        parser.error("Provide a command, e.g. 'scan Downloads for PSD files'.")

    command_text = " ".join(args.command)
    orchestrator = AIOperatingSystem()
    response = orchestrator.handle_text(command_text)

    if args.json:
        print(format_payload(response.payload or {}))
    else:
        print(f"Agent: {response.agent}")
        print(f"Status: {response.status}")
        print(f"Message: {response.message}")
        if response.payload:
            print("Payload:")
            print(format_payload(response.payload))

    if args.show_memory:
        print("\nConversation Memory:")
        for item in orchestrator.memory.history:
            print(f"[{item.role}] {item.content}")

    if args.dump_memory:
        orchestrator.memory.dump(args.dump_memory)
        print(f"Transcript saved to {args.dump_memory}")


if __name__ == "__main__":
    main()
