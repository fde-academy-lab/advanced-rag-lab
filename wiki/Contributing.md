# Contributing to this wiki

**Takeaway:** the wiki is generated from the repository. Pages live under
[`wiki/`](https://github.com/fde-academy-lab/advanced-rag-lab/tree/main/wiki), are link-checked
and tested like every other document, and are pushed here by a workflow on every merge to
`main`. Editing a page here directly works for a day and is then overwritten.

## To change a page

1. Open the file under `wiki/` in the repository, click the pencil, edit, and propose the change.
   A maintainer merges it; the wiki updates within a couple of minutes.
2. A link to another wiki page is written with the page's file name, `How-To.md` for
   example, so the repository's link checker can verify it; the sync strips the `.md` on the
   way to the wiki. Links to repository files are absolute
   `https://github.com/...` URLs, because the wiki is a separate site.

## To add a page

1. Add `wiki/Your-Page.md`. Hyphens become spaces in the title GitHub shows.
2. Put the takeaways at the top, in a list, before any heading.
3. Add a row to [Home](Home.md). The test that keeps the wiki honest fails if a page is not
   reachable from Home.

## To send something for the newsletter

Open a thread in [Ideas](https://github.com/fde-academy-lab/advanced-rag-lab/discussions/categories/ideas)
with the `newsletter` label: the link, the date, one sentence on why an FDE cares, and one thing
to try here. The editor of the month folds it into the next issue with credit.
