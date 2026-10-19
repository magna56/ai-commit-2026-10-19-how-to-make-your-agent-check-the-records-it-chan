# How to Make Your Agent Check the Records It Changed Before It Says Done

**TL;DR:** An agent decides it is done from what its tools returned, and a wrong write returns success just like a right one. Check the records it actually changed against what the task required, before it closes the task.

Published from [The AI Commit](https://theaicommit.com/#2026-10-19/code) — Building Agents & MCP, 2026-10-19.

## Run

```bash
python3 code_example.py
```

## Output

```
run       transcript check   state check
right     pass               closed
wrong     pass               REFUSED, state does not match the task:
                            wrong: tickets/T9.status is 'resolved', want 'on_hold'
extra     pass               REFUSED, state does not match the task:
                            extra: refunds/R1.amount None -> 745
missing   pass               REFUSED, state does not match the task:
                            missing: tickets/T9.status is 'open', want 'on_hold'

500 tasks, 20 clean runs each
  spread  pass@1 73.0%   passes all 20:  0.0%
  split   pass@1 72.4%   passes all 20: 38.4%

```

## Code

See [`code_example.py`](code_example.py).
