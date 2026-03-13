"""
AIOps Router Workflow Entry.
"""

from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv
load_dotenv(override=True)

from aiops.notifications import format_report
from aiops.workflows import build_default_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="AIOps Router")
    parser.add_argument("--query", required=True, help="Query for AIOps agents")
    args = parser.parse_args()

    workflow = build_default_workflow()
    result = workflow.invoke({"query": args.query})
    # print("Original query:", result["query"])
    # print("\nClassifications:")
    for c in result["classifications"]:
        print(f"  {c['source']} ({c['severity']}): {c['query']}")
    print("\nFinal Answer:\n", result["final_answer"])

    # report = format_report(result["query"], result["results"])
    # print("\nReport:\n", report)


if __name__ == "__main__":
    main()
