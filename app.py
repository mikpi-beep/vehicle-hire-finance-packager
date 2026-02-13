from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import streamlit as st

from core import evaluate_rules, readiness_score
from pdfgen import generate_credit_summary_pdf

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="UK Vehicle Hire Finance Packager (MVP)", layout="wide")
st.title("UK Vehicle Hire Finance Packager (MVP)")
st.caption("Broker-style intake + pack readiness checks + lender-friendly PDF credit summary. No lender integrations.")


def money_input(label, key_prefix, default_amt=None):
    col1, col2 = st.columns([2, 1])
    with col1:
        amt = st.number_input(
            label,
            min_value=0.0,
            value=float(default_amt or 0.0),
            step=100.0,
            key=f"{key_prefix}_amt",
        )
    with col2:
        cur = st.selectbox("Currency", ["GBP"], index=0, key=f"{key_prefix}_cur")
    return {"amount": float(amt), "currency": cur}


with st.sidebar:
    st.header("Application file")
    app_id = st.text_input("Deal reference (file name)", value="deal_001")
    load_btn = st.button("Load")
    save_btn = st.button("Save")
    st.divider()
    export_pdf_btn = st.button("Generate PDF Credit Summary")

app_path = DATA_DIR / f"{app_id}.json"


def default_app():
    return {
        "broker": {
            "brokerFirmName": "",
            "brokerContactName": "",
            "brokerContactEmail": "",
            "brokerContactPhone": "",
            "internalDealRef": app_id,
            "targetLenderProfiles": [],
            "notesInternal": "",
        },
        "applicant": {
            "legalName": "",
            "tradingName": "",
            "legalStructure": "limited_company",
            "companyNumber": "",
            "utr": "",
            "vatRegistered": True,
            "vatNumber": "",
            "incorporationDate": str(date.today()),
            "yearsTrading": 3,
            "sicCodes": [],
            "registeredAddress": {
                "line1": "",
                "line2": "",
                "townCity": "",
                "county": "",
                "postcode": "",
                "country": "UK",
            },
            "tradingAddresses": [],
            "primaryContact": {"name": "", "roleTitle": "", "email": "", "phone": ""},
            "banking": {"primaryBankName": ""},
            "industry": {"isVehicleHire": True, "subSector": "mixed"},
        },
        "controllers": {
            "directors": [
                {
                    "fullName": "",
                    "dob": "1980-01-01",
                    "homePostcode": "",
                    "homeAddress": None,
                    "role": "director",
                    "ownershipPercent": 0,
                    "isPrimaryGuarantor": True,
                }
            ],
            "shareholdersOrPSCs": [],
            "groupStructure": {"isGroup": False, "parentCompanyName": ""},
            "guarantees": {
                "personalGuaranteeExpected": "unknown",
                "pgType": "limited",
                "guarantors": [],
            },
        },
        "facility": {
            "financePurpose": "growth",
            "productType": "hire_purchase",
            "repaymentProfile": "monthly",
            "termMonths": 48,
            "deposit": {"amount": 0, "currency": "GBP"},
            "balloonOrResidual": {"amount": 0, "currency": "GBP"},
            "totalAmountRequested": {"amount": 0, "currency": "GBP"},
            "vatTreatment": "vat_on_purchase_reclaimable",
            "speedRequirement": "standard",
            "preferredPaymentDay": 1,
        },
        "assets": {
            "batches": [
                {
                    "batchRef": "BATCH-1",
                    "vehicleType": "van",
                    "newOrUsed": "new",
                    "quantity": 1,
                    "avgUnitPrice": {"amount": 0, "currency": "GBP"},
                    "totalPrice": {"amount": 0, "currency": "GBP"},
                    "avgVehicleAgeMonths": None,
                    "mileageRange": None,
                    "makeModelKnown": False,
                    "make": "",
                    "model": "",
                    "fuelType": "diesel",
                    "supplierName": "",
                    "quoteReference": "",
                    "expectedDeliveryDate": "",
                    "securityNotes": "",
                }
            ],
            "suppliers": [
                {
                    "supplierName": "",
                    "supplierType": "independent_dealer",
                    "contactName": "",
                    "contactEmail": "",
                    "contactPhone": "",
                    "address": None,
                }
            ],
        },
        "financials": {
            "accounts": {
                "lastFiledYearEnd": "",
                "turnover": {"amount": 0, "currency": "GBP"},
                "ebitda": {"amount": 0, "currency": "GBP"},
                "netProfit": {"amount": 0, "currency": "GBP"},
                "netAssets": {"amount": 0, "currency": "GBP"},
                "totalBorrowings": {"amount": 0, "currency": "GBP"},
            },
            "managementAccounts": {
                "periodEnd": "",
                "ytdTurnover": {"amount": 0, "currency": "GBP"},
                "ytdEbitda": {"amount": 0, "currency": "GBP"},
                "lastMonthTurnover": {"amount": 0, "currency": "GBP"},
                "lastMonthEbitda": {"amount": 0, "currency": "GBP"},
            },
            "bankingEvidence": {
                "statementsMonthsProvided": 0,
                "avgMonthlyCredits": {"amount": 0, "currency": "GBP"},
                "avgMonthlyDebits": {"amount": 0, "currency": "GBP"},
                "minMonthEndBalance": {"amount": 0, "currency": "GBP"},
            },
            "existingDebt": {
                "monthlyFinanceCommitments": {"amount": 0, "currency": "GBP"},
                "fleetFinanceCommitments": {"amount": 0, "currency": "GBP"},
                "otherDebtCommitments": {"amount": 0, "currency": "GBP"},
            },
        },
        "fleetOps": {
            "fleetSizeTotal": 0,
            "fleetOwned": 0,
            "fleetLeasedOrFinanced": 0,
            "avgUtilisationPercent": 0,
            "avgRevenuePerVehiclePerMonth": {"amount": 0, "currency": "GBP"},
            "avgMaintenanceCostPerVehiclePerMonth": {"amount": 0, "currency": "GBP"},
            "customerConcentrationPercentTop1": "",
            "customerConcentrationPercentTop5": "",
            "contractCoverageNarrative": "",
        },
        "risk": {
            "hasCCJsOrInsolvency": "unknown",
            "anyLateTaxOrVAT": "unknown",
            "adverseTradingEvents": [],
            "brokerNarrative": "",
        },
        "consents": {"hasAuthorityToShareData": False, "dataProcessingConsent": False},
    }


