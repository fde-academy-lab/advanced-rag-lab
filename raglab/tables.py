"""
Table rendering for the notebooks.

A rule this curriculum takes seriously: every diagram that encodes a decision
must also exist as a table. A picture is how you remember a rule; a table is
how you *apply* one at 2am with a failing query in front of you. So the
decision trees and decision matrices in `raglab.trees` render both ways from a
single definition, and this module is the table half.
"""
from __future__ import annotations

from . import viz

_TABLE_N = 0
_PREFIX = ""


def reset_tables(prefix: str = "") -> None:
    global _TABLE_N, _PREFIX
    _TABLE_N = 0
    _PREFIX = prefix


def _next_label() -> str:
    global _TABLE_N
    _TABLE_N += 1
    return f"Table {_PREFIX}{_TABLE_N}"


def df(rows, columns):
    import pandas as pd

    return pd.DataFrame(rows, columns=columns)


def styled(frame, title="", caption="", source=None, kicker="", label=True,
           emphasize=None, wrap_cols=None, index=False, align_left=None, highlight_rows=None):
    """Return a pandas Styler dressed in the deck's visual system.

    emphasize      : column name whose cells get the amber accent
    highlight_rows : callable(row) -> bool, marks rows worth staring at
    """

    head_bits = []
    if label:
        head_bits.append(_next_label())
    if kicker:
        head_bits.append(kicker)
    head = "  ·  ".join(head_bits)

    cap_html = ""
    if head or title:
        cap_html += (
            f"<div style='font:600 8.5px/1.4 ui-monospace,monospace;letter-spacing:.14em;"
            f"text-transform:uppercase;color:{viz.AMBER_DEEP};margin:14px 0 2px'>{head}</div>"
        )
        cap_html += (
            f"<div style='font:700 15px/1.3 system-ui,sans-serif;color:{viz.INK};"
            f"margin:0 0 8px'>{title}</div>"
        )
    foot = "  ".join([x for x in [caption, (f"Source: {source}" if source else "")] if x])

    sty = frame.style
    if not index:
        sty = sty.hide(axis="index")

    sty = sty.set_table_styles(
        [
            {"selector": "", "props": [("border-collapse", "collapse"),
                                       ("font-family", "system-ui,-apple-system,sans-serif"),
                                       ("font-size", "12.5px"),
                                       ("width", "100%")]},
            {"selector": "thead th", "props": [
                ("background", viz.INK), ("color", "#F2F4F7"),
                ("font", "600 10px/1.35 ui-monospace,monospace"),
                ("letter-spacing", ".09em"), ("text-transform", "uppercase"),
                ("text-align", "left"), ("padding", "9px 10px"),
                ("border-bottom", f"2px solid {viz.AMBER}"), ("vertical-align", "bottom")]},
            {"selector": "tbody td", "props": [
                ("padding", "8px 10px"), ("vertical-align", "top"),
                ("border-bottom", f"1px solid {viz.LINE}"), ("color", viz.INK_SOFT),
                ("line-height", "1.45")]},
            {"selector": "tbody tr:nth-child(even) td", "props": [("background", viz.BONE_2)]},
            {"selector": "tbody tr:hover td", "props": [("background", "#FBEFE2")]},
        ]
    )

    if emphasize and emphasize in frame.columns:
        sty = sty.set_properties(subset=[emphasize],
                                 **{"color": viz.INK, "font-weight": "600"})
    if align_left:
        sty = sty.set_properties(subset=align_left, **{"text-align": "left"})
    if highlight_rows is not None:
        def _row_style(row):
            hit = bool(highlight_rows(row))
            return [f"background:#FBEFE2;box-shadow:inset 3px 0 0 {viz.AMBER};" if hit else ""
                    for _ in row]
        sty = sty.apply(_row_style, axis=1)

    if wrap_cols:
        for c in wrap_cols:
            if c in frame.columns:
                sty = sty.set_properties(subset=[c], **{"max-width": "320px"})

    sty = sty.set_caption("")
    html_head = cap_html
    html_foot = (
        f"<div style='font:400 11px/1.5 system-ui,sans-serif;color:{viz.MUTED};"
        f"margin:6px 0 18px'>{foot}</div>" if foot else "<div style='margin-bottom:14px'></div>"
    )
    sty._raglab_head = html_head
    sty._fde_foot = html_foot
    return sty


def show(frame_or_styler, title="", caption="", source=None, kicker="", **kw):
    """Display a table with its heading and caption. Falls back to plain text."""
    try:
        from IPython.display import HTML, display
    except Exception:
        print(title)
        print(frame_or_styler)
        return

    sty = frame_or_styler
    if hasattr(sty, "columns"):  # a bare DataFrame
        sty = styled(sty, title=title, caption=caption, source=source, kicker=kicker, **kw)
    head = getattr(sty, "_raglab_head", "")
    foot = getattr(sty, "_fde_foot", "")
    display(HTML(head + sty.to_html() + foot))
    return None


def keyvalue(pairs, title="", caption="", kicker="", source=None):
    """A two-column fact panel -- used for run configs and measured summaries."""
    import pandas as pd

    frame = pd.DataFrame(list(pairs), columns=["Field", "Value"])
    show(frame, title=title, caption=caption, kicker=kicker, source=source, emphasize="Value")


def callout(text, kind="note", title=None):
    """A margin note. kind: note | warn | win | interview."""
    palette = {
        "note": (viz.CYAN, "#EAF4F7", "Engineering note"),
        "warn": (viz.RED, "#FBECE8", "Failure mode"),
        "win": (viz.GREEN, "#E9F3EE", "What good looks like"),
        "interview": (viz.VIOLET, "#EFEDFB", "In the interview"),
        "cost": (viz.AMBER_DEEP, "#FBF1E2", "Cost consequence"),
    }
    col, bg, default_title = palette.get(kind, palette["note"])
    try:
        from IPython.display import HTML, display

        display(HTML(
            f"<div style='border-left:4px solid {col};background:{bg};padding:11px 14px;"
            f"margin:12px 0;font:400 13px/1.55 system-ui,sans-serif;color:{viz.INK}'>"
            f"<div style='font:600 9.5px/1.3 ui-monospace,monospace;letter-spacing:.13em;"
            f"text-transform:uppercase;color:{col};margin-bottom:5px'>"
            f"{title or default_title}</div>{text}</div>"
        ))
    except Exception:
        print(f"[{(title or default_title).upper()}] {text}")
