# Resources

One directory per week. Everything an instructor shares in or around a session lives here,
in the repository, so it is versioned, link-checked and searchable. A link in a chat
disappears; a file here does not.

```
resources/
  README.md              this page
  week-01/
    README.md            the session page: agenda, links, what to do before and after
    pre-read.md          what to read before the session, with the question each item answers
    session-notes.md     the shared in-session document; edited live, committed after
    slides.md            a link to the deck, plus the three slides worth re-reading
    recording.md         a link to the recording and the timestamps that matter
    handouts/            anything distributed: CSVs, snippets, diagrams
```

## Who edits what

| Person | Edits | How |
|---|---|---|
| Instructor of record | `week-NN/*` for their week | Direct push to `resources/` on `main` is allowed by CODEOWNERS for `@instructors`; everything else is a PR |
| Teaching assistant | `session-notes.md` during the session, `recording.md` after | Same |
| Learners | Nothing here. Learner work lives in Discussions and in their own fork | |

## Rules

- A link to an external document carries one line saying what is in it and why it is worth
  opening. A bare URL is not a resource.
- Recordings and decks stay where they are hosted; the repository holds the link and the
  index. Large binaries do not go into git.
- The pre-read names the question each reading answers. A list of titles is homework; a list
  of questions is a study guide.
- Anything that names a learner stays out of this directory. Roster data is not content.
