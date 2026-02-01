# Claude Code instructions

This repository is a one-shot, home-use project. Keep it simple, elegant, and readable.
Prefer straightforward designs over cleverness or over-engineering.  Keep APIs lean.

## Operating rules

- **Read first:** `README.md`, then docs/*, then `PLAN.md`.
- **Keep commits small:** one logical change per commit.
- **No default arguments in methods/functions.**
- **Tests:** add/adjust tests with changes; run unit tests before committing.

## Branch workflow

- Do work on a topic branch named: `claude/NNNN-<some-task>`
  - NNNN are sequential numbers, so use the next available number.
  - Examples: `claude/0000-protocol-python`, `0001-claude/simulator`, etc.
- If a task spans multiple commits, keep them reviewable and ordered.
- When I review your code, use incremental commits on top of current topic branch.

## Progress tracking

Keep a running checklist for the current branch in the branch description and in `PLAN.md`.
After each commit, update the checklist by marking what is done.

Commit checklist:
- [ ] Tests added/updated for the change
- [ ] `pytest` passes
- [ ] Code is simple/readable; no unnecessary abstractions
- [ ] No default arguments introduced in methods/functions
- [ ] Docs updated if behavior/interfaces changed (PLAN.md, docs/*).

## Notes

- The authoritative docs are in docs/ (protocol, wiring, etc).
- This system is expected to remain small (a few devices) and run on a home network.
- The system should be testable from x86 Linux, without requiring the ESP32 hardware side to be up.
- ASCII character throughout please, no extended characters.
- If something isn't clear, ask me and we can discuss it.
