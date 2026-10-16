# Lab 5 — Reflection

## 1. Which issues were the easiest to fix, and which were the hardest?

The easiest were the Flake8 style issues: adding a second blank line between functions, wrapping long lines, deleting the unused `math` import and dropping the `f` from an f-string with no placeholders. Each was mechanical, touched one line and could not change what the program does.

The hardest were the problems no tool reported at all. The program ran without errors, but the output was wrong: an EMI of 375,000 on a 5 lakh loan, a "crypto" loan being approved, a maximum loan that ignored interest, and an "interest saved" figure that counted the prepaid principal as savings. Fixing these needed me to understand the finance (FOIR, present value of an annuity, what interest saved actually means) and to check the new answers independently — for example, confirming that the EMI on the new maximum loan is exactly the 15,000 the customer can afford. Among the tool-reported issues, replacing FTP was the hardest because there is no one-line fix: I had to rewrite the upload over HTTPS and move the credentials into environment variables.

## 2. Did the static analysis tools report any false positives? If so, describe one example.

Bandit's B404 (importing `subprocess`) is close to a false positive: importing the module is not a vulnerability by itself, and the original call used a list of arguments rather than `shell=True`, so shell injection was not possible. It is a reminder to review, not proof of a bug. Here it still pointed to real weaknesses (the `mail` program was found through `PATH`, and failures were ignored), so I replaced it with `smtplib`.

The opposite case mattered more: false negatives. Bandit rated the hard-coded password only "Low" severity, even though a password committed to Git is a serious real-world risk, and none of the three tools caught the five logic bugs. A clean report does not mean correct code.

## 3. How would you integrate static analysis tools into your actual software development workflow?

- **Locally, before each commit:** a `pre-commit` hook that runs Flake8 and Bandit, so style and security problems never reach the repository.
- **In CI (e.g. GitHub Actions):** run Pylint, Flake8 and Bandit on every push and pull request, and fail the build if Bandit finds any Medium/High issue or the Pylint score drops below a threshold such as 9.5.
- **In the editor:** enable Pylint/Flake8 in VS Code so issues are underlined while typing, when they are cheapest to fix.
- **Shared configuration:** keep a `pyproject.toml` / `.flake8` in the repo so the whole team uses the same rules, and document any rule that is deliberately disabled.
- **Alongside tests:** static analysis cannot check that an answer is right, so it should run together with unit tests (this lab's logic bugs would each have been caught by a one-line test with a known expected value).

## 4. What tangible improvements did you observe in code quality, readability, or potential robustness after applying the fixes?

- **Correctness:** the demo now prints correct figures — EMI 10,379.18 instead of 375,000; the over-borrowed customer and the "crypto" loan are rejected; the maximum loan is 722,600.60 instead of 900,000; the interest saved is 12,275.07 instead of 62,275.07; a score of 950 is INVALID.
- **Security:** Bandit went from 8 issues (2 High) to 0. No credentials in source code, no plain-text FTP, no unsafe `marshal` file, unpredictable application IDs.
- **Robustness:** files are always closed via `with`; there is no shared mutable default list or global state; passing a percentage instead of a fraction now raises a clear error instead of returning nonsense; importing the module no longer runs the demo.
- **Readability:** Pylint went from 5.17 to 10.00 and Flake8 to zero warnings. Snake_case names, docstrings on every function and named constants (`MIN_AGE`, `VALID_LOAN_TYPES`, `MAX_CREDIT_SCORE`) make the business rules readable at a glance.
