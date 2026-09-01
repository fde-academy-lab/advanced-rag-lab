"""
A tiny diagram language for the raglab notebooks.

Why not Mermaid? Because "one click and it runs" has to mean *everywhere* --
JupyterLab, VS Code, Colab, nbviewer, a PDF export, a GitHub preview. Mermaid
renders in some of those and silently shows raw text in the others. These
diagrams are drawn with matplotlib, so they are ordinary cell outputs: they
survive export, they print, and they are byte-identical between runs.

Every function here draws one of the shapes the course deck uses:

    flow()          a left-to-right pipeline                (deck: slides 5, 26, 52)
    funnel()        a narrowing sequence                    (deck: slide 6)
    stages()        stage cards with a knob line            (deck: slide 8)
    decision_tree() the spine-and-branch tree               (deck: slides 11, 24, 42, 69)
    hld()           a multi-lane architecture diagram       (deck: slides 22, 27, 67, 83)
    budget()        a stacked allocation bar                (deck: slides 48, 53)
    bars/lines()    measured results

House rule for this curriculum: a diagram either shows a mechanism or it does
not ship. None of these draw decoration.
"""
from __future__ import annotations

import textwrap

# ---------------------------------------------------------------- palette ----
# Derived from the course deck's palette, re-tuned for a light
# notebook background (the deck runs on --ink; notebooks run on white).
INK = "#101318"
INK_SOFT = "#3A414B"
MUTED = "#6B7480"
LINE = "#C9C4B8"
BONE = "#EDEAE3"
BONE_2 = "#F6F4EF"
AMBER = "#E9A83C"
AMBER_DEEP = "#B87A12"
CYAN = "#2F8CA3"
RED = "#CF4F35"
GREEN = "#3F8F6E"
VIOLET = "#6C5CE0"
WHITE = "#FFFFFF"

SEQ = [AMBER, CYAN, VIOLET, GREEN, RED, MUTED]

_FIG_N = 0
_FIG_PREFIX = ""


def reset_figures(prefix: str = "") -> None:
    """Restart figure numbering; call once at the top of a notebook."""
    global _FIG_N, _FIG_PREFIX
    _FIG_N = 0
    _FIG_PREFIX = prefix


def _next_label() -> str:
    global _FIG_N
    _FIG_N += 1
    return f"Figure {_FIG_PREFIX}{_FIG_N}"


def apply_style() -> None:
    import matplotlib as mpl

    mpl.rcParams.update(
        {
            "figure.facecolor": WHITE,
            "axes.facecolor": WHITE,
            "savefig.facecolor": WHITE,
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
            "text.color": INK,
            "axes.labelcolor": INK,
            "axes.edgecolor": LINE,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "axes.grid": True,
            "grid.color": "#E8E5DE",
            "grid.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 110,
            "savefig.bbox": "tight",
        }
    )


# ------------------------------------------------------------- primitives ----
# Geometry note. The canvas is 100 units wide and H units tall, and one y unit
# is UNIT_IN inches. Every height in this module is computed from that single
# constant, by one function that both measures and draws -- because the moment
# measuring and drawing use different arithmetic, text starts escaping its box
# and every diagram in the curriculum is subtly broken.
XMAX = 100.0
UNIT_IN = 0.085                      # inches per y unit
PT_PER_UNIT = UNIT_IN * 72.0         # points per y unit
LINE_FACTOR = 1.30                   # line advance as a multiple of font size
CHAR_W = {"bold": 0.635, "regular": 0.560, "mono": 0.605}
PAD = 1.9                            # box padding, y units


