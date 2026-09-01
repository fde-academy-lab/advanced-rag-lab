#!/usr/bin/env python3
"""Build the GitHub Pages site into _site/.

Two audiences, and the landing page has to serve both in about fifteen seconds:

  - someone sent the link by a recruiter or a colleague, who needs to know what this is;
  - a cohort member who wants a specific notebook.

So the page leads with the engagement and the three findings, not with a file listing. The
executed notebooks sit below that, where somebody looking for them will find them.

    python scripts/build_site.py --out _site            # landing page only (fast)
    python scripts/build_site.py --out _site --notebooks # + execute and export the notebooks
"""
from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NOTEBOOK_BLURBS = {
    "00_start_here": "The whole system in four seconds. Start here.",
    "01_retrieval_and_evaluation_foundations": "The recall budget: where evidence is lost between corpus and answer.",
    "02_multihop_rag_use_case": "Why per-piece recall and per-question recall are different questions.",
    "03_rag_system_design": "Design decisions, and when a vector database is the wrong answer.",
    "04_retrieval_methods_and_reranking": "BM25 from scratch, the ANN graph that collapses, fusion that loses.",
    "05_llm_context_design": "Token budgets, provenance, position sensitivity, abstention.",
    "06_evaluation_approaches": "Building a judge, then calibrating the judge.",
    "07_cost_and_token_optimization": "Four token categories and the cache rule that decides most of the bill.",
    "08_agentic_search_and_evaluation": "A loop with stop conditions that stop, scored on its trace.",
    "09_capstone_build": "Propose a change to Client Zero's system, measure it, defend it.",
}

FINDINGS = [
    ("Equal-weight RRF loses to BM25 alone.",
     "Weighted fusion at &alpha;&nbsp;=&nbsp;0.2 wins instead: evidence recall 0.7645 &rarr; 0.7891, "
     "[+0.008,&nbsp;+0.041], holding on the frozen slice. Fusing a strong retrieval leg with a weak "
     "one at equal weight moves the result toward the weak one.",
     "Returns to the expected result when both legs are comparably strong."),
    ("Comparison starvation does not reproduce.",
     "The corpus is generated from a fact graph that emits organisations on a balanced schedule, so "
     "the prevalence ratio is &asymp;&nbsp;1 and the precondition is absent by construction.",
     "Which is itself the finding: a balanced generator cannot measure imbalance failures, and most "
     "eval sets are built by balanced generators because those are easier to write."),
    ("No retrieval-score threshold separates answerable from unanswerable questions.",
     "Best F1 <b>0.38</b> across four signals. The null questions name real entities in the corpus's "
     "own vocabulary while genuine questions paraphrase &mdash; so the unanswerable ones are lexically "
     "<i>closer</i>.",
     "Any threshold on retrieval score is reading a feature with the wrong sign, and no amount of "
     "tuning repairs that."),
]

METRICS = [
    ("0.7645", "Evidence recall@8", "of gold evidence pieces reached the window"),
    ("0.4686", "Full-chain recall", "of questions had <em>every</em> required piece"),
    ("0.4115", "Answer correct", "judged against gold, abstentions included"),
    ("$0.0039", "Cost per eval run", "all 243 questions"),
]

