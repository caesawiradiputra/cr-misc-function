#!/usr/bin/env bash
# UserPromptSubmit hook: prompt coach. Passes the hook JSON on stdin to
# coach.py, which logs the prompt locally (masked) when the coach is on and prints
# the extra context asking Claude for a short coaching note.
#
# Fail-soft by design: every path exits 0 and stderr is discarded, so a problem
# here never blocks the turn or changes the other UserPromptSubmit hooks. A missing
# helper or a coach that is off prints nothing.
#
# PROMPT_COACH_SCRIPT overrides the helper path (used by the tests).
script="${PROMPT_COACH_SCRIPT:-$HOME/.claude/skills/prompt-coach/coach.py}"
[ -f "$script" ] || exit 0
timeout 5 python3 "$script" hook 2>/dev/null
exit 0
