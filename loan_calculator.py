"""Loan eligibility and EMI calculator.

Calculates EMIs, checks loan eligibility, works out the maximum loan a
customer can afford, builds amortisation schedules, assigns risk bands
from credit scores, estimates interest saved by prepaying and stores
application records in a JSON file.

All interest rates are annual rates given as fractions (0.09 means 9%).
"""
import base64
import http.client
import json
import os
import secrets
import smtplib
from datetime import datetime
from email.message import EmailMessage

MAX_FOIR = 0.5
MIN_AGE = 21
MAX_AGE = 60
MIN_CREDIT_SCORE = 300
MAX_CREDIT_SCORE = 900
VALID_LOAN_TYPES = frozenset({"home", "car", "personal"})
BUREAU_HOST = "api.creditbureau.example"
APPLICATIONS_FILE = "loans.json"


def calculate_emi(principal, annual_rate, years):
    """Return the monthly EMI for a loan.

    annual_rate is a fraction (0.09 for 9%). Passing a percentage such as
    9 raises ValueError instead of silently returning a huge EMI.
    """
    if not 0 <= annual_rate < 1:
        raise ValueError("annual_rate must be a fraction, e.g. 0.09 for 9%")
    months = years * 12
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        return principal / months
    growth = (1 + monthly_rate) ** months
    return principal * monthly_rate * growth / (growth - 1)


def check_eligibility(age, income, credit_score, existing_emi, loan_type):
    """Return True if the applicant passes every eligibility rule.

    Every rule applies to every applicant: a high income or credit score
    no longer skips the affordability (FOIR) or loan-type checks.
    """
    if not MIN_AGE <= age <= MAX_AGE:
        return False
    if income <= 0:
        return False
    if not MIN_CREDIT_SCORE <= credit_score <= MAX_CREDIT_SCORE:
        return False
    if loan_type not in VALID_LOAN_TYPES:
        return False
    return existing_emi / income <= MAX_FOIR


def max_loan_amount(income, existing_emi, annual_rate, years):
    """Return the largest principal whose EMI fits within the FOIR limit.

    This is the present value of the affordable monthly instalment, so it
    accounts for interest instead of just multiplying EMI by months.
    """
    available = income * MAX_FOIR - existing_emi
    if available <= 0:
        return 0.0
    months = years * 12
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        return available * months
    return available * (1 - (1 + monthly_rate) ** -months) / monthly_rate


def amortisation_schedule(principal, annual_rate, years):
    """Return (month, interest, closing_balance) rows for the loan."""
    emi = calculate_emi(principal, annual_rate, years)
    balance = principal
    rows = []
    for month in range(1, years * 12 + 1):
        interest = balance * annual_rate / 12
        balance = max(balance - (emi - interest), 0.0)
        rows.append((month, round(interest, 2), round(balance, 2)))
    return rows


def application_id():
    """Return an unpredictable application ID such as LN-12345678."""
    return "LN-" + str(10000000 + secrets.randbelow(90000000))


def load_applications(path=APPLICATIONS_FILE):
    """Return the stored applications, or an empty dict if none exist."""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_application(name, amount, path=APPLICATIONS_FILE):
    """Add an application to the JSON loan book and return its ID."""
    applications = load_applications(path)
    app_id = application_id()
    applications[app_id] = {"name": name, "amount": amount,
                            "date": datetime.now().isoformat()}
    with open(path, "w", encoding="utf-8") as file:
        json.dump(applications, file, indent=2)
    return app_id


def upload_to_bureau(report_path):
    """Upload a report to the credit bureau over HTTPS.

    Credentials come from the BUREAU_USER and BUREAU_PASSWORD environment
    variables, never from the source code.
    """
    user = os.environ.get("BUREAU_USER", "loanops")
    secret = os.environ.get("BUREAU_PASSWORD")
    if not secret:
        raise RuntimeError("Set BUREAU_PASSWORD in the environment")
    token = base64.b64encode(f"{user}:{secret}".encode()).decode()
    with open(report_path, "rb") as report:
        body = report.read()
    conn = http.client.HTTPSConnection(BUREAU_HOST, timeout=30)
    try:
        conn.request("POST", "/reports/" + os.path.basename(report_path),
                     body=body, headers={"Authorization": "Basic " + token})
        if conn.getresponse().status >= 300:
            raise RuntimeError("Bureau upload failed")
    finally:
        conn.close()


def notify_applicant(recipient, status):
    """Email the applicant their loan status over an encrypted connection."""
    message = EmailMessage()
    message["Subject"] = "Loan " + status
    message["From"] = os.environ.get("LOAN_MAIL_FROM", "loans@bank.example")
    message["To"] = recipient
    message.set_content("Your loan application is " + status)
    with smtplib.SMTP_SSL(os.environ.get("SMTP_HOST", "localhost")) as smtp:
        smtp.send_message(message)


def interest_saved(principal, annual_rate, years, prepayment):
    """Return the interest saved by prepaying part of the principal now.

    The prepayment itself is money the borrower pays, not a saving, so it
    is subtracted from the drop in total repayments.
    """
    months = years * 12
    original = calculate_emi(principal, annual_rate, years) * months
    reduced = calculate_emi(principal - prepayment, annual_rate,
                            years) * months
    return original - reduced - prepayment


def risk_band(credit_score):
    """Return the risk band for a credit score in the 300-900 range."""
    if not MIN_CREDIT_SCORE <= credit_score <= MAX_CREDIT_SCORE:
        return "INVALID"
    if credit_score >= 800:
        return "LOW"
    if credit_score >= 700:
        return "MEDIUM"
    if credit_score >= 600:
        return "HIGH"
    return "VERY HIGH"


def main():
    """Run a short demo of the calculator."""
    print("EMI for 5L @ 9% for 5 years:",
          round(calculate_emi(500000, 0.09, 5), 2))
    print("Eligible (score 760, income 15000, EMIs 12000):",
          check_eligibility(35, 15000, 760, 12000, "personal"))
    print("Eligible (unknown loan type 'crypto'):",
          check_eligibility(30, 80000, 650, 0, "crypto"))
    print("Max loan for income 40000:",
          round(max_loan_amount(40000, 5000, 0.09, 5), 2))
    print("Last schedule row:", amortisation_schedule(100000, 0.12, 1)[-1])
    print("Risk band for 950:", risk_band(950))
    print("Interest saved by prepaying 50000:",
          round(interest_saved(500000, 0.09, 5, 50000), 2))
    print("Saved as:", save_application("Anil", 500000))
    print("Applications on file:", len(load_applications()))
    print("Upload to bureau skipped (no network)")


if __name__ == "__main__":
    main()
