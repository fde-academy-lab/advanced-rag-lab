# Trivia

**Takeaway:** every fact below has a file behind it. Use them to open a session, to argue with
a slide, or to remember why the rule exists.

| The fact | Where it lives |
|---|---|
| Client Zero is 484 documents and 2,430 chunks, synthetic on purpose so that every failure mode the curriculum needs is present and nothing is under NDA | [client-zero.md](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/docs/00-orientation/client-zero.md) |
| The repository published for months that fusion beat its best single leg. It did not. The retraction is kept public with a banner, and eleven files had to be corrected | [ADR-0015](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0015-correct-the-fusion-finding.md) |
| A repository-wide test now fails if the retracted sentence appears anywhere outside a correction | [tests/test_measurements.py](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/tests/test_measurements.py) |
| ANN recall against exact search was 0.00 at 2,430 chunks until long-range links were added; then 0.94 | [ADR-0010](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0010-ann-long-range-links.md) |
| Identifier recall went from 0.34 to 0.81 by telling the tokenizer that `_` and `-` are letters | [ADR-0013](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0013-analyzer-in-index-identity.md) |
| Context precision on the BM25 arm falls from 0.3029 to 0.1948 when k goes from 5 to 10, while recall rises. A precision gate is cleared by lowering k | [metrics.md](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/docs/04-evaluation/metrics.md) |
| The two retrieval legs fail on the same questions 96.84% of the time. With personas in the eval set, 99.10% | [fusion-rules.md](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/docs/09-research/measurements/fusion-rules.md) |
| The grader could be told what to say: an empty attempt, a syntax error and `os._exit(0)` all graded as passes on four units, until the grader started requiring its own result block | [hands-on-roadmap.md](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/docs/10-community/hands-on-roadmap.md) |
| A quiz key in this project's own draft was wrong. The selftest caught it because the reference answer was rejected by the grader it was written for | same page, "computed keys" |
| GitHub caps a label description at 100 characters. One label was 131, so it was never created and fifteen threads went without it | [seed_content.py](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/scripts/seed_content.py) |
| GitHub rejects a workflow file that reads a secret inside an `if:`. Two board workflows never ran, silently, until a lint test was added | [test_workflows.py](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/tests/test_workflows.py) |
| A YAML file reads a bare `no` as the boolean false. A quiz answer `is_a_specification: no` was graded wrong until the check accepted both | the cohort template's `Q01` |
| The reranker's first version was uniformly slightly worse at every k. Four days were spent verifying code that was fine; the features were wrong | the week 3 standup thread |
| The simulator will not give you a leaderboard. It counts attempts, clears and retries per person and refuses to rank, because ranking on a public repository ranks who had a free weekend | [labsim_progress.py](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/scripts/labsim_progress.py) |
| Pulse heat is `comments × 3 + people × 2 + reactions`. The weights are the whole policy and they are tested | [discussions_pulse.py](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/scripts/discussions_pulse.py) |
