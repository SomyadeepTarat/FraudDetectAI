"""Run an offline research snapshot: python -m scripts.run_joint_funding INPUT OUTPUT."""

import argparse
import json
from pathlib import Path

from app.services.joint_funding import analyze, rank_evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input", type=Path, help="JSON with ledger, threshold and optional queries"
    )
    parser.add_argument(
        "output", type=Path, help="Research certificate and query recommendation JSON"
    )
    args = parser.parse_args()
    request = json.loads(args.input.read_text())
    certificate = analyze(request["ledger"], request["threshold"])
    result = {
        "certificate": certificate,
        "evidence_selection": rank_evidence(
            request["ledger"], request["threshold"], request.get("queries", [])
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "funding_condition": certificate["result"],
                "selected_query": result["evidence_selection"]["selected_query"],
                "output": str(args.output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