if load_btn:
    if app_path.exists():
        st.session_state["appdata"] = json.loads(app_path.read_text())
        st.success(f"Loaded {app_path}")
    else:
        st.session_state["appdata"] = default_app()
        st.info("No saved file found; started a new application.")

if "appdata" not in st.session_state:
    st.session_state["appdata"] = default_app()

app = st.session_state["appdata"]

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "1) Broker & Applicant",
        "2) Controllers",
        "3) Facility",
        "4) Assets (Fleet batches)",
        "5) Fleet Ops & Financials",
        "6) Readiness & Export",
    ]
)

with tab1:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Broker")
        app["broker"]["brokerFirmName"] = st.text_input(
            "Broker firm name", value=app["broker"]["brokerFirmName"]
        )
        app["broker"]["brokerContactName"] = st.text_input(
            "Broker contact name", value=app["broker"]["brokerContactName"]
        )
        app["broker"]["brokerContactEmail"] = st.text_input(
            "Broker contact email", value=app["broker"]["brokerContactEmail"]
        )
        app["broker"]["brokerContactPhone"] = st.text_input(
            "Broker contact phone", value=app["broker"]["brokerContactPhone"]
        )
        app["broker"]["internalDealRef"] = app_id
        app["broker"]["notesInternal"] = st.text_area(
            "Internal notes", value=app["broker"]["notesInternal"], height=80
        )

    with c2:
        st.subheader("Applicant (UK)")
        app["applicant"]["legalName"] = st.text_input(
            "Legal name", value=app["applicant"]["legalName"]
        )
        app["applicant"]["tradingName"] = st.text_input(
            "Trading name (optional)", value=app["applicant"].get("tradingName", "")
        )
        app["applicant"]["legalStructure"] = st.selectbox(
            "Legal structure",
            ["limited_company", "llp", "sole_trader", "partnership"],
            index=["limited_company", "llp", "sole_trader", "partnership"].index(
                app["applicant"]["legalStructure"]
            ),
        )

        if app["applicant"]["legalStructure"] in ("limited_company", "llp"):
            app["applicant"]["companyNumber"] = st.text_input(
                "Company number", value=app["applicant"]["companyNumber"]
            )
            app["applicant"]["incorporationDate"] = str(
                st.date_input(
                    "Incorporation date",
                    value=date.fromisoformat(app["applicant"]["incorporationDate"]),
                )
            )
        else:
            app["applicant"]["utr"] = st.text_input(
                "UTR (optional for v1)", value=app["applicant"].get("utr", "")
            )

        app["applicant"]["vatRegistered"] = st.checkbox(
            "VAT registered", value=bool(app["applicant"]["vatRegistered"])
        )
        if app["applicant"]["vatRegistered"]:
            app["applicant"]["vatNumber"] = st.text_input(
                "VAT number", value=app["applicant"].get("vatNumber", "")
            )

        app["applicant"]["yearsTrading"] = st.number_input(
            "Years trading",
            min_value=0.0,
            value=float(app["applicant"]["yearsTrading"]),
            step=0.5,
        )

        st.markdown("**Registered address**")
        ra = app["applicant"]["registeredAddress"]
        ra["line1"] = st.text_input("Reg addr line 1", value=ra.get("line1", ""))
        ra["line2"] = st.text_input("Reg addr line 2", value=ra.get("line2", ""))
        ra["townCity"] = st.text_input("Reg addr town/city", value=ra.get("townCity", ""))
        ra["county"] = st.text_input("Reg addr county", value=ra.get("county", ""))
        ra["postcode"] = st.text_input("Reg addr postcode", value=ra.get("postcode", ""))

        st.markdown("**Primary contact**")
        pc = app["applicant"]["primaryContact"]
        pc["name"] = st.text_input("Contact name", value=pc.get("name", ""))
        pc["roleTitle"] = st.text_input("Role title", value=pc.get("roleTitle", ""))
        pc["email"] = st.text_input("Contact email", value=pc.get("email", ""))
        pc["phone"] = st.text_input("Contact phone", value=pc.get("phone", ""))

        app["applicant"]["industry"]["subSector"] = st.selectbox(
            "Vehicle hire sub-sector",
            ["daily_rental", "flexi_rent", "contract_hire_operator", "specialist_rental", "mixed"],
            index=["daily_rental", "flexi_rent", "contract_hire_operator", "specialist_rental", "mixed"].index(
                app["applicant"]["industry"]["subSector"]
            ),
        )

