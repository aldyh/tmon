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
- Each new branch should have master as the upstream: git branch -u master
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

## Coding guidelines

### For all languages

- Main API methods and top-level externally visible functions, include
  usage/code examples in the docs (docsstring or comments).
- Document each arg and return value in methods.

### C/C++ (GNU style)

- 2-space indentation.
- Braces on their own line, indented 2 spaces from the enclosing block.
- Code inside braces indented 2 more spaces (4 total from the enclosing block).
- Function definitions: return type on its own line, function name starts in
  column 0, opening brace in column 0.
- `struct`, `union`, `enum`, `typedef` definitions: opening brace in column 0.
- Space before parentheses in function calls and definitions: `foo (arg)`,
  `if (cond)`.
- Space after commas.

### Python

- Every class and every method/function gets a docstring.
- Use Google-style docstrings (Args/Returns/Example sections).

## Notes

- The authoritative docs are in docs/ (protocol, wiring, etc).
- This system is expected to remain small (a few devices) and run on a home network.
- The system should be testable from x86 Linux, without requiring the ESP32 hardware side to be up.
- ASCII character throughout please, no extended characters.
- If something isn't clear, ask me and we can discuss it.
