# Lessons for KOML

Recovery benchmarking needs a prior definition of success and an independently
checked expected label. Counting a reported success is straightforward; proving
that the recovery was correct is a separate experimental responsibility.

The build tests validate the narrow assumption that exact aggregation of recorded
trials can reconcile with independently specified fixture totals. Changing a
planted expected label introduces a false positive; changing an observed outcome
changes the recovery total. This validates computation rather than a hardcoded
report. It does not validate a recovery strategy, production reliability or demand.

An operating rule for future builds: preserve trial-level evidence in every saved
analysis and recompute aggregates during rendering. Treat copied labels, missing
baselines and absent real-use evidence as limitations, not proof of performance.

The next evidence-based improvement is to review a hand-checked real-use sample
after 14 days and fix its largest measured error cause, or kill for non-use. The
window and final verdict remain pending; no actual-use evidence has been supplied.