with tab2:
    st.subheader("Directors")
    directors = app["controllers"]["directors"]
    for i, d in enumerate(directors):
        with st.expander(f"Director {i+1}: {d.get('fullName') or '(name)'}", expanded=(i == 0)):
            d["fullName"] = st.text_input("Full name", value=d.get("fullName", ""), key=f"dir_name_{i}")
            d["dob"] = str(
                st.date_input(
                    "Date of birth",
                    value=date.fromisoformat(d.get("dob", "1980-01-01")),
                    key=f"dir_dob_{i}",
                )
            )
            d["homePostcode"] = st.text_input("Home postcode", value=d.get("homePostcode", ""), key=f"dir_pc_{i}")
            d["ownershipPercent"] = st.number_input(
                "Ownership % (optional)", min_value=0.0, max_value=100.0, value=float(d.get("ownershipPercent") or 0.0),
                step=1.0, key=f"dir_own_{i}"
            )
            d["isPrimaryGuarantor"] = st.checkbox("Primary guarantor", value=bool(d.get("isPrimaryGuarantor", False)), key=f"dir_pg_{i}")

    colA, colB = st.columns(2)
    with colA:
        if st.button("Add director"):
            directors.append(
                {
                    "fullName": "",
                    "dob": "1980-01-01",
                    "homePostcode": "",
                    "homeAddress": None,
                    "role": "director",
                    "ownershipPercent": 0,
                    "isPrimaryGuarantor": False,
                }
            )
    with colB:
        if st.button("Remove last director") and len(directors) > 1:
            directors.pop()

    st.subheader("Guarantees")
    g = app["controllers"]["guarantees"]
    g["personalGuaranteeExpected"] = st.selectbox(
        "Personal guarantee expected?", ["yes", "no", "unknown"],
        index=["yes", "no", "unknown"].index(g.get("personalGuaranteeExpected", "unknown"))
    )
    g["pgType"] = st.selectbox(
        "PG type", ["limited", "unlimited", "none"],
        index=["limited", "unlimited", "none"].index(g.get("pgType", "limited"))
    )
    if g["personalGuaranteeExpected"] == "yes":
        names = [d.get("fullName") for d in directors if d.get("fullName")]
        g["guarantors"] = st.multiselect("Guarantors", options=names, default=g.get("guarantors", []))

