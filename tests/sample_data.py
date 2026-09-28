"""Hand-built records in the ClinicalTrials.gov v2 JSON shape, for tests only.

The values are made up. They exist to exercise the code paths
(pagination, missing modules, month-only dates, combined phases),
not to produce findings.
"""

import random

REAL_LOOKING = {
    "protocolSection": {
        "identificationModule": {"nctId": "NCT00000001", "briefTitle": "Example trial"},
        "statusModule": {
            "overallStatus": "TERMINATED",
            "whyStopped": "Slow accrual",
            "startDateStruct": {"date": "2016-03", "type": "ACTUAL"},
            "completionDateStruct": {"date": "2018-09-15", "type": "ACTUAL"},
        },
        "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Example Pharma", "class": "INDUSTRY"}},
        "designModule": {
            "studyType": "INTERVENTIONAL",
            "phases": ["PHASE1", "PHASE2"],
            "enrollmentInfo": {"count": 42, "type": "ACTUAL"},
        },
        "armsInterventionsModule": {"interventions": [
            {"type": "DRUG", "name": "Osimertinib"},
            {"type": "BIOLOGICAL", "name": "MK-3475"},
            {"type": "DRUG", "name": "Osimertinib"},
            {"type": "PROCEDURE", "name": "Biopsy"},
        ]},
        "contactsLocationsModule": {"locations": [
            {"country": "China"}, {"country": "United States"}, {"country": "China"},
        ]},
    }
}

DRUGS = ["Pembrolizumab", "Osimertinib", "Carboplatin", "Sotorasib", "Ivonescimab",
         "Datopotamab deruxtecan", "Alectinib", "Bevacizumab", "Placebo", "Nivolumab"]
STATUSES = ["COMPLETED", "TERMINATED", "WITHDRAWN", "RECRUITING", "ACTIVE_NOT_RECRUITING", "UNKNOWN"]
CLASSES = ["INDUSTRY", "INDUSTRY", "OTHER", "NIH", "FED", "OTHER_GOV", "NETWORK", "AMBIG", "UNKNOWN"]
PHASES = [["PHASE1"], ["PHASE1", "PHASE2"], ["PHASE2"], ["PHASE3"], ["PHASE2", "PHASE3"],
          ["EARLY_PHASE1"], ["PHASE4"], ["NA"], []]
REASONS = ["Poor accrual", "Business decision", "Futility at interim analysis",
           "Unacceptable toxicity", "Lack of funding", "PI left the institution", "", None]
COUNTRIES = ["United States", "China", "Japan", "Germany", "Spain", "Korea, Republic of"]


def synthetic(n=400, seed=1):
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        start_y, start_m = rnd.randint(2008, 2026), rnd.randint(1, 12)
        months = rnd.randint(3, 100)
        end_y, end_m = start_y + (start_m + months - 1) // 12, (start_m + months - 1) % 12 + 1
        status = rnd.choice(STATUSES)
        s = {"protocolSection": {
            "identificationModule": {"nctId": f"NCT{i:08d}"},
            "statusModule": {
                "overallStatus": status,
                "startDateStruct": {"date": f"{start_y}-{start_m:02d}",
                                    "type": "ACTUAL" if start_y < 2026 else "ESTIMATED"},
                "completionDateStruct": {"date": f"{end_y}-{end_m:02d}-01",
                                         "type": "ACTUAL" if status == "COMPLETED" else "ESTIMATED"},
            },
            "sponsorCollaboratorsModule": {"leadSponsor": {
                "name": f"Sponsor {rnd.randint(1, 30)}", "class": rnd.choice(CLASSES)}},
            "designModule": {"studyType": rnd.choice(["INTERVENTIONAL"] * 6 + ["OBSERVATIONAL"]),
                             "phases": rnd.choice(PHASES),
                             "enrollmentInfo": {"count": rnd.randint(0, 900)}},
            "armsInterventionsModule": {"interventions": [
                {"type": rnd.choice(["DRUG", "BIOLOGICAL", "RADIATION"]), "name": rnd.choice(DRUGS)}
                for _ in range(rnd.randint(1, 3))]},
            "contactsLocationsModule": {"locations": [
                {"country": c} for c in rnd.sample(COUNTRIES, rnd.randint(0, 3))]},
        }}
        if status in ("TERMINATED", "WITHDRAWN") and (r := rnd.choice(REASONS)) is not None:
            s["protocolSection"]["statusModule"]["whyStopped"] = r
        if i % 37 == 0:                       # missing module
            del s["protocolSection"]["armsInterventionsModule"]
        if i % 53 == 0:                       # missing location module
            del s["protocolSection"]["contactsLocationsModule"]
        out.append(s)
    out.append(out[5])                        # duplicate record
    return out
