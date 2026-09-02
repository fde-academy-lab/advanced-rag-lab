"""Derived numbers, checked against the thing that derives them.

Two claims in this repository were wrong for months and neither was a typo. Both were figures
computed once, written into prose, and never re-derived — an aggregate table that said one
retriever beat another, and a `p^k` weighted over a question mixture that did not exist. CI could
not catch either, because CI compared the system against its own past self and never against
arithmetic.

So: every number the documentation quotes for the independence comparison is recomputed here from
the corpus and the committed baseline, and the test fails if the prose has drifted. It is fast —
the distribution needs chunking, not retrieval.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

NOTE = ROOT / "docs" / "09-research" / "measurements" / "multi-hop-independence.md"
QUOTING = [
    ROOT / "docs" / "04-evaluation" / "metrics.md",
    ROOT / "docs" / "01-architecture" / "lld" / "metrics.md",
    ROOT / "lab-simulator" / "units" / "E1-recall-that-means-something" / "BRIEF.md",
    ROOT / "lab-simulator" / "units" / "E1-recall-that-means-something" / "SOLUTION.md",
]

# The retracted figures. They may appear only inside an explicit retraction.
RETRACTED = ("0.6838", "128 single-hop", "61 two-hop", "18 three-or-more", "18 three-plus")
RETRACTION_WORDS = re.compile(
    r"corrected|retract|supersede|previously|used to read|published the opposite"
    r"|did not exist|got wrong|was wrong|the old version", re.I)
CONTEXT = 3          # a retracted figure may sit a few lines under the sentence retracting it


@pytest.fixture(scope="module")
def truth():
    from independence import summary
    return summary(measure=False)


def test_the_distribution_is_read_off_the_corpus(truth):
    """If the corpus generator changes, this is what tells you the prose is now stale."""
    sizes = truth["gold_pieces_per_question"]
    assert sum(sizes.values()) == truth["answerable"] == 207
    assert sizes == {"1": 21, "2": 59, "3": 21, "4": 100, "6": 6}, sizes


def test_the_prediction_and_the_verdict(truth):
    assert truth["prediction_macro"] == pytest.approx(0.4603, abs=5e-4)
    assert truth["full_chain_recall"] == pytest.approx(0.4686, abs=5e-4)
    # The sign is the whole finding: at or above independence means there is no correlated
    # failure structure to go looking for.
    assert truth["delta_macro"] > 0, (
        "measured full-chain recall has fallen below the independence prediction. That would be "
        "a real finding — correlated failure — and every document saying otherwise is now wrong.")


def test_the_exponent_is_pieces_not_hops():
    """The bug was `p^hops`. The corpus reports a hop field, and it is a different number."""
    from collections import Counter

    from raglab import chunking, corpus, metrics
    bundle = corpus.build_corpus()
    chunks = chunking.chunk_corpus(bundle.documents, strategy="structural")
    hops, pieces = Counter(), Counter()
    for q in bundle.questions:
        g = metrics.resolve_gold(q, chunks)[0]
        if g:
            hops[q.hops] += 1
            pieces[len(g)] += 1
    assert dict(hops) != dict(pieces), (
        "hops and gold-piece counts now agree, so the distinction this test guards is gone")
    assert max(pieces) > max(hops), "a question carries more evidence pieces than it has hops"


@pytest.mark.parametrize("path", QUOTING, ids=lambda p: p.name)
def test_the_prose_quotes_the_computed_numbers(path, truth):
    text = path.read_text()
    for value in (f"{truth['prediction_macro']:.4f}", f"{truth['full_chain_recall']:.4f}"):
        assert value in text, f"{path.name} does not quote {value}"


@pytest.mark.parametrize("path", QUOTING + [NOTE], ids=lambda p: p.name)
def test_retracted_figures_appear_only_inside_a_retraction(path):
    """The old numbers are allowed as history. They are not allowed as a claim.

    "Inside a retraction" means the line itself says so, it is quoted, or a line just above it
    does — a retracted figure usually sits a sentence or two under the sentence retracting it.
    """
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines):
        for bad in RETRACTED:
            if bad not in line:
                continue
            window = lines[max(0, i - CONTEXT):i + 1]
            excused = (line.lstrip().startswith(">")
                       or any(RETRACTION_WORDS.search(w) for w in window))
            assert excused, (
                f"{path.name}:{i + 1}: {bad!r} appears outside a retraction:\n  {line.strip()}")


def test_the_measurement_note_names_its_command():
    text = NOTE.read_text()
    assert "scripts/independence.py" in text
    assert "supersedes" in text.lower()


# ────────────────────────────────────────────────── the failure-overlap figure ──
FUSION_NOTE = ROOT / "docs" / "09-research" / "measurements" / "fusion-rules.md"
R3 = ROOT / "lab-simulator" / "units" / "R3-fusion-measured"


@pytest.fixture(scope="module")
def overlap():
    """Recomputed from the corpus. Slower than the independence fixture — it retrieves."""
    from failure_overlap import summary
    return summary()


def test_the_overlap_is_read_off_the_corpus(overlap):
    assert overlap["answerable"] == 207
    assert (overlap["dense_misses"], overlap["lexical_misses"], overlap["both_miss"]) \
        == (95, 102, 92)
    assert overlap["conditional"] == pytest.approx(0.9684, abs=5e-5)
    assert overlap["jaccard"] == pytest.approx(0.8762, abs=5e-5)


def test_the_conditional_and_the_jaccard_stay_far_enough_apart_to_grade_between(overlap):
    """R3 places a bar between them so a wrong formula fails on a number, not on style.

    If the two ever converge, that bar stops discriminating and the unit silently starts
    accepting the answer it was built to reject.
    """
    bar = 0.9000
    assert overlap["jaccard"] < bar < overlap["conditional"], (
        f"R3's bar of {bar} no longer separates the conditional ({overlap['conditional']}) "
        f"from the Jaccard ({overlap['jaccard']}), so the decoy formula now passes")
    assert f"{bar:.4f}" in (R3 / "unit.yaml").read_text()


@pytest.mark.parametrize("path", [FUSION_NOTE, R3 / "BRIEF.md", R3 / "unit.yaml"],
                         ids=lambda p: p.name)
def test_the_prose_quotes_the_computed_overlap(path, overlap):
    text = path.read_text()
    for value in (f"{overlap['conditional']:.4f}", f"{overlap['jaccard']:.4f}"):
        assert value in text, f"{path.name} does not quote {value}"


def test_the_correction_quotes_the_computed_overlap(overlap):
    """The correction posted to the live thread is prose too, and it drifts the same way."""
    import seed_content
    text = seed_content.CORRECTED[
        "RRF or weighted fusion — and what actually decided it on this corpus"]
    for value in (str(overlap["dense_misses"]), str(overlap["lexical_misses"]),
                  str(overlap["both_miss"]), f"{overlap['conditional']:.4f}",
                  f"{overlap['jaccard']:.4f}"):
        assert value in text, f"the correction does not quote {value}"


def test_the_fusion_note_names_its_commands():
    text = FUSION_NOTE.read_text()
    assert "scripts/failure_overlap.py" in text, (
        "the overlap figures are quoted without the command that regenerates them — which is "
        "the exact shape of the two claims this file exists to prevent")
    assert "run_eval.py --compare" in text


# ─────────────────────────────────── the retracted fusion claim, repository-wide ──
#
# The fusion retraction was applied where somebody remembered to look. It was still live in a
# case study that retracts it four lines earlier, in the premise of an exercise, in an
# interview bank, and in a LinkedIn template telling learners to publish it. A retraction that
# depends on remembering every copy is not a retraction; this is the thing that remembers.
FUSION_RETRACTED = (
    re.compile(r"RRF\s+(?:\w+\s+){0,3}(?:loses?|worse)\s+(?:than|to)\s+BM25", re.I),
    re.compile(r"equal[- ]weight\s+RRF\s+(?:was|is)\s+worse", re.I),
    re.compile(r"(?:LSA\s+)?dense\s+leg\s+is\s+(?:materially\s+|genuinely\s+)?weaker", re.I),
    re.compile(r"dense\s+leg\s+is\s+the\s+weak(?:er)?\s+(?:one|leg)", re.I),
    re.compile(r"offline\s+LSA\s+encoder\s+is\s+(?:genuinely\s+)?weaker", re.I),
)
# A negation is not an assertion. "RRF does not lose to BM25" is the correction.
NEGATED = re.compile(r"\b(?:does|did|do)\s+not\b|\bnever\b|\bisn't\b|\bdoesn't\b", re.I)
SEARCHED = ("docs", "concepts-and-case-studies", "interview-bank", "notebooks",
            "lab-simulator", "scripts", "raglab")
EXCUSED = re.compile(
    r"retract|corrected|supersede|previously|used to (?:read|say)|was wrong|it was wrong"
    r"|no longer|until 2026|the old version|published the opposite|does not reproduce"
    r"|withdrawn|I now know|since learned|repeating what|claimed \| measured"
    r"|not consistent with|is the \*\*strong\*\* one|does not lose", re.I)
CONTEXT_LINES = 8


def _readable_lines(path) -> list[str]:
    """The prose, not the container.

    A notebook is JSON, so every line of it carries escaped quotes — which made the
    quoted-therefore-excused rule excuse the whole file, including a capstone cell that
    asserted the retracted claim as a rejected alternative. Read the cells instead.
    """
    if path.suffix != ".ipynb":
        return path.read_text(encoding="utf-8").splitlines()
    import json
    nb = json.loads(path.read_text(encoding="utf-8"))
    out: list[str] = []
    for cell in nb.get("cells", []):
        src = cell.get("source") or []
        out.extend("".join(src).splitlines() if isinstance(src, list) else src.splitlines())
    return out


def _enclosing_thread_title(lines, i) -> str | None:
    """The nearest `"title": "..."` above line `i` in a seed module."""
    for j in range(i, -1, -1):
        m = re.search(r'"title":\s*"((?:[^"\\\\]|\\\\.)*)"', lines[j])
        if m:
            # Only the two escapes a Python string literal needs here. `unicode_escape`
            # would round-trip the UTF-8 em dash in these titles through latin-1 and
            # silently produce a title that matches nothing.
            return m.group(1).replace('\\"', '"').replace("\\\\", "\\")
    return None


def _covered_by_a_correction(path, lines, i) -> bool:
    """A seeded reply may carry the retracted claim — if the thread has a correction.

    The fusion thread's accepted answer *is* the retracted mechanism. That is deliberate: it is
    the artefact `CORRECTED` corrects, and deleting it would delete the evidence that a roomful
    of people found it convincing. So the rule is not "never appears" but **"never appears
    without a correction registered for the thread it is in"**, which is a stronger invariant
    than a suppression and fails the moment somebody removes the correction.
    """
    if path.name != "seed_content.py" and path.parent.name != "seed":
        return False
    import seed_content
    title = _enclosing_thread_title(lines, i)
    if title is None:
        return False
    canonical = seed_content.RENAMED.get(title, title)
    return canonical in seed_content.CORRECTED


def _prose_files():
    for top in SEARCHED:
        root = ROOT / top
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.suffix in {".md", ".py", ".ipynb"} and "__pycache__" not in path.parts:
                yield path


@pytest.mark.parametrize("path", list(_prose_files()),
                         ids=lambda p: str(p.relative_to(ROOT)))
def test_the_retracted_fusion_claim_appears_only_inside_a_retraction(path):
    """It may be quoted as history. It may not be asserted.

    Excused when the line negates the claim, quotes it, or sits within a few lines of a
    sentence withdrawing it — a correction usually sits a sentence or two from what it
    corrects. The window is whitespace-normalised because these files are hard-wrapped, so
    "It was\nwrong." has to read as "it was wrong".
    """
    lines = _readable_lines(path)
    for i, line in enumerate(lines):
        if not any(p.search(line) for p in FUSION_RETRACTED):
            continue
        if NEGATED.search(line):
            continue
        # A blockquote is NOT excused on its own. The worst instance the audit found was a
        # LinkedIn post template — a blockquote telling learners to publish the claim — so
        # "it is quoted" has to mean "quoted and marked", which the window below decides.
        if "*" in line.split("|")[0] and "|" in line:
            continue                     # a claimed/measured table row: the correction is beside it
        if '"' in line and path.suffix != ".ipynb":
            continue                     # somebody quoting the claim in order to reject it
        if _covered_by_a_correction(path, lines, i):
            continue
        window = " ".join(lines[max(0, i - CONTEXT_LINES):i + CONTEXT_LINES + 1]).replace("\\n", " ")
        assert EXCUSED.search(" ".join(window.split())), (
            f"{path.relative_to(ROOT)}:{i + 1} asserts a claim retracted on 2026-09-01:\n"
            f"  {line.strip()[:120]}\n"
            "Measured: RRF beats BM25 by +0.0624; the LSA leg is the stronger of the two; "
            "fusion does not separate from it because the legs fail on the same queries "
            "(overlap 0.9684). See ADR-0015.")


# ──────────────────────────────────── the answer drills' keys, against the notes ──
#
# An `answer` drill pins measured values inside its check.py so it can grade in seconds. A
# pinned number is exactly the kind that drifts, so each key is held to the note or grid that
# regenerates it. If the note changes, the drill fails CI before it teaches a stale figure.
UNITS = ROOT / "lab-simulator" / "units"


def _pinned(path, name):
    """Import a check.py far enough to read its module-level constants."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_rd2_key_matches_the_fusion_note():
    mod = _pinned(UNITS / "RD2-predict-before-you-fuse" / "check.py", "rd2")
    note = FUSION_NOTE.read_text(encoding="utf-8")
    rows = dict(re.findall(r"^(bm25|dense|rrf)\s+(\d\.\d{4})", note, re.M))
    assert rows, "the fusion note's table has changed shape"
    for arm, want in rows.items():
        assert mod.MEASURED[arm] == pytest.approx(float(want), abs=5e-5), (
            f"RD2 pins {arm}={mod.MEASURED[arm]} and the note says {want}")
    assert "(−0.0101, +0.0109)" in note, "the dense→rrf interval RD2 quotes has moved"


