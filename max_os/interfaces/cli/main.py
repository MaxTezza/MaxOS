"""Thin CLI wrapper around the MaxOS orchestrator."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from max_os.core.orchestrator import AIOperatingSystem


def format_payload(payload: Any) -> str:
    try:
        return json.dumps(payload, indent=2, sort_keys=True)
    except TypeError:
        return str(payload)


async def async_main() -> None:
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
    parser.add_argument(
        "--show-personality",
        action="store_true",
        help="Show learned personality model and preferences.",
    )
    parser.add_argument(
        "--export-personality",
        type=Path,
        help="Export personality model to JSON file.",
    )
    parser.add_argument(
        "--show-context",
        action="store_true",
        help="Print the latest context signals captured by the orchestrator.",
    )
    parser.add_argument(
        "--show-learning-metrics",
        action="store_true",
        help="Print recent real-time learning batch metrics.",
    )
    args = parser.parse_args()

    orchestrator = AIOperatingSystem()

    # Handle personality inspection commands
    if args.show_personality:
        if orchestrator.enable_learning:
            personality = orchestrator.personality.export_personality()
            print("=== User Personality Model ===")
            print("\nCommunication Style:")
            for key, value in personality["communication_style"].items():
                print(f"  {key}: {value:.2f}")
            print("\nSkill Levels:")
            for domain, level in personality["skill_levels"].items():
                print(f"  {domain}: {level:.2f}")
            print(
                f"\nRecent Interactions: {len(orchestrator.personality.get_recent_interactions())}"
            )
            return
        else:
            print("Learning system is disabled")
            return

    if args.export_personality:
        if orchestrator.enable_learning:
            import json

            personality = orchestrator.personality.export_personality()
            args.export_personality.write_text(json.dumps(personality, indent=2))
            print(f"Personality exported to {args.export_personality}")
            return
        else:
            print("Learning system is disabled")
            return

    if not args.command:
        parser.error("Provide a command, e.g. 'scan Downloads for PSD files'.")

    command_text = " ".join(args.command)
    response = await orchestrator.handle_text(command_text)

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

    if args.show_context:
        signals = orchestrator.get_last_context().get("signals")
        print("\nContext Signals:")
        if signals:
            print(format_payload(signals))
        else:
            print("No context signals captured for this interaction.")

    if args.show_learning_metrics:
        metrics = orchestrator.get_learning_metrics()
        print("\nLearning Metrics:")
        if metrics:
            print(format_payload(metrics))
        else:
            print("No learning batches processed yet.")

    if args.dump_memory:
        orchestrator.memory.dump(args.dump_memory)
        print(f"Transcript saved to {args.dump_memory}")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
