# Agent workflow

This project was built with LLM coding agents, using a customized multi-agent setup rather than
the stock configuration. These are the actual prompts, included because the process is part of the
engineering.

The shape of the problem drove the shape of the workflow. This codebase is a formal solver where
an incorrect assumption can silently turn a proof into a guess — so the workflow is built around
*not letting decisions get made implicitly*, by either the human or the agents.

## Three roles

| File | Role |
|---|---|
| [CLAUDE.md](CLAUDE.md) | The orchestrator. Acts as tech lead: gathers requirements, delegates, reports. Never writes code. |
| [Plan.md](Plan.md) | Architect. Read-only — designs task plans and the tests that go with them, and is explicitly forbidden from editing files. |
| [Code.md](Code.md) | Implementer. Writes tests first, then code. Pinned to a cheaper model with a restricted tool set. |

The split exists because the failure modes are different. An agent that both designs and implements
will quietly reshape the design to suit the code it already wrote. Making the planner read-only
means a design change has to come back through the orchestrator, and through the human.

## Decisions as queryable records

The piece that matters most is the records system. Design decisions don't live in commit messages
or chat history where they get lost — they live in a queryable store, indexed by the files they
govern. Agents query it by path before touching code:

```
python3 ~/.claude/scripts/records.py query --path engine/src/solver/bucket/expand.cpp
```

Each record carries a **confidence level**, which determines whether an agent may revisit it:

- `requirement` — a human decision. Never changed without approval.
- `settled` — an agent decision made deliberately. Question it only if the approach is failing.
- `provisional` — an agent decision where alternatives may be better. Question it freely.

This directly addresses the most expensive failure mode in agent-assisted work: an agent
encountering a non-obvious design choice, assuming it was accidental, and "fixing" it. Confidence
levels make the difference between *deliberate* and *incidental* machine-readable, so a decision
made in week three still constrains work in week twelve.

The tool lives in a separate project; the prompts here show how it is used.

## Rules that emerged from failures

Several instructions in these files exist because their absence caused real problems:

- **Ask before starting.** The orchestrator must restate its interpretation, its reasoning, and its
  concerns, then stop and wait. Misalignment is cheap to fix before implementation and expensive
  after.
- **Escalate after two failures.** Repeating a failed approach is the characteristic agent failure
  mode. Two strikes forces a human back into the loop.
- **Tests before implementation, always.** Written into all three prompts, and verified by the
  orchestrator rather than trusted.
- **Fail loudly.** If logic isn't guaranteed to have valid inputs, throw. This is a project-wide
  principle that shows up in the solver as "never auto-bisect" — a self-healing search would mask
  exactly the bugs that make a proof unsound.
- **One agent at a time.** Parallel agents editing a shared tree produce conflicts that cost more
  than the concurrency saves — but the bigger reasons are cost and coherence. Serial execution
  bounds how much work can be done in a wrong direction before anyone notices, and it keeps the
  orchestrator reasoning about exactly one task at a time instead of interleaving several.

## Case study: porting the game's mechanics

The hardest use of this setup was porting the game's mechanics into the engine in the predecessor
project — hundreds of individual behaviours, each of which had to be right, with no oracle to
check against beyond the game itself and the community documentation.

The approach was an assembly line of narrow, single-purpose passes. A script drove each stage,
feeding items to an agent **one at a time** and writing results to a file as it went:

1. **Enumerate.** Break the game into individual mechanics; emit the list.
2. **Research.** For each mechanic, an agent consults the game's source or the Run & Bun
   documentation and determines how it is *supposed* to behave.
3. **Confirm.** A second agent independently re-derives each entry. Disagreements go to a third
   agent, or to me. Nothing proceeds on one agent's unreviewed reading.
4. **Plan.** A planning agent turns the confirmed list into an implementation order and chunks it
   across coding agents — explicitly **grouping tasks that touch the same file**, since re-reading
   a large file for each of five scattered tasks wastes both tokens and context.
5. **Specify tests.** Another agent designs a unit test per mechanic — *specifications only*, no
   implementation.
6. **Implement.** Another agent implements them one at a time, against a generic logging facility
   built to serve three consumers at once — interactive debugging, unit-test assertions, and
   checking the engine against the visual tool — so a mechanic could be observed the same way in
   all three contexts. When a test failed, the agent was permitted to check whether it had
   implemented the *test* correctly, but was **forbidden from reading the engine source**. This is
   the load-bearing rule: an implementer who can see the code will rationalize the test into
   agreeing with it, and the test stops being an independent check.
7. **Adjudicate.** A separate agent reviews each failing test and rules on whether the *source* or
   the *test* is wrong, producing a list of decisions.
8. **Re-plan.** A planning agent turns those decisions into fix tasks, under the same grouping
   rules, and the line runs again.

Three things made it work:

- **One item at a time, with results written to disk as it goes.** Context was 200k at the time,
  and a long pass would otherwise lose its early work to the middle of the window or to
  auto-compaction. Persisting after each item makes the process resumable and makes progress
  auditable.
- **Independence between producing and checking.** The researcher, the confirmer, the test
  designer, the implementer, and the adjudicator are separate sessions. None of them can see the
  reasoning that produced the artifact they're checking, which is what makes the check worth
  anything. It's double-entry bookkeeping for a port.
- **Cheap review relative to cheap error.** Every extra pass is one more narrow agent run. Catching
  a single silently-wrong mechanic — the kind that surfaces fifty hours later as an inexplicable
  divergence — pays for many of them.

## Caveat

These are working files, tuned against one codebase and one person's preferences, not a general
recommendation. The parts likely to transfer are the read-only planner, the confidence-tagged
decision records, and the requirement to restate intent before acting.
