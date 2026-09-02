# How to open the repository in a Codespace

**Takeaway:** the Codespace comes prebuilt. Python, the package, the notebooks and the
simulator are installed before you arrive; the welcome banner tells you the three commands.

1. On the [repository page](https://github.com/fde-academy-lab/advanced-rag-lab), click **Code**,
   then **Codespaces**, then **Create codespace on main**.
2. Wait for the editor. The terminal prints a welcome with the three commands.
3. `python -m labsim status` from `lab-simulator/` lists the pathway; `make eval` prints the
   scorecard in about ten seconds; `make lab` opens JupyterLab on the notebooks.
4. Your attempts live under `lab-simulator/attempts/`; commit them to a branch if you want to
   keep them, or post them in a thread to be graded.

**Done when:** `make eval` prints evidence recall 0.7645.

Two things on purpose: the worked answers are hidden from the explorer and from search (open
them from the terminal if you mean to), and stopping the Codespace when you are done keeps your
free hours.
