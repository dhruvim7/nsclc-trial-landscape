"""Map intervention names to mechanism classes used in NSCLC.

Intervention names in the registry are free text ("Pembrolizumab", "MK-3475",
"pembrolizumab 200 mg IV"), so matching is done on a normalised string with
spaces, hyphens and punctuation removed. The list covers the main approved
agents plus common development code names; it is not exhaustive, and
anything unmatched is simply left unclassified.

Order matters: the first matching class wins for a given drug. ADCs come first
so that, for example, trastuzumab deruxtecan is counted as an ADC rather than
as a HER2 agent, and PD-1-based bispecifics come before plain PD-(L)1.
"""

import re

MECHANISMS = [
    ("ADC", [
        "deruxtecan", "vedotin", "govitecan", "tirumotecan", "ravtansine", "emtansine",
        "ds8201", "ds1062", "datodxd", "u31402", "skb264", "mk2870", "abbv399",
    ]),
    ("PD-1-based bispecific", [
        "ivonescimab", "ak112", "smt112", "cadonilimab", "ak104",
    ]),
    ("PD-1/PD-L1", [
        "pembrolizumab", "mk3475", "nivolumab", "bms936558", "ono4538",
        "atezolizumab", "mpdl3280a", "durvalumab", "medi4736", "cemiplimab",
        "avelumab", "tislelizumab", "bgba317", "sintilimab", "ibi308",
        "camrelizumab", "shr1210", "toripalimab", "js001", "serplulimab", "hlx10",
        "sugemalimab", "cs1001", "penpulimab", "ak105", "envafolimab",
        "adebrelimab", "shr1316", "benmelstobart", "retifanlimab", "dostarlimab",
        "cosibelimab", "zimberelimab", "socazolimab", "antipd1", "antipdl1",
    ]),
    ("CTLA-4", ["ipilimumab", "tremelimumab"]),
    ("EGFR", [
        "osimertinib", "azd9291", "gefitinib", "erlotinib", "afatinib", "dacomitinib",
        "icotinib", "aumolertinib", "almonertinib", "furmonertinib", "firmonertinib",
        "alflutinib", "lazertinib", "befotertinib", "sunvozertinib", "mobocertinib",
        "rezivertinib", "zipalertinib", "amivantamab", "necitumumab", "cetuximab",
        "nimotuzumab",
    ]),
    ("ALK/ROS1", [
        "crizotinib", "alectinib", "brigatinib", "lorlatinib", "ceritinib",
        "ensartinib", "iruplinalkib", "envonalkib", "entrectinib", "repotrectinib",
        "taletrectinib",
    ]),
    ("KRAS", [
        "sotorasib", "amg510", "adagrasib", "mrtx849", "divarasib", "garsorasib",
        "glecirasib", "fulzerasib", "olomorasib", "opnurasib", "jdq443", "d1553",
    ]),
    ("MET", ["capmatinib", "tepotinib", "savolitinib", "glumetinib", "vebreltinib"]),
    ("RET", ["selpercatinib", "pralsetinib"]),
    ("HER2 (non-ADC)", ["pyrotinib", "zongertinib", "poziotinib"]),
    ("BRAF/MEK", ["dabrafenib", "trametinib", "encorafenib", "binimetinib"]),
    ("Anti-angiogenic", [
        "bevacizumab", "ramucirumab", "anlotinib", "nintedanib", "endostar", "endostatin",
    ]),
]

MECHANISM_ORDER = [name for name, _ in MECHANISMS]


def normalise(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def classify_drug(name):
    key = normalise(name)
    for mechanism, keywords in MECHANISMS:
        if any(k in key for k in keywords):
            return mechanism
    return None


def classify_trial(drug_names):
    """Sorted list of distinct mechanism classes across a trial's drugs."""
    found = {m for m in (classify_drug(d) for d in drug_names) if m}
    return [m for m in MECHANISM_ORDER if m in found]
