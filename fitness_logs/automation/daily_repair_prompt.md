# Daily record automatic repair

You are running unattended in an isolated clone of the health repository. Repair exactly the target daily JSON supplied at the end of this prompt so the repository's deterministic `recalculate`, `validate`, `report`, and `jq empty` checks pass.

Read `README.md`, `fitness_logs/AGENTS.md`, `fitness_logs/README.md`, `fitness_logs/current_plan.json`, `fitness_logs/food_catalog.json`, `fitness_logs/record_tools.py`, and the target JSON before editing.

You may edit only the supplied target JSON. Use only facts already present in the repository, its Git history, and the supplied validation error. Preserve reported food, quantities, body weight, exercises, stable IDs, event IDs, corrections, estimates, uncertainty, and source evidence. Never invent a meal, quantity, workout, completion state, or user statement. Structural normalization, restoring required empty arrays or snapshots from the plan effective on that date, recalculating derived fields, and adding an uncertainty note already supported by an entry's estimate basis are allowed.

If the error requires a new user fact, do not guess. Preserve the entry and express the unresolved fact using the existing missing or pending fields when the schema supports it. Do not edit scripts, rules, prompts, plans, catalogs, templates, other dates, credentials, Git configuration, or state outside the target JSON. Do not commit, push, pull, reset, clean, stash, install software, or contact the user.

After editing, run the four deterministic checks. Finish with a concise summary of the repair and any question that still needs user input.
