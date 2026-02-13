from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
from dateutil.relativedelta import relativedelta


def _months_old(d: Optional[date]) -> Optional[int]:
    if not d:
        return None
    today = date.today()
    if d > today:
        return 0
    rd = relativedelta(today, d)
    return rd.years * 12 + rd.months


@dataclass
class RuleResult:
    missing: List[str]
    required_now: List[str]
    flags: List[str]
    suggestions: List[str]


def evaluate_rules(app: Dict[str, Any]) -> RuleResult:
    """
    Simple v1 rules engine for UK vehicle hire asset finance packaging.
    It does NOT make a credit decision; it checks pack readiness and flags.
    """
    missing: List[str] = []
    required_now: List[str] = []
    flags: List[str] = []
    suggestions: List[str] = []

    def get(path: str, default=None):
        cur = app
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
        return cur

    baseline_required = [
        "broker.brokerFirmName",
        "broker.brokerContactName",
        "broker.brokerContactEmail",
        "broker.internalDealRef",
        "applicant.legalName",
        "applicant.legalStructure",
        "applicant.vatRegistered",
        "applicant.yearsTrading",
        "applicant.registeredAddress.postcode",
        "applicant.primaryContact.name",
        "applicant.primaryContact.email",
        "applicant.primaryContact.phone",
        "controllers.directors",
        "facility.productType",
        "facility.financePurpose",
        "facility.termMonths",
        "facility.totalAmountRequested.amount",
        "facility.totalAmountRequested.currency",
        "facility.vatTreatment",
        "assets.batches",
        "assets.suppliers",
        "fleetOps.fleetSizeTotal",
        "fleetOps.avgUtilisationPercent",
        "fleetOps.avgRevenuePerVehiclePerMonth.amount",
        "consents.hasAuthorityToShareData",
        "consents.dataProcessingConsent",
        "risk.hasCCJsOrInsolvency",
    ]

    legal_structure = get("applicant.legalStructure")
    if legal_structure in ("limited_company", "llp"):
        baseline_required.append("applicant.companyNumber")
        baseline_required.append("applicant.incorporationDate")
    if get("applicant.vatRegistered") is True:
        baseline_required.append("applicant.vatNumber")

    directors = get("controllers.directors", [])
    if not isinstance(directors, list) or len(directors) == 0:
        missing.append("controllers.directors (at least 1 director required)")
    else:
        for i, d in enumerate(directors):
            for f in ("fullName", "dob", "homePostcode", "isPrimaryGuarantor"):
                if not d.get(f):
                    missing.append(f"controllers.directors[{i}].{f}")

    batches = get("assets.batches", [])
    if not isinstance(batches, list) or len(batches) == 0:
        missing.append("assets.batches (at least 1 batch required)")
    else:
        for i, b in enumerate(batches):
            for f in ("batchRef", "vehicleType", "newOrUsed", "quantity", "avgUnitPrice", "supplierName"):
                if f == "avgUnitPrice":
                    if not (isinstance(b.get("avgUnitPrice"), dict) and b["avgUnitPrice"].get("amount") is not None):
                        missing.append(f"assets.batches[{i}].avgUnitPrice.amount")
                else:
                    if not b.get(f) and b.get(f) != 0:
                        missing.append(f"assets.batches[{i}].{f}")
            if b.get("newOrUsed") == "used":
                if b.get("avgVehicleAgeMonths") in (None, ""):
                    required_now.append(f"assets.batches[{i}].avgVehicleAgeMonths (required for used vehicles)")

    suppliers = get("assets.suppliers", [])
    if not isinstance(suppliers, list) or len(suppliers) == 0:
        missing.append("assets.suppliers (at least 1 supplier required)")
    else:
        for i, s in enumerate(suppliers):
            if not s.get("supplierName"):
                missing.append(f"assets.suppliers[{i}].supplierName")
            if not s.get("supplierType"):
                required_now.append(f"assets.suppliers[{i}].supplierType")

    for p in baseline_required:
        v = get(p, None)
        if v is None or v == "":
            missing.append(p)

    years_trading = get("applicant.yearsTrading", 0) or 0
    try:
        years_trading_num = float(years_trading)
    except Exception:
        years_trading_num = 0.0

    if years_trading_num < 2:
        flags.append("Young business (<2 years trading): lenders often ask for more recent evidence and stronger guarantees.")
        required_now.append("financials.bankingEvidence.statementsMonthsProvided (suggest 6)")
        suggestions.append("Add 6 months bank statements (or at least 3) and a short operator experience narrative.")

    last_fye = get("financials.accounts.lastFiledYearEnd")
    last_fye_date = None
    if isinstance(last_fye, str) and last_fye:
        try:
            last_fye_date = datetime.strptime(last_fye, "%Y-%m-%d").date()
        except Exception:
            last_fye_date = None

    m_old = _months_old(last_fye_date) if last_fye_date else None
    if m_old is None:
        required_now.append("financials.accounts.lastFiledYearEnd (or management accounts periodEnd)")
        suggestions.append("If statutory accounts are not available/too old, provide recent management accounts.")
    elif m_old > 12:
        flags.append(f"Accounts are {m_old} months old: management accounts likely required.")
        required_now.append("financials.managementAccounts.periodEnd")
        suggestions.append("Provide management accounts (YTD + last month) to bring performance up to date.")

    for b in batches if isinstance(batches, list) else []:
        if b.get("newOrUsed") == "used":
            try:
                age_i = int(b.get("avgVehicleAgeMonths"))
            except Exception:
                age_i = None
            if age_i is not None and age_i > 36:
                flags.append(f"Batch {b.get('batchRef','(unknown)')}: used vehicles average age > 36 months.")
                suggestions.append("Consider higher deposit / shorter term / clearer remarketing plan for older used stock.")

    top1 = get("fleetOps.customerConcentrationPercentTop1")
    top5 = get("fleetOps.customerConcentrationPercentTop5")
    try:
        top1v = float(top1) if top1 not in (None, "") else None
    except Exception:
        top1v = None
    try:
        top5v = float(top5) if top5 not in (None, "") else None
    except Exception:
        top5v = None

    if (top1v is not None and top1v >= 35) or (top5v is not None and top5v >= 70):
        flags.append("Customer concentration appears high (Top1>=35% or Top5>=70%).")
        required_now.append("fleetOps.contractCoverageNarrative")
        suggestions.append("Add narrative: contract terms, break clauses, diversification plan, and utilisation resilience.")

    pg_expected = get("controllers.guarantees.personalGuaranteeExpected")
    if pg_expected == "yes":
        guarantors = get("controllers.guarantees.guarantors", [])
        if not guarantors:
            required_now.append("controllers.guarantees.guarantors")

    def uniq(seq):
        seen = set()
        out = []
        for x in seq:
            if x not in seen:
                out.append(x)
                seen.add(x)
        return out

    return RuleResult(
        missing=uniq(missing),
        required_now=uniq(required_now),
        flags=uniq(flags),
        suggestions=uniq(suggestions),
    )


def readiness_score(rr: RuleResult) -> Tuple[str, str]:
    if rr.missing:
        return "RED", f"Missing {len(rr.missing)} required fields."
    if rr.required_now or rr.flags:
        return "AMBER", f"{len(rr.required_now)} conditional items and {len(rr.flags)} flags to address."
    return "GREEN", "Pack looks complete for initial lender review."
