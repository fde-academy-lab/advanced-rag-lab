# Prompt · close a cohort

The week after the last session. Paste into a session in the clone.

---

Use the `cohort-repo-setup` skill. Cohort N, OWNER/REPO, is finished. Close it out.

1. Digest: run `scripts/labsim_digest.py --days 90`. Which checks caught the most people, which units were never attempted, which drills were cleared first try most often. This feeds the next cohort's `cohort.yaml`; write the recommendation as a list of concrete changes, each with the number that motivates it.
2. Threads: list Q&A threads with a marked answer and more than two reactions. Propose which become entries in `docs/00-orientation/faq.md`. Do not write the FAQ entries; the instructor of record does.
3. Retractions: search every doc and thread for claims that a measurement note in `docs/09-research/measurements/` contradicts. Use the guard in `tests/test_measurements.py` as the model. List them; do not edit threads.
4. Boards: set the Hands-on and Pulse boards to closed, and mark every Lifecycle practice that has its artefact as Done, with the link. Tell me which practices were marked Done without the artefact; that is the retro's first question.
5. Access: list every collaborator with `triage` and the invitation state. Do not remove anyone; give me the list and the one command that would.
6. Archive: propose the repository be archived after 90 days, and say what archiving breaks (scheduled workflows stop; Discussions become read-only).
7. Write the closing handover in the `verification.md` format, plus a "what to change for cohort N+1" section that the kickoff prompt for the next cohort can quote.
