# Lab 5 — Issues Found in `loan_calculator.py`

Line numbers refer to the **original** file. Ordered by severity: security (High/Medium) first, then logic bugs found by reading the program's output, then Pylint/Flake8 quality and style issues.

## Security issues (Bandit)

| # | Issue | Type | Line(s) | Description | Fix Approach |
|---|-------|------|---------|-------------|--------------|
| 1 | Insecure FTP (B402, B321) | Security — **High** | 3, 68 | `ftplib` sends the username, password and the credit report in plain text, so anyone on the network can read them. | Removed `ftplib`; the upload now uses `http.client.HTTPSConnection` (TLS-encrypted). |
| 2 | Unsafe deserialisation with `marshal` (B302) | Security — **Medium** | 4, 57, 64 | `marshal.loads` on a file is unsafe: a tampered `loans.bin` can crash the interpreter or feed it malicious data, and the format is not stable across Python versions. | Switched to `json.dump` / `json.load` and renamed the file to `loans.json`. |
| 3 | Hard-coded password (B107) | Security — Low (real-world impact high) | 67 | `password="Bureau#2024"` is visible to anyone who can read the source or the Git history. | Credentials now come from the `BUREAU_USER` / `BUREAU_PASSWORD` environment variables; the function refuses to run if the password is missing. |
| 4 | Predictable application IDs (B311) | Security — Low | 51 | `random.randint` is a predictable generator, so IDs could be guessed. | Used `secrets.randbelow`, which is cryptographically secure. |
| 5 | Shelling out to `mail` (B404, B603, B607) | Security — Low | 6, 74 | Runs an external `mail` program found through `PATH` (could be hijacked), passes user input to a subprocess and ignores failures. | Removed `subprocess`; the email is sent with `smtplib.SMTP_SSL` and `EmailMessage`. |

## Logic bugs (found by reading the output — no tool flagged these)

| # | Issue | Type | Line(s) | Description | Fix Approach |
|---|-------|------|---------|-------------|--------------|
| 6 | Rate passed as a percentage | Bug — **High** | 94, 15 | `calculateEMI(500000, 9, 5)` treats 9 as 900% a year, printing an EMI of 375000. Every other caller passes fractions (0.09). | The call now passes `0.09`; `calculate_emi` raises `ValueError` for rates ≥ 1 so the mistake cannot happen silently again. Correct EMI: 10,379.18. |
| 7 | Eligibility shortcut skips safety checks | Bug — **High** | 24–25 | `if credit_score > 750 or income > 25000: return True` runs before the FOIR and loan-type checks, so a customer whose EMIs already take 80% of income, and a `"crypto"` loan, were both approved. | Every applicant now goes through every check (age, income, credit-score range, loan type, FOIR). Both demo cases now print `False`. |
| 8 | Maximum loan ignores interest | Bug — **High** | 33–38 | It just multiplied the affordable EMI by the number of months (15000 × 60 = 900000), as if the loan were interest-free. `annual_rate` was never used. | Replaced the loop with the present-value-of-annuity formula. Result: 722,600.60 — and the EMI on that amount is exactly the 15,000 the customer can afford. |
| 9 | Interest saved includes the prepayment | Bug — Medium | 76–79 | The difference in total repayments includes the 50,000 prepaid principal itself, so the "saving" was overstated (62,275 instead of 12,275). | Subtract the prepayment: `original - reduced - prepayment`. |
| 10 | Credit score 950 rated "LOW" risk | Bug — Medium | 81–91 | Credit scores run from 300 to 900; 950 is invalid but was rated LOW risk. | Out-of-range scores (< 300 or > 900) now return `"INVALID"`; the same range is enforced in eligibility. |

## Code quality issues (Pylint)

| # | Issue | Type | Line(s) | Description | Fix Approach |
|---|-------|------|---------|-------------|--------------|
| 11 | Mutable default argument (W0102) | Bug — Medium | 20 | `history=[]` is created once and shared across every call, so it grows forever. It was never read. | Removed the unused parameter (this also fixes R0913/R0917 "too many arguments"). |
| 12 | Files opened without `with` (R1732) | Quality — Medium | 56, 63, 70 | If an exception occurs the file is never closed; line 70 never closed the report at all. | Every `open()` now uses a `with` block. |
| 13 | `global` statement (W0603) | Quality | 62 | `loadApplications` silently replaced a module-level dict. | `load_applications` returns the dict; `save_application` loads, adds and writes. No global state. |
| 14 | Built-in shadowed / unused names (W0622, W0612, W0613) | Quality | 34, 36, 33 | `sum` hid the built-in, `month` and `annual_rate` were unused. | Disappeared with the rewrite of `max_loan_amount` (fix #8). |
| 15 | Non-snake_case names (C0103) | Convention | 14–81 | `calculateEMI`, `checkEligibility`, etc. break PEP 8 naming. | Renamed to `calculate_emi`, `check_eligibility`, etc. |
| 16 | Missing docstrings (C0114, C0116) | Convention | 1 and every function | No module or function documentation. | Added a module docstring and one per function. |
| 17 | Redundant if/else, `or` chain (R1703, R1705, R1714, C0325) | Refactor | 28–31, 79, 82 | Verbose returns. | Used `in VALID_LOAN_TYPES`, early returns, removed extra parentheses. |
| 18 | `main()` runs on import | Quality | 106 | Importing the module ran the demo and wrote a file. | Wrapped in `if __name__ == "__main__":`. |

## Style issues (Flake8)

| # | Issue | Type | Line(s) | Description | Fix Approach |
|---|-------|------|---------|-------------|--------------|
| 19 | Unused import `math` (F401) | Style | 2 | Imported but never used. | Removed. |
| 20 | f-string without placeholders (F541, W1309) | Style | 104 | `f"Upload ..."` has nothing to format. | Plain string. |
| 21 | Expected 2 blank lines (E302, E305) | Style | 14–106 | Only one blank line between top-level functions. | Two blank lines everywhere. |
| 22 | Line too long (E501, C0301) | Style | 20, 55, 70, 78, 95, 96, 100 | Lines over 79 characters. | Wrapped inside parentheses. |

## Results

| Tool | Before | After |
|------|--------|-------|
| Pylint | 5.17 / 10 | **10.00 / 10** |
| Bandit | 8 issues (2 High, 1 Medium, 5 Low) | **0** |
| Flake8 | 22 warnings | **0** |