def test_xd1_key_matches_the_k_grid():
    mod = _pinned(UNITS / "XD1-which-way-does-precision-go" / "check.py", "xd1")
    grid = (ROOT / "docs" / "04-evaluation" / "metrics.md").read_text(encoding="utf-8")
    rows = {int(m.group(1)): (float(m.group(2)), float(m.group(5)))
            for m in re.finditer(r"^(\d+)\s+(\d\.\d{4})\s+(\d\.\d{4})\s+(\d\.\d{4})\s+(\d\.\d{4})",
                                 grid, re.M)}
    assert {5, 10} <= set(rows), f"the k grid no longer has k=5 and k=10: {sorted(rows)}"
    assert mod.K5 == {"evidence_recall": pytest.approx(rows[5][0]),
                      "context_precision": pytest.approx(rows[5][1])}
    assert mod.K10 == {"evidence_recall": pytest.approx(rows[10][0]),
                       "context_precision": pytest.approx(rows[10][1])}


def test_ed2_rows_match_the_fusion_note():
    mod = _pinned(UNITS / "ED2-which-deltas-are-real" / "check.py", "ed2")
    note = FUSION_NOTE.read_text(encoding="utf-8")
    wanted = {1: ("bm25 → rrf", "evidence recall"), 2: ("dense → rrf", "evidence recall"),
              3: ("rrf → w0.2", "nDCG"), 4: ("rrf → w0.5", "evidence recall")}
    for n, (pair, metric) in wanted.items():
        delta, lo, hi = mod.ROWS[n]
        pat = (rf"\|\s*\**{re.escape(pair)}\**\s*\|\s*\**{re.escape(metric)}\**\s*\|\s*\**"
               rf"([+−-]\d\.\d{{4}})\**\s*\|\s*\**\(([+−-]\d\.\d{{4}}),\s*([+−-]\d\.\d{{4}})\)")
        m = re.search(pat, note)
        assert m, f"row {n} ({pair}, {metric}) is not in the fusion note"
        got = [float(x.replace("−", "-")) for x in m.groups()]
        assert got == pytest.approx([delta, lo, hi], abs=5e-5), (
            f"ED2 row {n} pins {(delta, lo, hi)} and the note says {tuple(got)}")


def test_ed3_claims_quote_published_figures():
    """The write-up's sound claims must be sound, and its numbers must exist."""
    brief = (UNITS / "ED3-spot-the-measurement-smell" / "BRIEF.md").read_text(encoding="utf-8")
    note = FUSION_NOTE.read_text(encoding="utf-8")
    grid = (ROOT / "docs" / "04-evaluation" / "metrics.md").read_text(encoding="utf-8")
    for fig in ("0.7118", "0.7742", "+0.0624", "(+0.0407, +0.0857)", "0.4033", "0.4115"):
        assert fig in brief and fig in note, f"{fig} is in the brief but not in the note"
    for fig in ("0.3029", "0.1948", "0.6329", "0.7279"):
        assert fig in grid, f"{fig} is quoted by ED3 and is not in the k grid"
    baseline = json.loads((ROOT / ".github" / "eval-baseline.json").read_text())["metrics"]
    assert f"{baseline['full_chain_recall']:.4f}" in brief
    # the two figures that make claim 4 a smell must NOT be in any note — that is the point
    for fig in ("0.35", "0.7801"):
        assert fig not in note, f"{fig} has appeared in the fusion note; ED3's claim 4 is no longer a smell"