def _canvas(height_units: float, fig_w: float = 12.0):
    """A blank drawing surface: x in [0, 100], y in [0, height_units], y down."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(fig_w, max(1.2, height_units * UNIT_IN)))
    ax.set_xlim(0, XMAX)
    ax.set_ylim(0, height_units)
    ax.invert_yaxis()                # draw top-down, which is how flowcharts read
    ax.axis("off")
    ax.set_facecolor(WHITE)
    ax.set_position([0, 0, 1, 1])    # no axes margins: the canvas is the figure
    fig._fde_w = fig_w
    return fig, ax


def _advance(fontsize):
    """Vertical distance between baselines, in y units."""
    return LINE_FACTOR * fontsize / PT_PER_UNIT


def _wrap(text, w_units, fontsize, fig_w, kind="regular"):
    pts = (w_units / XMAX) * fig_w * 72.0
    chars = max(6, int(pts / (fontsize * CHAR_W[kind])))
    out = []
    for para in str(text).split("\n"):
        out.extend(textwrap.wrap(para, chars) or [""])
    return out


def _lines(w, fig_w, kicker=None, title=None, body=None, accent=False,
           title_size=10.5, body_size=9.0, kicker_size=7.6):
    """The single source of truth for box contents: (text, size, kind) tuples."""
    avail = w - 2 * PAD - (0.8 if accent else 0.0)
    out = []
    if kicker:
        out.append((str(kicker).upper(), kicker_size, "mono", MUTED, "normal"))
    if title:
        for ln in _wrap(title, avail, title_size, fig_w, "bold"):
            out.append((ln, title_size, "bold", None, "bold"))
    if body:
        for ln in _wrap(body, avail, body_size, fig_w, "regular"):
            out.append((ln, body_size, "regular", None, "normal"))
    return out


def _stack_height(lines, extra=0.0):
    if not lines:
        return 2 * PAD + extra
    h = sum(_advance(sz) for _, sz, _, _, _ in lines)
    return h + 2 * PAD + extra


def _box_height(w, title=None, body=None, kicker=None, fig_w=12.0,
                title_size=10.5, body_size=9.0, kicker_size=7.6, accent=False, extra=0.0):
    return _stack_height(_lines(w, fig_w, kicker, title, body, accent,
                                title_size, body_size, kicker_size), extra)


def _box(ax, x, y, w, h, title=None, body=None, kicker=None, fill=BONE_2, edge=LINE,
         accent=None, title_color=INK, body_color=INK_SOFT, title_size=10.5, body_size=9.0,
         kicker_size=7.6, lw=1.0, align="left"):
    """One rectangle with an optional kicker / title / body stack."""
    from matplotlib.patches import Rectangle

    fig_w = ax.figure._fde_w
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fill, edgecolor=edge, linewidth=lw, zorder=2))
    if accent:
        ax.add_patch(Rectangle((x, y), 0.5, h, facecolor=accent, edgecolor="none", zorder=3))

    lines = _lines(w, fig_w, kicker, title, body, bool(accent), title_size, body_size,
                   kicker_size)
    cx = x + w / 2 if align == "center" else x + PAD + (0.8 if accent else 0.0)
    ha = "center" if align == "center" else "left"
    cursor = y + PAD
    for text, size, kind, color, weight in lines:
        cursor += _advance(size) * 0.78          # baseline sits below the line top
        col = color or (title_color if kind == "bold" else body_color)
        ax.text(cx, cursor, text, fontsize=size, color=col, ha=ha, va="baseline",
                family="monospace" if kind == "mono" else None,
                fontweight="bold" if weight == "bold" else "normal", zorder=4)
        cursor += _advance(size) * 0.22
    return cursor


def _arrow(ax, x1, y1, x2, y2, color=AMBER, lw=1.6, label=None, label_color=MUTED, size=8.0):
    from matplotlib.patches import FancyArrowPatch

    ax.add_patch(
        FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12,
                        color=color, linewidth=lw, zorder=1, shrinkA=0, shrinkB=0)
    )
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if abs(x2 - x1) > abs(y2 - y1):          # horizontal arrow -> label above
            ax.text(mx, my - 0.7, label, fontsize=size, color=label_color, ha="center",
                    va="bottom", family="monospace", zorder=5)
        else:                                    # vertical arrow -> label to the right
            ax.text(mx + 1.0, my, label, fontsize=size, color=label_color, ha="left",
                    va="center", family="monospace", zorder=5)


def _frame(fig, ax, title, kicker, caption, source=None, label=True):
    """Common titling so every figure in the curriculum reads the same way.

    Titles and captions live outside the axes, in figure coordinates, so a tall
    diagram and a short one are captioned identically.
    """
    parts = []
    if label:
        parts.append(_next_label())
    if kicker:
        parts.append(kicker)
    head = "  ·  ".join(parts)
    fig_h_in = fig.get_size_inches()[1]
    step = 0.20 / fig_h_in                      # ~0.20 inch per heading line
    y = 1.0 + step * 1.7
    if head:
        fig.text(0.0, y, head.upper(), fontsize=8.0, color=AMBER_DEEP, family="monospace",
                 ha="left", va="baseline")
    if title:
        fig.text(0.0, 1.0 + step * 0.45, title, fontsize=13.5, color=INK, fontweight="bold",
                 ha="left", va="baseline")
    foot = [x for x in (caption, (f"Source: {source}" if source else "")) if x]
    if foot:
        fig.text(0.0, -step * 0.9, "  ".join(foot), fontsize=8.6, color=MUTED, ha="left",
                 va="top", wrap=True)
    return fig


def _show(fig):
    import matplotlib.pyplot as plt

    try:
        from IPython.display import display

        display(fig)
        plt.close(fig)
    except Exception:
        plt.close(fig)
    return None


# ------------------------------------------------------------------ flow ----
def flow(steps, title="", kicker="", caption="", source=None, highlight=-1, width=12.0,
         show=True):
    """A left-to-right pipeline. `steps` is a list of str or (title, body) pairs."""
    norm = []
    for i, s in enumerate(steps):
        if isinstance(s, (tuple, list)):
            t, b = (list(s) + [None])[:2]
        else:
            t, b = s, None
        norm.append((f"{i + 1:02d}", t, b))

    n = len(norm)
    gap = 3.4
    bw = (XMAX - 3 - gap * (n - 1)) / n
    hs = [_box_height(bw, t, b, k, width, accent=True) for k, t, b in norm]
    bh = max(max(hs), 10.0)
    H = bh + 4.0

    fig, ax = _canvas(H, width)
    x = 1.5
    top = 2.0
    for i, (k, t, b) in enumerate(norm):
        is_hl = (i == highlight) or (highlight == -1 and i == n - 1)
        _box(ax, x, top, bw, bh, title=t, body=b, kicker=k,
             fill=BONE if is_hl else BONE_2,
             edge=AMBER if is_hl else LINE,
             accent=AMBER if is_hl else None,
             lw=1.6 if is_hl else 1.0)
        if i < n - 1:
            _arrow(ax, x + bw + 0.5, top + bh / 2, x + bw + gap - 0.5, top + bh / 2)
        x += bw + gap
    _frame(fig, ax, title, kicker, caption, source)
    return _show(fig) if show else fig


def funnel(steps, title="", kicker="", caption="", source=None, width=12.0, show=True):
    """A narrowing sequence: each stage physically smaller than the last.

    `steps` is a list of (label, sublabel, relative_size in 0..1).
    """
    n = len(steps)
    gap = 3.0
    bw = (XMAX - 3 - gap * (n - 1)) / n
    Hbox = 36.0
    H = Hbox + 4.0
    fig, ax = _canvas(H, width)
    x = 1.5
    base = 2.0
    for i, (lab, sub, rel) in enumerate(steps):
        h = max(_box_height(bw, lab, sub, None, width) + 1.0, Hbox * float(rel))
        y = base + (Hbox - h)
        last = i == n - 1
        _box(ax, x, y, bw, h, title=lab, body=sub,
             fill=AMBER if last else BONE_2,
             edge=AMBER if last else LINE,
             title_color=INK, body_color=INK if last else MUTED,
             lw=1.4 if last else 1.0)
        if i < n - 1:
            _arrow(ax, x + bw + 0.4, base + Hbox - 3.0, x + bw + gap - 0.4, base + Hbox - 3.0,
                   color=MUTED, lw=1.2)
        x += bw + gap
    _frame(fig, ax, title, kicker, caption, source)
    return _show(fig) if show else fig


def stages(items, title="", kicker="", caption="", source=None, width=12.0, show=True):
    """Stage cards with a monospace 'knob' footer. `items`: dicts with
    keys stage, name, body, knob, and optional tone ('hot' | 'cool')."""
    n = len(items)
    gap = 2.6
    bw = (XMAX - 3 - gap * (n - 1)) / n
    knob_lines = [len(_wrap("knob: " + it["knob"], bw - 2 * PAD - 0.8, 7.6, width, "mono"))
                  if it.get("knob") else 0 for it in items]
    hs = [_box_height(bw, it["name"], it.get("body"), it.get("stage"), width, accent=True,
                      extra=(_advance(7.6) * kl + 1.4) if kl else 0.0)
          for it, kl in zip(items, knob_lines)]
    bh = max(hs)
    H = bh + 4.0
    fig, ax = _canvas(H, width)
    x = 1.5
    top = 2.0
    tones = {"hot": RED, "cool": CYAN, "amber": AMBER, "green": GREEN}
    for it, kl in zip(items, knob_lines):
        col = tones.get(it.get("tone", "amber"), AMBER)
        _box(ax, x, top, bw, bh, title=it["name"], body=it.get("body"), kicker=it.get("stage"),
             fill=BONE_2, edge=LINE, accent=col)
        if kl:
            cursor = top + bh - PAD - _advance(7.6) * (kl - 1)
            for ln in _wrap("knob: " + it["knob"], bw - 2 * PAD - 0.8, 7.6, width, "mono"):
                ax.text(x + PAD + 0.8, cursor, ln, fontsize=7.6, color=col, family="monospace",
                        va="baseline", zorder=5)
                cursor += _advance(7.6)
        x += bw + gap
    _frame(fig, ax, title, kicker, caption, source)
    return _show(fig) if show else fig


def hld(lanes, title="", kicker="", caption="", source=None, width=12.0, show=True):
    """A multi-lane high-level design.

    `lanes`: list of dicts {name, note, nodes:[str|(title,body)], tone}
    Nodes inside a lane are chained left-to-right with arrows.
    """
    fig_w = width
    lane_h = []
    for ln in lanes:
        nodes = ln["nodes"]
        n = max(1, len(nodes))
        gap = 1.8
        bw = (XMAX - 4 - gap * (n - 1)) / n
        hs = []
        for nd in nodes:
            t, b = (nd if isinstance(nd, (tuple, list)) else (nd, None))
            hs.append(_box_height(bw, t, b, None, fig_w, title_size=9.0, body_size=7.8,
                                  accent=True))
        lane_h.append((max(hs), bw, gap))
    LANE_HEAD = 3.6
    H = sum(h for h, _, _ in lane_h) + (LANE_HEAD + 3.0) * len(lanes) + 1.5
    fig, ax = _canvas(H, fig_w)

    tones = {"index": CYAN, "store": VIOLET, "query": AMBER, "control": GREEN, "warn": RED}
    y = 3.0
    for ln, (bh, bw, gap) in zip(lanes, lane_h):
        col = tones.get(ln.get("tone", "query"), AMBER)
        ax.text(1.5, y, ln["name"].upper(), fontsize=8.4, color=col, family="monospace",
                fontweight="bold", va="baseline")
        if ln.get("note"):
            ax.text(1.5 + len(ln["name"]) * 0.60 + 2.0, y, ln["note"], fontsize=7.8,
                    color=MUTED, family="monospace", va="baseline")
        ax.plot([1.5, XMAX - 1.5], [y + 1.0, y + 1.0], color=LINE, lw=0.9, zorder=0)
        x = 2.0
        nodes = ln["nodes"]
        top = y + 2.4
        for i, nd in enumerate(nodes):
            t, b = (nd if isinstance(nd, (tuple, list)) else (nd, None))
            _box(ax, x, top, bw, bh, title=t, body=b, fill=BONE_2, edge=LINE, accent=col,
                 title_size=9.0, body_size=7.8)
            if i < len(nodes) - 1 and ln.get("chain", True):
                _arrow(ax, x + bw + 0.2, top + bh / 2, x + bw + gap - 0.2, top + bh / 2,
                       color=col, lw=1.2)
            x += bw + gap
        y = top + bh + LANE_HEAD
    _frame(fig, ax, title, kicker, caption, source)
    return _show(fig) if show else fig


def decision_tree(tree, title=None, kicker="Decision tree", caption=None, source=None,
                  width=12.0, path=None, show=True):
    """Render a DecisionTree (see raglab.trees).

    `path` optionally highlights the branch a real case actually took, which is
    what turns a poster into a debugger.
    """
    nodes = tree.nodes
    fig_w = width
    qw, ow, gap = 47.0, 44.0, 6.0
    heights = []
    for i, nd in enumerate(nodes):
        qh = _box_height(qw, nd.question, None, f"Q{i + 1}", fig_w, accent=True)
        oh = _box_height(ow, nd.outcome, nd.why or None, None, fig_w,
                         title_size=9.4, body_size=8.0)
        heights.append(max(qh, oh, 8.0))
    dh = _box_height(XMAX - 3, tree.default, tree.default_why or None,
                     "Default / all answers exhausted", fig_w, accent=True)
    STEP = 4.6
    H = sum(heights) + STEP * len(nodes) + dh + 2.5
    fig, ax = _canvas(H, fig_w)

    # A path that fell through to the default has exit_index None, which must read as
    # "past every node", not as a missing key.
    exit_at = 10**9
    if path is not None and path.get("exit_index") is not None:
        exit_at = path["exit_index"]

    y = 1.5
    for i, (nd, h) in enumerate(zip(nodes, heights)):
        taken = path is not None and path.get("exit_index") == i
        onpath = path is not None and exit_at >= i
        q_edge = AMBER if taken else (INK_SOFT if onpath else LINE)
        _box(ax, 1.5, y, qw, h, title=nd.question, kicker=f"Q{i + 1}", fill=BONE_2,
             edge=q_edge, accent=AMBER if taken else CYAN, lw=1.7 if taken else 1.0)
        _arrow(ax, 1.5 + qw + 0.4, y + h / 2, 1.5 + qw + gap - 0.4, y + h / 2,
               color=RED if taken else LINE, lw=1.8 if taken else 1.1, label=nd.branch,
               label_color=RED if taken else MUTED)
        _box(ax, 1.5 + qw + gap, y, ow, h, title=nd.outcome, body=nd.why or None,
             fill="#FBEFE2" if taken else WHITE, edge=RED if taken else LINE,
             lw=1.7 if taken else 1.0, title_size=9.4, body_size=8.0)
        nxt = y + h + STEP
        cont_col = AMBER if (path is None or exit_at > i) else LINE
        _arrow(ax, 1.5 + qw / 2, y + h + 0.3, 1.5 + qw / 2, nxt - 0.3,
               color=cont_col, lw=1.5, label=nd.continues)
        y = nxt
    reached = path is not None and path.get("exit_index") is None
    _box(ax, 1.5, y, XMAX - 3, dh, title=tree.default, body=tree.default_why or None,
         kicker="Default / all answers exhausted",
         fill="#FBEFE2" if reached else BONE, edge=AMBER if reached else LINE,
         lw=1.7 if reached else 1.2, accent=AMBER)
    _frame(fig, ax, title or tree.title, kicker, caption or tree.caption, source or tree.source)
    return _show(fig) if show else fig


def budget(items, total=None, unit="", title="", kicker="Engineering budget", caption="",
           source=None, width=12.0, show=True):
    """A stacked allocation bar: how one fixed budget gets spent.

    `items`: list of (label, amount) or (label, amount, color).
    """
    import matplotlib.pyplot as plt

    labels = [i[0] for i in items]
    vals = [float(i[1]) for i in items]
    cols = [i[2] if len(i) > 2 else SEQ[k % len(SEQ)] for k, i in enumerate(items)]
    tot = float(total) if total else sum(vals)

    fig, (ax, ax2) = plt.subplots(
        2, 1, figsize=(width, 3.5), gridspec_kw={"height_ratios": [1.05, 1.5], "hspace": 0.55}
    )
    fig._fde_w = width
    left = 0.0
    for lab, v, c in zip(labels, vals, cols):
        ax.barh([0], [v], left=[left], color=c, edgecolor=WHITE, linewidth=1.4, height=0.55)
        if v / tot > 0.055:
            ax.text(left + v / 2, 0, f"{v:,.0f}", ha="center", va="center", fontsize=8.5,
                    color=WHITE, fontweight="bold")
        left += v
    ax.set_xlim(0, tot)
    ax.set_ylim(-0.5, 0.5)
    ax.set_yticks([])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlabel(f"cumulative {unit}".strip(), fontsize=9, color=MUTED)
    if total and sum(vals) < tot:
        ax.barh([0], [tot - sum(vals)], left=[sum(vals)], color="#E8E5DE", height=0.55)

    order = list(range(len(labels)))[::-1]
    ax2.barh([labels[i] for i in order], [vals[i] for i in order],
             color=[cols[i] for i in order], height=0.62)
    for i, idx in enumerate(order):
        ax2.text(vals[idx] + tot * 0.008, i, f"{vals[idx]:,.0f} {unit}  ({vals[idx] / tot:.0%})",
                 va="center", fontsize=8.6, color=INK_SOFT)
    ax2.set_xlim(0, max(vals) * 1.35)
    ax2.grid(axis="y", visible=False)
    ax2.tick_params(labelsize=9)
    for s in ax2.spines.values():
        s.set_visible(False)
    _frame(fig, ax, title, kicker, caption, source)
    return _show(fig) if show else fig


def bars(labels, series, title="", kicker="Measured", caption="", source=None, ylabel="",
         width=12.0, height=3.4, annotate=True, ylim=None, hline=None, hline_label="",
         show=True):
    """Grouped bars. `series` is {name: [values]} or a plain list."""
    import matplotlib.pyplot as plt
    import numpy as np

    if not isinstance(series, dict):
        series = {"": list(series)}
    fig, ax = plt.subplots(figsize=(width, height))
    fig._fde_w = width
    n = len(series)
    idx = np.arange(len(labels))
    w = 0.8 / n
    for k, (name, vals) in enumerate(series.items()):
        pos = idx - 0.4 + w * (k + 0.5)
        ax.bar(pos, vals, width=w * 0.92, label=name or None, color=SEQ[k % len(SEQ)])
        if annotate:
            for p, v in zip(pos, vals):
                ax.text(p, v, f"{v:.3g}", ha="center", va="bottom", fontsize=8.2, color=INK_SOFT)
    ax.set_xticks(idx)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.grid(axis="x", visible=False)
    if ylim:
        ax.set_ylim(*ylim)
    if hline is not None:
        ax.axhline(hline, color=RED, ls="--", lw=1.2)
        ax.text(len(labels) - 0.45, hline, "  " + hline_label, color=RED, fontsize=8.4,
                va="bottom", ha="right")
    if n > 1:
        ax.legend(frameon=False, fontsize=9, ncol=min(n, 4))
    _frame(fig, ax, title, kicker, caption, source)
    return _show(fig) if show else fig


def lines(x, series, title="", kicker="Measured", caption="", source=None, xlabel="", ylabel="",
          width=12.0, height=3.6, markers=True, vline=None, vline_label="", annotate_last=True,
          show=True):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(width, height))
    fig._fde_w = width
    for k, (name, ys) in enumerate(series.items()):
        ax.plot(x, ys, marker="o" if markers else None, ms=4.2, lw=1.9,
                color=SEQ[k % len(SEQ)], label=name)
        if annotate_last:
            ax.text(x[-1], ys[-1], f"  {ys[-1]:.3g}", fontsize=8.4, color=SEQ[k % len(SEQ)],
                    va="center")
    if vline is not None:
        ax.axvline(vline, color=RED, ls="--", lw=1.2)
        ax.text(vline, ax.get_ylim()[1], " " + vline_label, color=RED, fontsize=8.4, va="top")
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.legend(frameon=False, fontsize=9, ncol=min(len(series), 4))
    _frame(fig, ax, title, kicker, caption, source)
    return _show(fig) if show else fig


def scatter_frontier(points, title="", kicker="Tradeoff frontier", caption="", source=None,
                     xlabel="", ylabel="", width=11.0, height=4.2, chosen=None, show=True):
    """Cost/quality (or latency/quality) frontier with named operating points.

    `points`: list of (name, x, y).
    """
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(width, height))
    fig._fde_w = width
    for i, (name, px, py) in enumerate(points):
        is_ch = name == chosen
        ax.scatter([px], [py], s=180 if is_ch else 90,
                   color=AMBER if is_ch else CYAN,
                   edgecolor=INK if is_ch else "none", zorder=3, linewidth=1.4)
        ax.annotate(name, (px, py), textcoords="offset points", xytext=(9, 6),
                    fontsize=8.8, color=INK if is_ch else INK_SOFT,
                    fontweight="bold" if is_ch else "normal")
    xs = sorted(points, key=lambda p: p[1])
    ax.plot([p[1] for p in xs], [p[2] for p in xs], color=LINE, lw=1.2, zorder=1, ls="--")
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    _frame(fig, ax, title, kicker, caption, source)
    return _show(fig) if show else fig


def annotated_text(blocks, title="", kicker="", caption="", source=None, width=12.0, show=True):
    """A monospace panel with margin annotations -- used to dissect a packed
    prompt line by line (deck slide 55)."""
    fig_w = width
    left_w, right_w = 56.0, 40.0
    # Wrap every line to the panel width. A monospace panel that overflows its own
    # background is worse than no panel: it reads as a rendering bug in a figure whose
    # entire job is to show that provenance is legible.
    for b in blocks:
        b["_wrapped"] = []
        for raw in b["text"].split("\n"):
            b["_wrapped"].extend(_wrap(raw, left_w - 3.0, 8.2, fig_w, "mono") or [""])
    lines_ = [ln for b in blocks for ln in b["_wrapped"]]
    text_h = len(lines_) * 1.55 + 4.0
    notes = [b for b in blocks if b.get("note")]
    note_h = sum(_box_height(right_w, n.get("note_title"), n["note"], None, fig_w,
                             title_size=9.0, body_size=8.0) + 1.6
                 for n in notes)
    H = max(text_h, note_h) + 9.0
    fig, ax = _canvas(H, fig_w)
    from matplotlib.patches import Rectangle

    ax.add_patch(Rectangle((2.0, 6.0), left_w, text_h, facecolor="#14171C",
                           edgecolor=INK, zorder=2))
    y = 7.6
    anchors = {}
    for b in blocks:
        col = b.get("color", "#D8DEE6")
        start = y
        for ln in b["_wrapped"]:
            ax.text(3.4, y, ln, fontsize=8.2, color=col, family="monospace", va="top", zorder=4)
            y += 1.55
        anchors[id(b)] = (start + y) / 2 - 0.4
    ny = 6.0
    for b in notes:
        h = _box_height(right_w, b.get("note_title"), b["note"], None, fig_w,
                        title_size=9.0, body_size=8.0)
        _box(ax, 2.0 + left_w + 4.0, ny, right_w, h, title=b.get("note_title"), body=b["note"],
             fill=BONE_2, edge=LINE, accent=AMBER, title_size=9.0, body_size=8.0)
        ax.plot([2.0 + left_w, 2.0 + left_w + 4.0], [anchors[id(b)], ny + h / 2],
                color=AMBER, lw=1.0, ls=":", zorder=1)
        ny += h + 1.6
    _frame(fig, ax, title, kicker, caption, source)
    return _show(fig) if show else fig