with tab3:
    st.subheader("Facility request")
    f = app["facility"]
    f["financePurpose"] = st.selectbox(
        "Purpose", ["growth", "replacement", "contract_win", "refinance", "mixed"],
        index=["growth", "replacement", "contract_win", "refinance", "mixed"].index(f["financePurpose"])
    )
    f["productType"] = st.selectbox(
        "Product type", ["hire_purchase", "finance_lease", "operating_lease", "other"],
        index=["hire_purchase", "finance_lease", "operating_lease", "other"].index(f["productType"])
    )
    f["termMonths"] = st.slider("Term (months)", min_value=6, max_value=84, value=int(f["termMonths"]), step=6)
    f["vatTreatment"] = st.selectbox(
        "VAT treatment", ["vat_on_purchase_reclaimable", "vat_on_purchase_not_reclaimable", "vat_on_rentals", "unknown"],
        index=["vat_on_purchase_reclaimable", "vat_on_purchase_not_reclaimable", "vat_on_rentals", "unknown"].index(f["vatTreatment"])
    )
    f["totalAmountRequested"] = money_input("Total amount requested", "amt_req", default_amt=f["totalAmountRequested"]["amount"])
    f["deposit"] = money_input("Deposit (if any)", "deposit", default_amt=f.get("deposit", {}).get("amount", 0))
    f["balloonOrResidual"] = money_input("Balloon / Residual (if any)", "balloon", default_amt=f.get("balloonOrResidual", {}).get("amount", 0))

