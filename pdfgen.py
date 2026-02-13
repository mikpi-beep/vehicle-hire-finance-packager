from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def _money(m: Dict[str, Any]) -> str:
    if not isinstance(m, dict):
        return ""
    amt = m.get("amount")
    cur = m.get("currency", "GBP")
    if amt is None or amt == "":
        return ""
    try:
        amt_f = float(amt)
        return f"{cur} {amt_f:,.0f}"
    except Exception:
        return f"{cur} {amt}"


def _safe(d: Any) -> str:
    return "" if d is None else str(d)


def generate_credit_summary_pdf(app: Dict[str, Any], rules: Dict[str, Any], out_path: str) -> str:
    """
    Generates a clean 1–2 page lender-style credit summary PDF.
    """
    c = canvas.Canvas(out_path, pagesize=A4)
    width, height = A4  # noqa: F841

    margin_x = 18 * mm
    y = height - 18 * mm

    def h1(text):
        nonlocal y
        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin_x, y, text)
        y -= 8 * mm

    def h2(text):
        nonlocal y
        c.setFont("Helvetica-Bold", 11.5)
        c.drawString(margin_x, y, text)
        y -= 6 * mm

    def p(label, value):
        nonlocal y
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(margin_x, y, f"{label}:")
        c.setFont("Helvetica", 9.5)
        c.drawString(margin_x + 45 * mm, y, str(value)[:110])
        y -= 5 * mm

    def bullets(title, items: List[str]):
        nonlocal y
        h2(title)
        c.setFont("Helvetica", 9.5)
        for it in items[:12]:
            if y < 25 * mm:
                c.showPage()
                y = height - 18 * mm
                c.setFont("Helvetica", 9.5)
            c.drawString(margin_x + 3 * mm, y, f"• {_safe(it)}"[:120])
            y -= 5 * mm
        y -= 2 * mm

    broker = app.get("broker", {})
    applicant = app.get("applicant", {})
    facility = app.get("facility", {})
    fleet = app.get("fleetOps", {})
    financials = app.get("financials", {})
    accounts = financials.get("accounts", {}) if isinstance(financials, dict) else {}
    mgmt = financials.get("managementAccounts", {}) if isinstance(financials, dict) else {}
    existing = financials.get("existingDebt", {}) if isinstance(financials, dict) else {}
    assets = app.get("assets", {})
    batches = assets.get("batches", []) if isinstance(assets, dict) else []

    h1("Credit Summary – Vehicle Hire Asset Finance (UK)")
    c.setFont("Helvetica", 9.5)
    c.drawString(margin_x, y, f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}")
    y -= 7 * mm

    h2("Applicant")
    p("Legal name", _safe(applicant.get("legalName")))
    p("Trading name", _safe(applicant.get("tradingName", "")))
    p("Legal structure", _safe(applicant.get("legalStructure")))
    p("Company number", _safe(applicant.get("companyNumber", "")))
    p("VAT", "Yes" if applicant.get("vatRegistered") else "No")

