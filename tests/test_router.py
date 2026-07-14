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
    if "Fable" in name:  return "creative"
    if "Opus" in name:   return "high"
    if "Sonnet" in name: return "mid"
    return "low"

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
    # creative lane -> Fable
    ("écris la landing page et le copy de mon site", "creative"),
    ("trouve un nom de marque pour mon app", "creative"),
    ("write the copy for the homepage hero section", "creative"),
    ("rédige un post LinkedIn sur le lancement", "creative"),
    ("write a tagline and a slogan for the brand", "creative"),
    # technical "design" must NOT hijack into creative
    ("design a multi-tenant architecture with cache and security", "high"),
    ("/model opus", "skip"),
    ("", "skip"),
    # skill/slash-command routing by command name
    ("/gsd:debug", "high"),
    ("/security-review", "high"),
    ("/agents:status", "low"),
    ("/hook-generator write 5 hooks for a fitness reel", "creative"),
    ("/gsd:plan-phase add checkout flow", "high"),
    ("/architecture design a multi-tenant system with sharded db", "high"),
    ("/gsd:new-project", "high"),
    ("/status", "skip"),           # bare unnamespaced CLI control command
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
