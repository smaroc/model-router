#!/usr/bin/env python3
"""Minimal assertions for model-router's classifier. Run: python3 tests/test_router.py"""
import json, subprocess, sys, os, re

ROUTER = os.path.join(os.path.dirname(__file__), "..", "router.py")

def tier(prompt):
    out = subprocess.run([sys.executable, ROUTER], input=json.dumps({"user_input": prompt}),
                         capture_output=True, text=True).stdout
    d = json.loads(out)
    ctx = d.get("hookSpecificOutput", {}).get("additionalContext", "")
    if not ctx:
        return "skip"
    m = re.search(r"\*\*(.+?)\*\*", ctx)
    name = m.group(1) if m else ""
    return "high" if "Opus" in name else "mid" if "Sonnet" in name else "low"

CASES = [
    ("renomme cette variable en userId", "low"),
    ("git status", "low"),
    ("what is the command to list files", "low"),
    ("translate this readme to english", "low"),
    ("écris une fonction qui valide un email", "mid"),
    ("fix the bug on the profile page", "mid"),
    ("add an endpoint to create a user", "mid"),
    ("design a multi-tenant architecture with cache and security", "high"),
    ("why does this deadlock happen intermittently under load", "high"),
    ("refactor auth.ts and session.ts to share the same logic", "high"),
    ("/model opus", "skip"),
    ("", "skip"),
]

def main():
    fails = 0
    for prompt, expected in CASES:
        got = tier(prompt)
        ok = got == expected
        fails += not ok
        print(("PASS" if ok else "FAIL"), f"[{got:>4}] expected {expected:>4} :: {prompt[:56]!r}")
    print(f"\n{len(CASES)-fails}/{len(CASES)} passed")
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