with tab4:
    st.subheader("Suppliers")
    suppliers = app["assets"]["suppliers"]
    for i, s in enumerate(suppliers):
        with st.expander(f"Supplier {i+1}: {s.get('supplierName') or '(name)'}", expanded=(i == 0)):
            s["supplierName"] = st.text_input("Supplier name", value=s.get("supplierName", ""), key=f"sup_name_{i}")
            s["supplierType"] = st.selectbox(
                "Supplier type",
                ["franchise_dealer", "independent_dealer", "manufacturer", "auction", "broker", "other"],
                index=["franchise_dealer", "independent_dealer", "manufacturer", "auction", "broker", "other"].index(s.get("supplierType", "independent_dealer")),
                key=f"sup_type_{i}",
            )
            s["contactEmail"] = st.text_input("Contact email", value=s.get("contactEmail", ""), key=f"sup_email_{i}")

    colA, colB = st.columns(2)
    with colA:
        if st.button("Add supplier"):
            suppliers.append(
                {"supplierName": "", "supplierType": "independent_dealer", "contactName": "", "contactEmail": "", "contactPhone": "", "address": None}
            )
    with colB:
        if st.button("Remove last supplier") and len(suppliers) > 1:
            suppliers.pop()

    st.subheader("Vehicle batches")
    batches = app["assets"]["batches"]
    supplier_names = [s.get("supplierName") for s in suppliers if s.get("supplierName")] or [""]

    for i, b in enumerate(batches):
        with st.expander(f"Batch {i+1}: {b.get('batchRef')}", expanded=(i == 0)):
            b["batchRef"] = st.text_input("Batch reference", value=b.get("batchRef", ""), key=f"b_ref_{i}")
            b["vehicleType"] = st.selectbox(
                "Vehicle type", ["car", "van", "lcv", "hgv", "minibus", "specialist"],
                index=["car", "van", "lcv", "hgv", "minibus", "specialist"].index(b.get("vehicleType", "van")),
                key=f"b_vt_{i}",
            )
            b["newOrUsed"] = st.selectbox(
                "New or used", ["new", "used"],
                index=["new", "used"].index(b.get("newOrUsed", "new")),
                key=f"b_nu_{i}",
            )
            b["quantity"] = st.number_input(
                "Quantity", min_value=1, value=int(b.get("quantity") or 1), step=1, key=f"b_qty_{i}"
            )
            b["avgUnitPrice"] = money_input(
                "Average unit price", f"b_price_{i}", default_amt=b.get("avgUnitPrice", {}).get("amount", 0)
            )

            b["totalPrice"] = {"amount": float(b["avgUnitPrice"]["amount"]) * int(b["quantity"]), "currency": "GBP"}
            st.caption(f"Total price (auto): GBP {b['totalPrice']['amount']:,.0f}")

            if b["newOrUsed"] == "used":
                b["avgVehicleAgeMonths"] = st.number_input(
                    "Average vehicle age (months)", min_value=0, value=int(b.get("avgVehicleAgeMonths") or 0), step=1, key=f"b_age_{i}"
                )
            else:
                b["avgVehicleAgeMonths"] = None

            b["supplierName"] = st.selectbox(
                "Supplier for this batch", supplier_names,
                index=(supplier_names.index(b.get("supplierName", "")) if b.get("supplierName", "") in supplier_names else 0),
                key=f"b_sup_{i}",
            )
            b["quoteReference"] = st.text_input("Quote / pro-forma reference (optional)", value=b.get("quoteReference", ""), key=f"b_q_{i}")

    colA, colB = st.columns(2)
    with colA:
        if st.button("Add batch"):
            batches.append(
                {
                    "batchRef": f"BATCH-{len(batches)+1}",
                    "vehicleType": "van",
                    "newOrUsed": "new",
                    "quantity": 1,
                    "avgUnitPrice": {"amount": 0, "currency": "GBP"},
                    "totalPrice": {"amount": 0, "currency": "GBP"},
                    "avgVehicleAgeMonths": None,
                    "mileageRange": None,
                    "makeModelKnown": False,
                    "make": "",
                    "model": "",
                    "fuelType": "diesel",
                    "supplierName": supplier_names[0] if supplier_names else "",
                    "quoteReference": "",
                    "expectedDeliveryDate": "",
                    "securityNotes": "",
                }
            )
    with colB:
        if st.button("Remove last batch") and len(batches) > 1:
            batches.pop()