CSS = """
:root{--bg:#fbfaf8;--fg:#16151a;--mut:#5c5a66;--line:#e3e0da;--card:#fff;--accent:#8a5a1a;
      --accent-bg:#fdf6ec;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){
  :root{--bg:#111014;--fg:#eceaf2;--mut:#a29fae;--line:#2a2833;--card:#191821;
        --accent:#e8ab5c;--accent-bg:#221a10}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
     font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,system-ui,sans-serif;
     -webkit-font-smoothing:antialiased}
.wrap{max-width:60rem;margin:0 auto;padding:0 1.5rem}
header{border-bottom:1px solid var(--line);padding:3.5rem 0 2.5rem;margin-bottom:3rem}
.kicker{font:600 .72rem/1 var(--mono);letter-spacing:.14em;text-transform:uppercase;
        color:var(--accent);margin:0 0 1rem}
h1{font-size:clamp(2rem,5vw,3rem);line-height:1.1;letter-spacing:-.025em;margin:0 0 1rem;font-weight:680}
.lede{font-size:1.15rem;color:var(--mut);max-width:44rem;margin:0 0 1.75rem}
.brief{border-left:3px solid var(--accent);background:var(--accent-bg);padding:1rem 1.25rem;
       margin:0 0 1.75rem;border-radius:0 6px 6px 0}
.brief p{margin:0;font-style:italic}
.brief cite{display:block;margin-top:.6rem;font-style:normal;font-size:.85rem;color:var(--mut)}
.btns{display:flex;flex-wrap:wrap;gap:.6rem}
a.btn{display:inline-block;padding:.55rem 1rem;border:1px solid var(--line);border-radius:7px;
      background:var(--card);color:var(--fg);text-decoration:none;font-size:.92rem;font-weight:500}
a.btn:hover{border-color:var(--accent);color:var(--accent)}
a.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
a.btn.primary:hover{color:#fff;opacity:.9}
h2{font-size:1.45rem;letter-spacing:-.015em;margin:3.5rem 0 .5rem;font-weight:650}
h2+.sub{color:var(--mut);margin:0 0 1.5rem;max-width:44rem}
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(11rem,1fr));gap:1rem;margin:1.5rem 0}
.metric{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:1.1rem}
.metric b{display:block;font:650 1.6rem/1 var(--mono);letter-spacing:-.02em;margin-bottom:.35rem}
.metric span{display:block;font-size:.85rem;font-weight:600}
.metric small{display:block;color:var(--mut);font-size:.78rem;margin-top:.2rem;line-height:1.45}
.finding{background:var(--card);border:1px solid var(--line);border-radius:9px;
         padding:1.25rem 1.4rem;margin-bottom:1rem}
.finding h3{margin:0 0 .5rem;font-size:1.02rem;font-weight:650}
.finding p{margin:0 0 .6rem;color:var(--mut);font-size:.94rem}
.finding .cond{margin:0;font-size:.87rem;color:var(--fg);border-top:1px solid var(--line);padding-top:.6rem}
.finding .cond b{color:var(--accent);font-weight:600}
ol.nb{list-style:none;padding:0;margin:1.5rem 0;counter-reset:nb -1}
ol.nb li{counter-increment:nb;border-bottom:1px solid var(--line);padding:.85rem 0 .85rem 3rem;position:relative}
ol.nb li::before{content:counter(nb,decimal-leading-zero);position:absolute;left:0;top:.9rem;
                 font:600 .8rem/1 var(--mono);color:var(--accent)}
ol.nb a{color:var(--fg);text-decoration:none;font-weight:600}
ol.nb a:hover{color:var(--accent)}
ol.nb span{display:block;color:var(--mut);font-size:.89rem;margin-top:.15rem}
ol.nb li.pending{color:var(--mut)}
.lab{display:grid;grid-template-columns:repeat(auto-fit,minmax(12rem,1fr));gap:1rem;margin:1.5rem 0}
.lab div{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:1.1rem}
.lab h3{margin:0 0 .35rem;font:650 .74rem/1 var(--mono);letter-spacing:.1em;
        text-transform:uppercase;color:var(--accent)}
.lab p{margin:0;font-size:.9rem;color:var(--mut)}
footer{border-top:1px solid var(--line);margin-top:4rem;padding:2rem 0 3rem;color:var(--mut);font-size:.86rem}
footer a{color:var(--mut)}
code{font:.9em var(--mono);background:var(--accent-bg);padding:.1em .35em;border-radius:4px}
"""


def repo() -> tuple[str, str]:
    try:
        d = json.loads((ROOT / ".identity.json").read_text())
        return d["owner"], d["repo"]
    except (OSError, KeyError, ValueError):
        return "fde-academy-lab", "advanced-rag-lab"


