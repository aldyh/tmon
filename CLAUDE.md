# Claude Code instructions

This repository is a one-shot, home-use project. Keep it simple, elegant, and readable.
Prefer straightforward designs over cleverness or over-engineering.  Keep APIs lean.

## Operating rules

- **Read first:** `README.org`, then docs/*, then `PLAN.org`.
- **TODO list for project:** `TODO.org`.
- **Keep commits small:** one logical change per commit.
- **No default arguments in methods/functions.**
- **Tests:** add/adjust tests with changes; run unit tests before committing.

## Branch workflow

- Do work on a topic branch named: `claude/NNN-<some-task>`
  - NNN are sequential numbers, so use the next available number.
  - Examples: `claude/000-protocol-python`, `claude/001-simulator`, etc.
- Each new branch should have master as the upstream: git branch -u master
- If a task spans multiple commits, keep them reviewable and ordered.
- When I review your code, amend the specific commits being reviewed via interactive rebase, rather than adding fix-up commits on top.
- Use fast-forward merges: `git merge <branch>` (no `--no-ff`).

## Progress tracking

Keep a running checklist for the current branch in the branch description and in `PLAN.org`.
After each commit, update the checklist by marking what is done.

Commit checklist:
- [ ] Tests added/updated for the change
- [ ] `pytest` passes
- [ ] Code is simple/readable; no unnecessary abstractions
- [ ] No default arguments introduced in methods/functions
- [ ] Docs updated if behavior/interfaces changed (PLAN.org, docs/*).
- [ ] Generated/build artifacts added to `.gitignore`.

## Coding guidelines

### C/C++ (GNU style)

- 2-space indentation.
- Braces on their own line, indented 2 spaces from the enclosing block.
- Code inside braces indented 2 more spaces (4 total from the enclosing block).
- Function definitions: return type on its own line, function name starts in
  column 0, opening brace in column 0, body indented 2 spaces.
  **Not** indented like inner blocks. Example:
  ```c
  void
  setup (void)
  {
    do_something ();
  }
  ```
- `struct`, `union`, `enum`, `typedef` definitions: opening brace in column 0.
- Inner blocks (`if`, `while`, `for`, etc.): braces indented 2 spaces from the
  enclosing block, code inside indented 2 more.
- Space before parentheses in function calls and definitions: `foo (arg)`,
  `if (cond)`.
- Space after commas.
- C++ member variables use `m_` prefix: `m_count`, `m_name`.
- **Documentation placement**: Headers (`.h`) contain only prototypes and brief
  comments for types/constants. Full function documentation (description, Args,
  Returns) goes in the source (`.c`) file, directly above each function
  definition. See `client/include/protocol.h` and `client/src/protocol.c` for the
  reference style.

### Python

- Every class and every method/function gets a docstring.
- Short/obvious methods: a one-line summary is enough. Use type hints
  in the signature instead of documenting each arg.
- Larger or non-obvious functions: use Google-style sections
  (Args/Returns/Raises) where they add value.

## Notes

- The authoritative docs are in docs/ (protocol, wiring, etc).
- This system is expected to remain small (a few devices) and run on a home network.
- The system should be testable from x86 Linux, without requiring the ESP32 hardware side to be up.
- ASCII character throughout please, no extended characters.
- New org files should start with `#+STARTUP: showall`. Do not change existing STARTUP lines.
- Branch numbers are sequential; check existing branches with `git branch` before creating a new one.
- Any new subsystem or testable work must be added to the Makefile (`make check` and build targets), following the existing style.
- If something isn't clear, ask me and we can discuss it.
