#!/usr/bin/env python3
"""Run real Gemini user matching for a grounded crisis and cache results in DB."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

DEFAULT_CRISIS_ID = "31111111-1111-4111-8111-111111111101"


async def main() -> None:
    parser = argparse.ArgumentParser(description="Match Ansar users to a grounded crisis")
    parser.add_argument("crisis_id", nargs="?", default=DEFAULT_CRISIS_ID)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run Gemini even if cached matched_users exist",
    )
    args = parser.parse_args()

    from grounding.match_users import match_users_for_crisis

    crisis_id = UUID(args.crisis_id)
    print(f"Matching users for crisis {crisis_id} (force={args.force})...")
    print("Calling Gemini (gemini-3.5-flash)...\n")

    result = await match_users_for_crisis(crisis_id, force=args.force)

    print(json.dumps(result, indent=2))
    print(f"\nMatched users: {len(result.get('matched_users', []))}")
    print(f"Cached: {result.get('cached', False)}")
    print(f"Elapsed: {result.get('elapsed_seconds')}s")


if __name__ == "__main__":
    asyncio.run(main())
