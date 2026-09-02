"""Invariants on the seeded discussion content.

Seed data is prose, so nothing else checks it. These are the mistakes that would ship silently:
a thread aimed at a category that does not exist, a reply from a persona with no entry in the
register, an accepted answer in a category that cannot accept one, and — the one that actually
happened — a relative link that 404s because Discussions resolve relative URLs against the
discussion, not the repository root.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import seed_content as content  # noqa: E402
from seed.personas import PERSONAS  # noqa: E402

THREADS = content.DISCUSSIONS
BUILT_IN = {"Announcements", "General", "Ideas", "Q&A", "Show and tell", "Polls"}
DECLARED = {name for name, *_ in content.CATEGORIES} | BUILT_IN
ANSWERABLE = {name for name, _emoji, _desc, fmt in content.CATEGORIES if fmt == "ANSWER"} | {"Q&A"}


def test_every_thread_targets_a_declared_category():
    unknown = {t["category"] for t in THREADS} - DECLARED
    assert not unknown, f"threads aimed at categories nobody creates: {sorted(unknown)}"


def test_every_author_and_replier_is_in_the_register():
    used = {t.get("author", "maintainer") for t in THREADS}
    used |= {r["by"] for t in THREADS for r in t.get("replies", [])}
    assert not used - set(PERSONAS), f"unknown personas: {sorted(used - set(PERSONAS))}"


def test_accepted_answers_only_in_answerable_categories():
    """Marking an answer in a non-answerable category is an API error, not a no-op."""
    for t in THREADS:
        if any(r.get("accepted") for r in t.get("replies", [])):
            assert t["category"] in ANSWERABLE, (
                f"“{t['title'][:50]}” marks an answer but {t['category']} is not answerable")


def test_at_most_one_accepted_answer_per_thread():
    for t in THREADS:
        n = sum(1 for r in t.get("replies", []) if r.get("accepted"))
        assert n <= 1, f"“{t['title'][:50]}” marks {n} answers"


def test_no_relative_repo_links_in_seeded_bodies():
    """Discussions resolve relative links against the discussion URL, so ../blob/main 404s."""
    bad = []
    for t in THREADS:
        for label, body in [("body", t["body"])] + [
                (f"reply/{r['by']}", r["body"]) for r in t.get("replies", [])]:
            if "../blob/" in body or "](docs/" in body:
                bad.append(f"{t['title'][:40]} · {label}")
    assert not bad, f"relative repo links that will 404 inside a Discussion: {bad}"


def test_no_links_to_the_pre_restructure_docs_layout():
    stale = [t["title"][:44] for t in THREADS
             if "/docs/adr/" in t["body"]
             or any("/docs/adr/" in r["body"] for r in t.get("replies", []))]
    assert not stale, f"links to docs/adr/, which moved to docs/01-architecture/adr/: {stale}"


@pytest.mark.parametrize("thread", THREADS, ids=lambda t: t["title"][:40])
def test_threads_carry_a_real_conversation(thread):
    """A thread with no replies is the defect this content set exists to fix."""
    if thread["category"] == "Announcements":
        return  # announcements are posts, not conversations
    assert thread.get("replies"), "no replies — this is a noticeboard post, not a thread"


def test_the_corpus_is_substantial_enough_to_set_a_standard():
    replies = sum(len(t.get("replies", [])) for t in THREADS)
    answers = sum(1 for t in THREADS for r in t.get("replies", []) if r.get("accepted"))
    assert len(THREADS) >= 25, len(THREADS)
    assert replies >= 60, replies
    assert answers >= 10, answers


# ------------------------------------------------- renames, labels, retirements

def test_every_rename_target_is_what_the_seed_now_asks_for():
    """RENAMED is a migration, not a second source of truth.

    Seeding is keyed by title. If the seed still asks for the OLD title, renaming the live
    thread makes the seeder create a second copy under the old name — the exact failure RENAMED
    exists to prevent.
    """
    import seed_content
    defined = {t["title"] for t in seed_content.DISCUSSIONS}
    for old, new in seed_content.RENAMED.items():
        assert new in defined, f"renamed to {new!r}, which the seed does not define"
        assert old not in defined, (
            f"{old!r} is renamed and still seeded — it would be recreated on the next run")


def test_no_rename_collides_with_another_rename():
    import seed_content
    targets = list(seed_content.RENAMED.values())
    assert len(set(targets)) == len(targets), "two threads renamed to the same title"


def test_worked_example_is_a_label_not_a_title_suffix():
    """It said nothing about the question and pushed the subject past where GitHub truncates."""
    import seed_content
    offenders = [t["title"] for t in seed_content.DISCUSSIONS
                 if "[worked example]" in t["title"]]
    assert not offenders, offenders
    assert any(name == "worked example" for name, *_ in seed_content.DISCUSSION_LABELS)


def test_every_labelled_title_exists_somewhere():
    """A label mapping keyed on a title nobody seeds is a silent no-op."""
    import seed_content
    known = ({t["title"] for t in seed_content.DISCUSSIONS}
             | set(seed_content.RENAMED) | set(seed_content.RETIRED))
    unknown = sorted(t for t in seed_content.THREAD_LABELS if t not in known)
    assert not unknown, unknown


def test_every_label_used_is_one_the_repository_defines():
    import seed_content
    defined = ({name for name, *_ in seed_content.DISCUSSION_LABELS}
               | {name for name, *_ in seed_content.LABELS})
    used = {l for labels in seed_content.THREAD_LABELS.values() for l in labels}
    assert used <= defined, sorted(used - defined)


def test_the_retracted_thread_is_labelled_as_such():
    """Whatever else it carries, a thread holding a withdrawn claim says so in its labels."""
    import seed_content
    for old in seed_content.RETIRED:
        assert "retracted" in seed_content.THREAD_LABELS.get(old, []), \
            f"{old!r} is retired but not labelled `retracted`"


def test_every_extra_reply_chain_finds_exactly_one_thread():
    """`threads_extra.REPLIES` is keyed by title PREFIX, so a rename silently orphans it.

    That is not hypothetical: renaming two titles to drop a `[worked example]` suffix left two
    threads with an empty reply list, and the only symptom was a thread that had gone quiet.
    """
    import seed_content
    from seed import threads_extra
    titles = [t["title"] for t in seed_content.DISCUSSIONS]
    for prefix in threads_extra.REPLIES:
        hits = [t for t in titles if t.startswith(prefix)]
        assert len(hits) == 1, (
            f"prefix {prefix!r} matches {len(hits)} threads. A prefix keyed on a title is broken "
            "by any rename, and the failure is silent — the thread simply has no conversation.")


# ──────────────────────────────────────────────────────── live corrections ──
def test_every_corrected_title_is_one_the_repository_seeds():
    """A correction keyed on a title nobody seeds posts nowhere and says nothing."""
    import seed_content
    known = {t["title"] for t in seed_content.DISCUSSIONS}
    unknown = sorted(t for t in seed_content.CORRECTED if t not in known)
    assert not unknown, unknown


def test_a_corrected_thread_is_labelled_retracted():
    """The correction and the label have to agree, or a filter on one misses the other."""
    import seed_content
    for title in seed_content.CORRECTED:
        assert "retracted" in seed_content.THREAD_LABELS.get(title, []), \
            f"{title!r} carries a correction but is not labelled `retracted`"


def test_correction_bodies_only_use_the_placeholders_that_are_supplied():
    """`.format(owner=…, repo=…)` on a body with a stray brace raises at seed time."""
    import string

    import seed_content
    for title, text in seed_content.CORRECTED.items():
        fields = {f for _, f, _, _ in string.Formatter().parse(text) if f}
        assert fields <= {"owner", "repo"}, f"{title!r} wants {sorted(fields - {'owner', 'repo'})}"
        text.format(owner="o", repo="r")          # raises on an unbalanced brace


def test_the_fusion_correction_quotes_the_measurement_note_verbatim():
    """The numbers in a correction must come from the note that regenerates them.

    This is the guard the retracted claim did not have. The original finding survived for
    months because the number lived only in prose — nothing tied it to a command, so nothing
    could notice when re-running the command disagreed. A correction that repeats the same
    mistake is worse than the mistake.
    """
    import pathlib
    import re

    import seed_content

    note = (pathlib.Path(__file__).resolve().parents[1]
            / "docs/09-research/measurements/fusion-rules.md").read_text(encoding="utf-8")
    rows = dict(re.findall(r"^(bm25|dense|rrf|w0\.2|w0\.5)\s+([\d.\s]+)$", note, re.M))
    assert len(rows) == 5, f"the note's table changed shape: {sorted(rows)}"

    text = seed_content.CORRECTED[
        "RRF or weighted fusion — and what actually decided it on this corpus"]
    quoted = dict(re.findall(r"^(bm25|dense|rrf|w0\.2|w0\.5)\b[^\n]*?((?:\s+\d\.\d{4}){3})$",
                             text, re.M))
    assert len(quoted) == 5, f"the correction's table changed shape: {sorted(quoted)}"

    for arm, figures in quoted.items():
        want = rows[arm].split()[:3]            # recall, full-chain, ndcg
        assert figures.split() == want, (
            f"{arm}: the correction says {figures.split()} and the measurement note that "
            f"regenerates it says {want}")


# ───────────────────────────────────────────────────────────── cross-links ──
def test_cross_links_point_at_threads_that_exist():
    """A see-also pointing at a title nobody seeds renders a link to nothing."""
    import seed_content
    known = ({t["title"] for t in seed_content.DISCUSSIONS}
             | set(seed_content.RENAMED) | set(seed_content.RETIRED)
             | {"Welcome to advanced-rag-lab Discussions!"})   # GitHub's own, never seeded
    for title, (_reason, others) in seed_content.SEE_ALSO.items():
        assert title in known, f"see-also is keyed on {title!r}, which nothing seeds"
        for other in others:
            assert other in known, f"{title!r} points at {other!r}, which nothing seeds"
        assert title not in others, f"{title!r} points at itself"


def test_cross_links_between_seeded_threads_are_reciprocal():
    """A one-way link is found from one side only, which is the half that already knew."""
    import seed_content
    links = {t: set(o) for t, (_r, o) in seed_content.SEE_ALSO.items()}
    for title, others in links.items():
        for other in others:
            if other not in links:
                # GitHub's boilerplate welcome post is deliberately one-way: the maintained
                # thread should not carry a pointer back to the one nobody maintains.
                assert title == "Welcome to advanced-rag-lab Discussions!", (
                    f"{title!r} points at {other!r} and gets nothing back")
                continue
            assert title in links[other], f"{other!r} does not point back at {title!r}"


# ────────────────────────────────────────── the second wave of seeded threads ──
def test_every_thread_is_labelled():
    """An unlabelled thread is invisible to every filter the guide teaches."""
    import seed_content
    have = set(seed_content.THREAD_LABELS)
    missing = sorted(t["title"] for t in seed_content.DISCUSSIONS if t["title"] not in have)
    assert not missing, missing


def test_no_two_threads_share_a_title():
    """Seeding is keyed by title, so a collision silently seeds one and skips the other."""
    import collections

    import seed_content
    counts = collections.Counter(t["title"] for t in seed_content.DISCUSSIONS)
    assert not [t for t, n in counts.items() if n > 1], \
        [t for t, n in counts.items() if n > 1]


def test_every_answerable_thread_has_an_accepted_reply():
    """A Q&A thread with no answer reads as unanswered and gets asked again next cohort."""
    import seed_content
    answerable = {n for n, _e, _d, fmt in seed_content.CATEGORIES if fmt == "ANSWER"} | {"Q&A"}
    naked = [t["title"] for t in seed_content.DISCUSSIONS
             if t["category"] in answerable
             and not any(r.get("accepted") for r in t.get("replies", []))]
    assert not naked, naked


def test_every_category_the_repository_creates_has_at_least_one_thread():
    """A category created by hand and then never used is a worse default than not creating it."""
    import seed_content
    seeded = {t["category"] for t in seed_content.DISCUSSIONS}
    empty = sorted({n for n, *_ in seed_content.CATEGORIES} - seeded)
    assert not empty, f"these categories exist in CATEGORIES and hold no seeded thread: {empty}"


def test_no_seeded_thread_quotes_a_figure_the_repository_cannot_justify():
    """Every multi-decimal figure has to be traceable to a file somebody can open.

    Not a spelling check — the two retracted claims were both fabricated decimals that read as
    measurements. Arithmetic worked in the open (a discount table, a DCG sum) is exempt only
    because it is checkable in the thread itself, so those live in ALLOWED with a reason.
    """
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parents[1]
    haystack = []
    for pattern in ("docs/**/*.md", "lab-simulator/**/*.md", "lab-simulator/**/*.yaml",
                    "lab-simulator/**/*.py", "raglab/*.py", "concepts-and-case-studies/**/*.md",
                    ".github/eval-baseline.json"):
        for f in root.glob(pattern):
            if "__pycache__" in f.parts:
                continue
            haystack.append(f.read_text(encoding="utf-8", errors="ignore"))
    corpus = "\n".join(haystack)

    # A figure is attested if it appears, or if a longer figure in the corpus rounds to it:
    # the baseline stores `884.0494` and the prose sensibly quotes `884.05`.
    attested = set(re.findall(r"\b\d+\.\d+\b", corpus))
    for value in list(attested):
        for places in (2, 3, 4):
            try:
                attested.add(f"{float(value):.{places}f}")
            except ValueError:                              # pragma: no cover
                pass

    # Arithmetic the thread shows its working for, checkable by the reader on the spot.
    ALLOWED = {
        # nDCG discount table and the worked DCG/IDCG sums in threads_math
        "0.1250", "0.2500", "0.3155", "0.3333", "0.4307", "0.5000", "0.6309", "1.0000",
        "1.8250", "2.0833", "2.3332", "2.5616", "0.8760", "0.9109",
        # BM25 saturation at k1=1.5, ceiling 2.5
        "1.4286", "1.6667", "1.9231", "2.1739", "2.4631",
        # the retracted p^hops arithmetic, quoted as history
        "0.6514", "97.856", "35.652", "8.043",
        # bar thresholds and quoted grader output
        "42.1600", "45.0000", "63.2250", "0.667",
        # the Week 3 standup's fusion figures, quoted verbatim in Week 6 in order to withdraw
        # them. They do not reproduce, which is the point of quoting them.
        "0.7891", "0.041",
    }
    # Scoped to the modules written against a verified-figures sheet. The earlier modules
    # carry figures nobody can now re-derive, which is a real debt and a separate piece of
    # work — failing this build on them would only teach people to delete the test.
    CHECKED = ("threads_general.py", "threads_reading.py", "threads_ideas.py",
               "threads_showandtell.py", "threads_labsim_more.py", "threads_clinic_more.py",
               "threads_qa_more.py", "threads_design_more.py", "threads_math.py",
               "threads_standup_more.py")
    dec = re.compile(r"\b\d+\.\d{2,4}\b")
    offenders = {}
    for name in CHECKED:
        text = (root / "scripts" / "seed" / name).read_text(encoding="utf-8")
        bad = sorted({d for d in dec.findall(text)
                      if d not in ALLOWED and d not in corpus and d not in attested})
        if bad:
            offenders[name] = bad
    assert not offenders, (
        "figures with nothing in the repository behind them:\n"
        + "\n".join(f"  {k}: {v}" for k, v in offenders.items()))


def test_the_drills_index_thread_names_every_drill():
    """The seeded drills thread is a table; a drill missing from it cannot be found from it."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lab-simulator"))
    import seed_content
    from labsim.registry import all_units
    thread = next(t for t in seed_content.DISCUSSIONS if t["title"].startswith("Drills — "))
    for u in all_units():
        if u.is_drill:
            assert f"`{u.uid}`" in thread["body"], f"{u.uid} is not in the drills index thread"