def landing(exported: list[str], owner: str, name: str) -> str:
    gh = f"https://github.com/{owner}/{name}"
    metrics = "\n".join(
        f'<div class="metric"><b>{v}</b><span>{lbl}</span><small>{note}</small></div>'
        for v, lbl, note in METRICS)
    findings = "\n".join(
        f'<div class="finding"><h3>{i}. {t}</h3><p>{body}</p>'
        f'<p class="cond"><b>Condition:</b> {cond}</p></div>'
        for i, (t, body, cond) in enumerate(FINDINGS, 1))

    items = []
    for stem, blurb in NOTEBOOK_BLURBS.items():
        title = stem.split("_", 1)[1].replace("_", " ")
        if f"{stem}.html" in exported:
            items.append(f'<li><a href="{stem}.html">{html.escape(title)}</a>'
                         f'<span>{html.escape(blurb)}</span></li>')
        else:
            items.append(f'<li class="pending"><a href="{gh}/blob/main/notebooks/{stem}.ipynb">'
                         f'{html.escape(title)}</a><span>{html.escape(blurb)}</span></li>')
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Advanced RAG &amp; Evals Lab — FDE Academy</title>
<meta name="description" content="The Client Zero engagement. A from-scratch retrieval stack and
the evaluation that judges it. Ten runnable notebooks, no vector database, no API key.">
<style>{CSS}</style></head><body>
<header><div class="wrap">
  <p class="kicker">FDE Academy · FDE LAB · Client Zero</p>
  <h1>Advanced RAG &amp; Evals Lab</h1>
  <p class="lede">The whole retrieval stack — BM25, dense, ANN, fusion, reranking — and the
  evaluation that decides whether any of it worked. No vector database, no framework, no API key.
  It runs in memory, in about ten seconds.</p>
  <div class="brief">
    <p>“We have all this documentation and our people can’t find answers in it. Can you put an AI
    search thing on it? How long would that take?”</p>
    <cite>— Client Zero. That is the entire brief, and it is how briefs actually arrive.</cite>
  </div>
  <div class="btns">
    <a class="btn primary" href="{gh}">Open on GitHub</a>
    <a class="btn" href="{gh}/blob/main/docs/00-orientation/client-zero.md">The engagement</a>
    <a class="btn" href="{gh}/discussions">Discussions</a>
    <a class="btn" href="{gh}/tree/main/interview-bank">Interview bank</a>
  </div>
</div></header>
<main class="wrap">

  <h2>LAB — Learn, Apply, Build</h2>
  <p class="sub">Three modes, and a fourth that is the reason people do the first three.</p>
  <div class="lab">
    <div><h3>Learn</h3><p>Ten notebooks. Run one, change a parameter, watch the metric move.</p></div>
    <div><h3>Apply</h3><p>Exercises run as Discussion threads. Approach before code, submission
    with an interval, one peer review owed before one is asked for.</p></div>
    <div><h3>Build</h3><p>A capstone change to Client Zero’s system, proposed, measured and
    defended.</p></div>
    <div><h3>Defend</h3><p>An interview bank with eight approach models and a ninety-second
    timer.</p></div>
  </div>

  <h2>Where it currently stands</h2>
  <p class="sub">Produced by <code>scripts/run_eval.py</code> over 243 questions. The gap between
  the first two numbers is the entire multi-hop problem, stated numerically.</p>
  <div class="metrics">{metrics}</div>

  <h2>Three results that contradict the expected answer</h2>
  <p class="sub">Each is measured, reproducible from a notebook cell, and names the condition under
  which the expected result returns. A negative finding without that condition is an anecdote.</p>
  {findings}

  <h2>The notebooks</h2>
  <p class="sub">Executed with their outputs. No dataset to download, no API key, no service to
  start — the entire retrieval stack lives inside <code>sqlite3.connect(":memory:")</code>.</p>
  <ol class="nb">{"".join(items)}</ol>

</main>
<footer><div class="wrap">
  <p><b>Client Zero is fictional.</b> Meridian Group and its subsidiaries are generated from a
  fact graph, so gold evidence is true by construction and nothing here is under anyone’s NDA.
  Any resemblance to a real organisation is a coincidence of the name generator.</p>
  <p>Apache-2.0 · <a href="{gh}">{owner}/{name}</a></p>
</div></footer>
</body></html>
"""


def export_notebooks(out: Path) -> list[str]:
    exported = []
    for nb in sorted((ROOT / "notebooks").glob("*.ipynb")):
        print(f"  executing {nb.name}", flush=True)
        res = subprocess.run(
            ["jupyter", "nbconvert", "--to", "html", "--execute",
             "--ExecutePreprocessor.timeout=900", "--output-dir", str(out), str(nb)],
            capture_output=True, text=True)
        if res.returncode == 0:
            exported.append(nb.stem + ".html")
        else:
            tail = (res.stderr or "").strip().splitlines()[-1:] or ["no stderr"]
            print(f"::warning::{nb.name} did not export — {tail[0]}")
    return exported


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="_site")
    ap.add_argument("--notebooks", action="store_true",
                    help="execute and export the notebooks (slow; the landing page works without)")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    exported = export_notebooks(out) if args.notebooks else []

    owner, name = repo()
    (out / "index.html").write_text(landing(exported, owner, name), encoding="utf-8")
    # Jekyll would otherwise skip files beginning with an underscore.
    (out / ".nojekyll").write_text("")
    print(f"\nbuilt {out}/index.html · {len(exported)} notebooks exported")
    return 0


if __name__ == "__main__":
    sys.exit(main())
