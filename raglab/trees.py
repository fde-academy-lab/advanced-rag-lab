"""
Decision trees and decision matrices as *executable* objects.

A decision tree in a slide deck is a poster. The same tree defined here is
three things at once:

    tree.figure()          the poster            -- how you remember it
    tree.table()           the procedure         -- how you apply it
    tree.decide(context)   the running code      -- how the pipeline applies it

That third mode is the point. The fault-isolation tree from the deck is not
something a learner reads and nods at; in notebook 01 it is called on a real
failing query and it returns an owning stage. Once a decision tree can be
executed it can also be regression-tested, which is the difference between
engineering judgement and a wall poster.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from . import tables, viz


@dataclass
class Branch:
    """One question on the spine of a decision tree."""

    question: str
    branch: str              # label on the arrow that leaves the spine ("NO", "YES")
    outcome: str             # what you do when you leave here
    continues: str = ""      # label on the arrow that carries on downwards
    why: str = ""            # the reasoning -- shows in the table, not the poster
    knobs: str = ""          # the specific parameters this outcome lets you touch
    owner: str = ""          # which stage of the pipeline owns the fix
    test: Callable | None = None   # predicate(ctx) -> True means "exit here"
    terminal: bool = True    # False = record the finding and keep narrowing


@dataclass
class DecisionTree:
    key: str
    title: str
    nodes: list
    default: str
    default_why: str = ""
    caption: str = ""
    source: str = ""

    # ---------------------------------------------------------------- views --
    def figure(self, path=None, **kw):
        return viz.decision_tree(self, path=path, **kw)

    def table(self):
        import pandas as pd

        rows = []
        for i, n in enumerate(self.nodes, 1):
            rows.append({
                "#": f"Q{i}",
                "Question asked": n.question,
                "Answer that exits": n.branch,
                "Then do this": n.outcome,
                "Why it is the right call": n.why,
                "Knobs it unlocks": n.knobs,
                "Owning stage": n.owner,
                "Ends the walk?": "yes" if n.terminal else "no — narrows and continues",
            })
        rows.append({
            "#": "—",
            "Question asked": "All questions answered without exiting",
            "Answer that exits": "—",
            "Then do this": self.default,
            "Why it is the right call": self.default_why,
            "Knobs it unlocks": "",
            "Owning stage": "",
            "Ends the walk?": "yes",
        })
        return pd.DataFrame(rows)

    def show_table(self, title=None, caption=None, source=None):
        tables.show(
            self.table(),
            title=title or f"{self.title} — read as a procedure",
            kicker="Decision tree, tabulated",
            caption=caption or (
                "Same tree as the figure above. The figure is for recall; this table is what "
                "you actually run down when something is broken."),
            source=source or self.source,
            emphasize="Then do this",
        )

    # ------------------------------------------------------------ execution --
    def decide(self, ctx):
        """Walk the tree against a real case.

        Returns a dict with the exit index (None = fell through to the default),
        the outcome text, and a full trace of every question evaluated -- the
        trace is what makes the verdict auditable instead of merely plausible.
        """
        trace, findings = [], []
        for i, n in enumerate(self.nodes):
            if n.test is None:
                trace.append({"q": n.question, "evaluated": False, "exits": False,
                              "answer": "—", "note": "no predicate bound"})
                continue
            exits = bool(n.test(ctx))
            trace.append({"q": n.question, "evaluated": True, "exits": exits,
                          "answer": n.branch if exits else (n.continues.split() or ["—"])[0]})
            if exits:
                if not n.terminal:
                    # A classification step: it narrows the search without ending it.
                    findings.append(n.outcome)
                    continue
                return {"exit_index": i, "node": n, "outcome": n.outcome, "owner": n.owner,
                        "knobs": n.knobs, "why": n.why, "trace": trace, "tree": self.key,
                        "findings": findings}
        return {"exit_index": None, "node": None, "outcome": self.default, "owner": "",
                "knobs": "", "why": self.default_why, "trace": trace, "tree": self.key,
                "findings": findings}

    def explain(self, ctx, show_figure=True):
        """decide() + render the highlighted path + print the reasoning."""
        d = self.decide(ctx)
        if show_figure:
            self.figure(path=d, caption=f"Path taken for this case → {d['outcome']}")
        import pandas as pd

        rows = [{"Step": f"Q{i + 1}", "Question": t["q"],
                 "Answer": t.get("answer", "—"),
                 "Exits here?": "YES — this is the verdict" if t["exits"] else "no, keep walking"}
                for i, t in enumerate(d["trace"])]
        tables.show(pd.DataFrame(rows),
                    title="How the tree reached its verdict",
                    kicker="Executed decision tree",
                    caption=f"Verdict: {d['outcome']}"
                            + (f"  ·  Owning stage: {d['owner']}" if d["owner"] else "")
                            + (f"  ·  Knobs: {d['knobs']}" if d["knobs"] else ""),
                    emphasize="Answer")
        return d


@dataclass
class DecisionMatrix:
    """A comparison table where the columns are the axes of the decision."""

    key: str
    title: str
    columns: list
    rows: list
    caption: str = ""
    source: str = ""
    kicker: str = "Decision matrix"
    note: str = ""
    recommend: str | None = None   # value in column 0 that is the default choice

    def frame(self):
        import pandas as pd

        return pd.DataFrame(self.rows, columns=self.columns)

    def show(self, title=None, caption=None, highlight=None):
        first = self.columns[0]
        target = highlight if highlight is not None else self.recommend
        hl = (lambda r: str(r[first]) == str(target)) if target else None
        cap = caption or self.caption
        if target:
            cap = (cap + "  ") if cap else ""
            cap += ("Highlighted row = the default you should have to argue your "
                    f"way out of: {target}.")
        tables.show(self.frame(), title=title or self.title, kicker=self.kicker,
                    caption=cap, source=self.source,
                    emphasize=self.columns[0], highlight_rows=hl)
        if self.note:
            tables.callout(self.note, kind="note")


def score_matrix(matrix, weights, scores, title=None, chosen=None):
    """Turn a qualitative matrix into a defensible number.

    `weights` : {criterion: weight}
    `scores`  : {option: {criterion: 0..5}}
    Prints the weighted table and returns the ranking. The output of this is
    the sentence an interview panel is listening for: "I picked B, it scores
    4.1 against A's 3.6, and here is the criterion that decided it."
    """
    import pandas as pd

    tot_w = sum(weights.values())
    rows = []
    for opt, sc in scores.items():
        weighted = sum(sc.get(c, 0) * w for c, w in weights.items()) / tot_w
        row = {"Option": opt}
        row.update({f"{c} (w={w})": sc.get(c, 0) for c, w in weights.items()})
        row["Weighted score"] = round(weighted, 2)
        rows.append(row)
    frame = pd.DataFrame(rows).sort_values("Weighted score", ascending=False)
    best = frame.iloc[0]["Option"]
    tables.show(frame, title=title or "Weighted decision", kicker="Scored matrix",
                caption=(f"Highest weighted score: {best}."
                         + (f" Chosen: {chosen}." if chosen and chosen != best else "")),
                emphasize="Weighted score",
                highlight_rows=lambda r: r["Option"] == (chosen or best))
    return frame