with tab5:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Fleet operations (vehicle hire)")
        fo = app["fleetOps"]
        fo["fleetSizeTotal"] = st.number_input("Fleet size total", min_value=0, value=int(fo.get("fleetSizeTotal") or 0), step=1)
        fo["avgUtilisationPercent"] = st.slider("Average utilisation %", min_value=0, max_value=100, value=int(fo.get("avgUtilisationPercent") or 0), step=1)
        fo["avgRevenuePerVehiclePerMonth"] = money_input("Average revenue per vehicle per month", "rev_pv", default_amt=fo.get("avgRevenuePerVehiclePerMonth", {}).get("amount", 0))
        fo["customerConcentrationPercentTop1"] = st.text_input("Top 1 customer % (optional)", value=str(fo.get("customerConcentrationPercentTop1", "")))
        fo["customerConcentrationPercentTop5"] = st.text_input("Top 5 customers % (optional)", value=str(fo.get("customerConcentrationPercentTop5", "")))
        fo["contractCoverageNarrative"] = st.text_area("Contract coverage narrative (if needed)", value=fo.get("contractCoverageNarrative", ""), height=120)

    with c2:
        st.subheader("Financials (structured summary)")
        fin = app["financials"]
        acc = fin["accounts"]
        acc["lastFiledYearEnd"] = st.text_input("Last filed year-end (YYYY-MM-DD, optional)", value=acc.get("lastFiledYearEnd", ""))
        acc["turnover"] = money_input("Turnover (last FY)", "turnover", default_amt=acc.get("turnover", {}).get("amount", 0))
        acc["ebitda"] = money_input("EBITDA (last FY)", "ebitda", default_amt=acc.get("ebitda", {}).get("amount", 0))
        acc["netProfit"] = money_input("Net profit (last FY)", "np", default_amt=acc.get("netProfit", {}).get("amount", 0))
        acc["netAssets"] = money_input("Net assets", "na", default_amt=acc.get("netAssets", {}).get("amount", 0))
        acc["totalBorrowings"] = money_input("Total borrowings", "tb", default_amt=acc.get("totalBorrowings", {}).get("amount", 0))

        ex = fin["existingDebt"]
        ex["monthlyFinanceCommitments"] = money_input("Monthly finance commitments", "mfc", default_amt=ex.get("monthlyFinanceCommitments", {}).get("amount", 0))

        st.subheader("Risk & consents")
        r = app["risk"]
        r["hasCCJsOrInsolvency"] = st.selectbox("Any CCJs/insolvency?", ["yes", "no", "unknown"], index=["yes", "no", "unknown"].index(r.get("hasCCJsOrInsolvency", "unknown")))
        app["consents"]["hasAuthorityToShareData"] = st.checkbox("I have authority to share applicant data", value=bool(app["consents"]["hasAuthorityToShareData"]))
        app["consents"]["dataProcessingConsent"] = st.checkbox("Data processing consent", value=bool(app["consents"]["dataProcessingConsent"]))

with tab6:
    st.subheader("Readiness")
    rr = evaluate_rules(app)
    status, expl = readiness_score(rr)
    st.metric("Readiness", status, expl)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.write("**Missing (required)**")
        st.write(rr.missing if rr.missing else "—")
    with c2:
        st.write("**Conditional required now**")
        st.write(rr.required_now if rr.required_now else "—")
    with c3:
        st.write("**Flags**")
        st.write(rr.flags if rr.flags else "—")
    with c4:
        st.write("**Suggestions**")
        st.write(rr.suggestions if rr.suggestions else "—")

    st.divider()
    st.subheader("Funding narrative (draft)")
    narrative = f"""
Applicant: {app['applicant'].get('legalName','')}
Business: UK vehicle hire ({app['applicant']['industry'].get('subSector','')}).
Request: {app['facility'].get('productType','')} over {app['facility'].get('termMonths','')} months for {app['facility'].get('financePurpose','')}.

Operations: fleet size {app['fleetOps'].get('fleetSizeTotal','')}, utilisation {app['fleetOps'].get('avgUtilisationPercent','')}%, revenue per vehicle per month approx GBP {app['fleetOps'].get('avgRevenuePerVehiclePerMonth',{}).get('amount',0):,.0f}.
Key risks addressed: {", ".join(rr.flags) if rr.flags else "no major flags identified in intake"}.
""".strip()
    st.text_area("Narrative (copy/paste into lender email or pack)", value=narrative, height=180)

if save_btn:
    app_path.write_text(json.dumps(app, indent=2))
    st.succe
