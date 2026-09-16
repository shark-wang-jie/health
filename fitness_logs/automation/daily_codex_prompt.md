# Daily Codex semantic review

You are running unattended inside the health repository. Review exactly the target date supplied at the end of this prompt. Do not create a record for any other date.

Read these files in this exact order before reviewing or editing:

1. `README.md`
2. `fitness_logs/AGENTS.md`
3. `fitness_logs/README.md`
4. `fitness_logs/CHATGPT_CODEX_WORKFLOW.md`
5. `fitness_logs/handoff_summary.md`
6. `fitness_logs/current_plan.json`
7. `fitness_logs/food_catalog.json`
8. the supplied target daily JSON

Inspect the target JSON fields `intake_entries`, `exercise_entries`, `morning_weight_kg`, `corrections`, `food_coverage`, `training_coverage`, `record_status`, `missing_sections`, `non_energy_pending_notes`, and `daily_summary`.

Check for duplicate foods; corrections accidentally recorded as additions; duplicate or unstable `id` and `event_id`; incorrect food catalog reuse; incorrect priority between current labels, actual consumed amounts, user statements, catalog values, and historical defaults; unremoved leftovers, bones, or unconsumed soup; duplicated oils, sauces, seasonings, or components; incorrect totals; duplicate active calories or summed readings for the same training event; incorrect coverage or record status; lost corrections, basis, or uncertainty.

You may edit only files under `fitness_logs/`, and only when existing repository facts prove the correction. Preserve stable identifiers, correction history, basis, uncertainty, source images, and raw training readings. Never invent meals, quantities, weights, workouts, body weight, soup consumption, completion state, or recovery. If new user facts are required, preserve the source record and add a concise pending item using the existing schema. Do not append the same pending item or correction twice on repeated runs.

Do not commit, push, pull, reset, checkout, clean, stash, install software, change credentials, or contact the user. Do not modify schema, calculation code, plans, templates, or general rules unless a deterministic inconsistency in the target record cannot be repaired without such a change; in that exceptional case, leave files unchanged and report the blocker.

If you edit source fields, use the repository tools to recalculate and validate. If no correction is justified, do not edit files. Finish with a concise summary containing: semantic review result, files changed, corrections made, and pending questions.
