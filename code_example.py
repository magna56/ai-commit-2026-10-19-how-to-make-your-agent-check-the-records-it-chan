"""Check what an agent changed, not what it said, before it closes a task.

An agent's final message is written from its transcript, and the transcript holds what each
tool *returned*. A write that succeeded with the wrong value returns "ok" exactly like a right
one, so a run can end cleanly, with no tool error, and still leave the record wrong.

This file is the pattern to lift into your own agent:

  1. EffectLog     wrap every state-changing tool so each write records before and after
  2. Contract      per task type: the fields that must end at a value, and the fields it may touch
  3. check()       compare the effects to the contract -> wrong, missing, extra
  4. close_ticket  the gate: the closing tool refuses until check() is clean, and returns the diff
  5. pass_hat_k    run each task k times from a clean copy; report the all-k rate next to pass@1

Pure Python, no API keys. Run it: python3 code_example.py
"""
import copy
import random
from dataclasses import dataclass, field


# --- 1. Every write goes through one function that records what it changed ------------------

@dataclass
class Effect:
    table: str
    key: str
    field: str
    before: object
    after: object


class EffectLog:
    def __init__(self, db):
        self.db, self.effects = db, []

    def write(self, table, key, fld, value):
        row = self.db[table].setdefault(key, {})
        self.effects.append(Effect(table, key, fld, row.get(fld), value))
        row[fld] = value
        return "ok"                      # all the transcript ever sees


# --- 2 and 3. The contract, and the check that reads state rather than the transcript ---------

@dataclass
class Contract:
    required: dict                       # (table, key, field) -> value it must end at
    allowed: set = field(default_factory=set)   # extra fields this task may touch

    def check(self, db, effects):
        problems, touched = [], {(e.table, e.key, e.field) for e in effects}
        for (t, k, f), want in self.required.items():
            got = db[t].get(k, {}).get(f)
            if got != want:
                kind = "wrong" if (t, k, f) in touched else "missing"
                problems.append(f"{kind}: {t}/{k}.{f} is {got!r}, want {want!r}")
        for e in effects:
            spot = (e.table, e.key, e.field)
            if spot not in self.required and spot not in self.allowed:
                problems.append(f"extra: {e.table}/{e.key}.{e.field} {e.before!r} -> {e.after!r}")
        return problems


# --- 4. The gate sits on the tool that ends the task ------------------------------------------

def close_ticket(log, contract, ticket):
    problems = contract.check(log.db, log.effects)
    if problems:                         # goes back to the model as the tool result
        return "REFUSED, state does not match the task:\n  " + "\n  ".join(problems)
    log.write("tickets", ticket, "closed", True)
    return "closed"


# --- The case from the source: a $745 appliance stuck in an open carrier exception -----------

def fresh_db():
    return {"orders": {"A17": {"price": 745, "carrier_exception": "open"}},
            "tickets": {"T9": {"status": "open"}},
            "refunds": {}}


HOLD = Contract(required={("tickets", "T9", "status"): "on_hold"},
                allowed={("tickets", "T9", "note"), ("tickets", "T9", "closed")})

RUNS = {   # four agent runs; every tool call returns "ok" and every run ends "done"
    "right":   [("tickets", "T9", "status", "on_hold"), ("tickets", "T9", "note", "waiting on carrier")],
    "wrong":   [("tickets", "T9", "status", "resolved"), ("tickets", "T9", "note", "refund policy explained")],
    "extra":   [("tickets", "T9", "status", "on_hold"), ("refunds", "R1", "amount", 745)],
    "missing": [("tickets", "T9", "note", "carrier contacted")],
}


def demo_gate():
    print("run       transcript check   state check")
    for name, writes in RUNS.items():
        log = EffectLog(fresh_db())
        results = [log.write(*w) for w in writes]
        transcript_ok = all(r == "ok" for r in results)       # no tool error, agent said done
        verdict = close_ticket(log, HOLD, "T9")
        print(f"{name:9} {'pass' if transcript_ok else 'FAIL':18} {verdict.splitlines()[0]}")
        for line in verdict.splitlines()[1:]:
            print(f"{'':28}{line.strip()}")


# --- 5. pass^k: the same pass@1 can hide very different agents --------------------------------

def pass_hat_k(task_probs, k, rng):
    """Run every task k times from a clean state; a task counts only if all k pass."""
    first = sum(rng.random() < p for p in task_probs) / len(task_probs)
    every = sum(all(rng.random() < p for _ in range(k)) for p in task_probs) / len(task_probs)
    return first, every


def demo_consistency(n_tasks=500, k=20, seed=7):
    rng = random.Random(seed)
    spread = [0.71] * n_tasks                                  # fails a little on every task
    split = [0.98] * 300 + [0.45] * 120 + [0.10] * 80          # reliable on most, hopeless on some
    print(f"\n{n_tasks} tasks, {k} clean runs each")
    for name, probs in (("spread", spread), ("split", split)):
        first, every = pass_hat_k(probs, k, rng)
        print(f"  {name:7} pass@1 {first:5.1%}   passes all {k}: {every:5.1%}")


if __name__ == "__main__":
    demo_gate()
    demo_consistency()
