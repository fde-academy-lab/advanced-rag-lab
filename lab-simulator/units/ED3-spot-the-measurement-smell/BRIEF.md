# ED3 · Five claims in a write-up. Three of them are the reason this repo has an ADR-0015.

**Track** evaluation · **Kind** drill · **Mode** answer · **Difficulty** hard · **~12 min**
**Prerequisites** ED2

---

An engineer posts this to Show and tell:

> **Fusion retune — results**
>
> **(1)** Switching from BM25 alone to equal-weight RRF raised evidence recall from 0.7118 to
> 0.7742, +0.0624 with a paired-bootstrap interval of (+0.0407, +0.0857) over 243 questions,
> `python scripts/run_eval.py --compare`.
>
> **(2)** Answer correctness improved from 0.4033 to 0.4115 on the same change, so the gain is
> reaching users.
>
> **(3)** Context precision fell from 0.3029 to 0.1948 when we widened k from 5 to 10, so the
> wider window is retrieving worse.
>
> **(4)** Our best α came out at 0.35 after sweeping on the frozen slice, which we recommend
> shipping; it scored 0.7801 there.
>
> **(5)** Full-chain recall at k=8 on the shipped configuration is 0.4686, from the committed
> baseline in `.github/eval-baseline.json`.

Which claims are **unsupported as stated**? For each, name its shape from this table:

| shape | what it looks like |
|---|---|
| `no-interval` | a delta quoted as a win with no interval, or one whose interval you can check straddles zero |
| `denominator` | a metric whose denominator is a config choice, read as a statement about quality |
| `tuned-on-frozen` | a parameter chosen on the slice it is then reported on |
| `no-command` | a figure with no command that regenerates it |
| `wrong-sign` | the direction of a delta read backwards |

<details><summary>Hint 1</summary>

Two of the five claims name a command or a committed file. Start by trusting those and
distrusting the rest, then check whether the distrust survives.
</details>

<details><summary>Hint 2</summary>

Claim 2's numbers are real. The question is whether a move from 0.4033 to 0.4115 is a
difference. ED2 told you how to answer that, and the interval is in the fusion note.
</details>
