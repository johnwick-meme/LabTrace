"""
run_demo.py — Run a complete LabTrace investigation from the terminal.
Demonstrates how Programmer 2 (or a user) interacts with the AI investigation harness.
"""

import json
import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from harness.agent import run_investigation

def main():
    print("==================================================")
    print("        LabTrace AI Investigation Demo")
    print("==================================================\n")

    # Load sample experiment
    sample_file = os.path.join(PROJECT_ROOT, "data", "sample_experiment.json")
    with open(sample_file, "r", encoding="utf-8") as f:
        experiment = json.load(f)

    print(f"Loaded Experiment: {experiment['name']} (ID: {experiment['experiment_id']})")
    print("Readings:")
    for i, r in enumerate(experiment["readings"], 1):
        print(f"  Reading {i}: {r['voltage']} V, {r['current']} A")

    print("\nRunning AI Agent Investigation with local Gemma...")
    print("(Calculating resistances, detecting anomalies, loading references, querying model...)\n")

    result = run_investigation(experiment)

    print(f"Status: {result['status'].upper()}\n")
    print("------------- AI INVESTIGATION REPORT -------------")
    # Output cleanly in terminal
    try:
        print(result["report"])
    except UnicodeEncodeError:
        print(result["report"].encode("ascii", errors="replace").decode("ascii"))

    print("\n---------------- EXECUTION TRACE -----------------")
    for step in result["trace"]:
        print(f"- Step: {step['step']:<22} | {step.get('detail', 'done')}")

    print("\n==================================================")
    print("Investigation Complete!")
    print("==================================================")

if __name__ == "__main__":
    main()
