# Ideas to try

**Takeaways**

1. Every idea names the seam it touches, the command that measures it, and the number to watch.
   An idea without those three is a wish.
2. Most of these take an evening. The ones marked *project* take a cohort week and have a brief
   in the extension points list.
3. Post what you find in Show and tell, with the interval. A negative result earns full credit.

| # | Try | Seam | Measure with | Watch |
|---|---|---|---|---|
| 1 | Change RRF's constant from 60 to 10 and to 200 | fusion | `run_eval.py --compare` | evidence recall against the dense leg alone; expect nothing outside the noise band |
| 2 | Weighted fusion at α = 0.3, 0.7, 0.9 | fusion | `run_eval.py --sweep` | where the curve peaks (it was 0.7790 at 0.5) and whether the peak is inside the interval |
| 3 | Drop the reranker entirely | rerank | `run_eval.py` with the reranker disabled | nDCG at k=8; if it barely moves, the reranker is not earning its latency |
| 4 | Halve k in the packer | context | `run_eval.py --ksweep` | full-chain recall against evidence recall; precision will rise, recall will fall, and the gap is what k buys |
| 5 | Turn `tokenchars '_-'` off and rerun | analyzer | `run_eval.py` on the identifier slice | recall on that slice (it was 0.34 without) |
| 6 | Remove the ANN long-range links | index | the ANN recall curve in notebook 04 | recall at ef=64 (it fell to 0.00 without them) |
| 7 | Reverse the packer's ordering | context | `run_eval.py` | full-chain recall; position sensitivity on this corpus is inside the noise band, and you can confirm that |
| 8 | Add personas to the eval set and remeasure overlap | eval | `failure_overlap.py --with-personas` | overlap rises to 0.9910; ask what that does to any fusion claim |
| 9 | Swap the LSA encoder for a sentence-transformer | encoder | `run_eval.py` | evidence recall on the dense arm and seconds per 1k queries; both numbers or it is not a result |
| 10 | Write a decoy for an existing drill that its check does not catch | simulator | `python -m labsim selftest` | the selftest must fail; then fix the check |
| 11 | Write an `answer` drill for one number in the k grid | simulator | `labsim validate`, `selftest` | a pinned key needs a test in `test_measurements.py` |
| 12 | Grade a submission with a harness other than the one it was written for | simulator | post it in a thread | whether the reply names the same checks |
| 13 | Run the eval gate against a deliberately regressed baseline | CI | open a pull request | the scorecard comment must go red |
| 14 | Add a query class and give it its own fusion weight (*project*, extension 3) | fusion | `--compare` per class | the per-class interval, not the average |
| 15 | Distil the cross-encoder (*project*, extension 4) | rerank | nDCG, latency | the trade you are making, stated as two numbers |
| 16 | Calibrate a real judge against the frozen slice (*project*, extension 13) | judge | agreement with the slice | κ, and its drift over a week |
| 17 | Build the multi-turn eval set (*project*, extension 15) | eval | a new metric | whether any single-turn number survives |
| 18 | Put a real ANN backend behind the seam (*project*, extension 18) | index | recall against exact search at three `ef` values | the curve, not one point |
| 19 | Post one drill from a phone and one from a Codespace; compare the replies | community | the two threads | they should be identical; if not, that is a bug |
| 20 | Take one interview question from the wiki and answer it in ninety seconds on a thread | interview prep | `interview-bank/practice.py --drill models` | which mental model you named before answering |

The extension points with hypotheses and effort are in
[extension-points.md](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/docs/09-research/extension-points.md).
Claim one by opening an issue with the `type: extension` label.
