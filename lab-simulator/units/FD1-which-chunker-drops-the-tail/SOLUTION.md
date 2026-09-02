# FD1 · solution

**A and C drop the tail. B does not.** The grader ran them; here is what it saw.

| | 100 words, stride 48 | 140 words, stride 48 |
|---|---|---|
| **A** `range(0, max(len-size, 1), stride)` | `range(0, 36, 48)` → one window, 0–63. **Drops 36 words** | `range(0, 76, 48)` → windows at 0, 48; last ends at 111. **Drops 28** |
| **B** emit, then `if start + size >= len: return` | windows at 0, 48; last ends at 99 ✓ | windows at 0, 48, 96; last ends at 139 ✓ |
| **C** `len // stride` windows | `100 // 48 = 2` → 0, 48; last ends at 111 ✓ | `140 // 48 = 2` → 0, 48; last ends at 111. **Drops 28** |

**A** asks "is there a whole window left?", which stops one window early whenever `len − size`
is not a multiple of the stride.

**C** is the nastier one. It counts windows with a floor, so it is correct exactly when the
document's remainder after the last full stride is shorter than the window's reach — which is
true of the short example somebody tests with and false of the long document that ships.
Passing at 100 and failing at 140 is the signature of a bound written against one example.

**B** asks the right question — *has the window I just emitted reached the end?* — after
emitting rather than before. That is the shape F1's solution uses.

The transferable skill is the second column: pick a length that does not divide evenly, then
pick another. A bound that is wrong is wrong at some length, and one example is never enough to
find which.
