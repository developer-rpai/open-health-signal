"""Curated drugs, conditions, and MedDRA terms for the monitor.

Drug classes follow the product scope: NSAIDs, systemic corticosteroids,
TNF inhibitors, interleukin inhibitors, and JAK inhibitors used in
inflammatory disease (tofacitinib, upadacitinib, baricitinib). A small
set of other immunomodulators is included so the FAERS background for
those products is visible, but they are not part of the validation panel.

Ingredient strings are the uppercase openFDA ``generic_name.exact`` values.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Drug:
    key: str
    generic_name: str
    drug_class: str
    label: str
    brands: tuple[str, ...] = ()
    spotlight: bool = True


@dataclass(frozen=True)
class DrugClass:
    key: str
    label: str
    short_label: str


@dataclass(frozen=True)
class Topic:
    key: str
    label: str
    topic_type: str
    pubmed_term: str
    trials_query: str | None = None


DRUG_CLASSES: tuple[DrugClass, ...] = (
    DrugClass("nsaid", "NSAID", "NSAIDs"),
    DrugClass("corticosteroid", "Corticosteroid", "Corticosteroids"),
    DrugClass("tnf_inhibitor", "TNF inhibitor", "TNF inhibitors"),
    DrugClass("il_inhibitor", "Interleukin inhibitor", "IL inhibitors"),
    DrugClass("jak_inhibitor", "JAK inhibitor", "JAK inhibitors"),
    DrugClass("other_immunomodulator", "Other immunomodulator", "Other immunomodulators"),
)

CLASS_BY_KEY = {item.key: item for item in DRUG_CLASSES}

DRUGS: tuple[Drug, ...] = (
    Drug("ibuprofen", "IBUPROFEN", "nsaid", "Ibuprofen", ("advil", "motrin")),
    Drug("naproxen", "NAPROXEN", "nsaid", "Naproxen", ("aleve", "naprosyn")),
    Drug("celecoxib", "CELECOXIB", "nsaid", "Celecoxib", ("celebrex",)),
    Drug("diclofenac", "DICLOFENAC", "nsaid", "Diclofenac", ("voltaren",)),
    Drug("meloxicam", "MELOXICAM", "nsaid", "Meloxicam", ("mobic",)),
    Drug("prednisone", "PREDNISONE", "corticosteroid", "Prednisone"),
    Drug("methylprednisolone", "METHYLPREDNISOLONE", "corticosteroid", "Methylprednisolone", ("medrol",)),
    Drug("dexamethasone", "DEXAMETHASONE", "corticosteroid", "Dexamethasone"),
    Drug("adalimumab", "ADALIMUMAB", "tnf_inhibitor", "Adalimumab", ("humira",)),
    Drug("infliximab", "INFLIXIMAB", "tnf_inhibitor", "Infliximab", ("remicade",)),
    Drug("etanercept", "ETANERCEPT", "tnf_inhibitor", "Etanercept", ("enbrel",)),
    Drug("certolizumab_pegol", "CERTOLIZUMAB PEGOL", "tnf_inhibitor", "Certolizumab pegol", ("cimzia",)),
    Drug("golimumab", "GOLIMUMAB", "tnf_inhibitor", "Golimumab", ("simponi",)),
    Drug("ustekinumab", "USTEKINUMAB", "il_inhibitor", "Ustekinumab", ("stelara",)),
    Drug("secukinumab", "SECUKINUMAB", "il_inhibitor", "Secukinumab", ("cosentyx",)),
    Drug("ixekizumab", "IXEKIZUMAB", "il_inhibitor", "Ixekizumab", ("taltz",)),
    Drug("risankizumab", "RISANKIZUMAB", "il_inhibitor", "Risankizumab", ("skyrizi",)),
    Drug("guselkumab", "GUSELKUMAB", "il_inhibitor", "Guselkumab", ("tremfya",)),
    Drug("tocilizumab", "TOCILIZUMAB", "il_inhibitor", "Tocilizumab", ("actemra",)),
    Drug("tofacitinib", "TOFACITINIB", "jak_inhibitor", "Tofacitinib", ("xeljanz",)),
    Drug("upadacitinib", "UPADACITINIB", "jak_inhibitor", "Upadacitinib", ("rinvoq",)),
    Drug("baricitinib", "BARICITINIB", "jak_inhibitor", "Baricitinib", ("olumiant",)),
    Drug("abatacept", "ABATACEPT", "other_immunomodulator", "Abatacept", ("orencia",), spotlight=False),
    Drug("vedolizumab", "VEDOLIZUMAB", "other_immunomodulator", "Vedolizumab", ("entyvio",), spotlight=False),
    Drug("belimumab", "BELIMUMAB", "other_immunomodulator", "Belimumab", ("benlysta",), spotlight=False),
)

DRUG_BY_KEY = {drug.key: drug for drug in DRUGS}


def drugs_in_class(class_key: str) -> list[Drug]:
    return [drug for drug in DRUGS if drug.drug_class == class_key]


def spotlight_drugs() -> list[Drug]:
    return [drug for drug in DRUGS if drug.spotlight]


# Prespecified MedDRA preferred terms. British spelling matches FAERS.
SAFETY_REACTIONS: tuple[str, ...] = (
    "PULMONARY EMBOLISM",
    "DEEP VEIN THROMBOSIS",
    "THROMBOSIS",
    "MYOCARDIAL INFARCTION",
    "CEREBROVASCULAR ACCIDENT",
    "CEREBRAL INFARCTION",
    "TUBERCULOSIS",
    "PULMONARY TUBERCULOSIS",
    "PNEUMONIA",
    "SEPSIS",
    "HERPES ZOSTER",
    "GASTROINTESTINAL HAEMORRHAGE",
    "GASTRIC ULCER",
    "DUODENAL ULCER",
    "MELAENA",
    "HAEMATEMESIS",
    "GASTRIC ULCER HAEMORRHAGE",
    "ACUTE KIDNEY INJURY",
    "HEPATIC FAILURE",
    "LYMPHOMA",
)

# Product-use and coding artifacts. They dominate FAERS count endpoints
# and are not treated as safety reactions in the default dashboard view.
ADMIN_TERMS = frozenset(
    {
        "DRUG INEFFECTIVE",
        "OFF LABEL USE",
        "OFF LABEL USE OF DEVICE",
        "PRODUCT DOSE OMISSION ISSUE",
        "PRODUCT DOSE OMISSION",
        "INTENTIONAL PRODUCT USE ISSUE",
        "PRODUCT USE ISSUE",
        "PRODUCT USE IN UNAPPROVED INDICATION",
        "WRONG TECHNIQUE IN PRODUCT USAGE PROCESS",
        "NO ADVERSE EVENT",
        "THERAPEUTIC PRODUCT EFFECT INCOMPLETE",
        "THERAPEUTIC RESPONSE DECREASED",
        "PRODUCT AVAILABILITY ISSUE",
        "PRODUCT STORAGE ERROR",
        "EXPIRED PRODUCT ADMINISTERED",
        "CIRCUMSTANCE OR INFORMATION CAPABLE OF LEADING TO MEDICATION ERROR",
        "INAPPROPRIATE SCHEDULE OF PRODUCT ADMINISTRATION",
        "WRONG PRODUCT ADMINISTERED",
        "EXTRA DOSE ADMINISTERED",
        "INCORRECT DOSE ADMINISTERED",
        "DRUG DOSE OMISSION",
        "TREATMENT NONCOMPLIANCE",
        "INTENTIONAL PRODUCT MISUSE",
        "PRODUCT QUALITY ISSUE",
        "DEVICE FAILURE",
        "FATIGUE",
        "MALAISE",
    }
)

INDICATION_TERMS = frozenset(
    {
        "RHEUMATOID ARTHRITIS",
        "PSORIASIS",
        "PSORIATIC ARTHROPATHY",
        "CROHN'S DISEASE",
        "COLITIS ULCERATIVE",
        "INFLAMMATORY BOWEL DISEASE",
        "SYSTEMIC LUPUS ERYTHEMATOSUS",
        "ANKYLOSING SPONDYLITIS",
        "JUVENILE IDIOPATHIC ARTHRITIS",
    }
)


def _normalize_term(reaction: str) -> str:
    return (
        reaction.upper()
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("`", "'")
        .replace("^", "'")
    )


def is_admin_term(reaction: str) -> bool:
    upper = _normalize_term(reaction)
    if upper in ADMIN_TERMS:
        return True
    return upper.startswith(("DEVICE ", "PRODUCT ", "CIRCUMSTANCE OR INFORMATION"))


def is_indication_term(reaction: str) -> bool:
    return _normalize_term(reaction) in INDICATION_TERMS


CONDITIONS: tuple[Topic, ...] = (
    Topic(
        "rheumatoid_arthritis",
        "Rheumatoid arthritis",
        "condition",
        '"rheumatoid arthritis"[MeSH Terms]',
        "Rheumatoid Arthritis",
    ),
    Topic(
        "crohns_disease",
        "Crohn's disease",
        "condition",
        '"crohn disease"[MeSH Terms]',
        "Crohn Disease",
    ),
    Topic(
        "ulcerative_colitis",
        "Ulcerative colitis",
        "condition",
        '"colitis, ulcerative"[MeSH Terms]',
        "Ulcerative Colitis",
    ),
    Topic(
        "psoriasis",
        "Psoriasis",
        "condition",
        '"psoriasis"[MeSH Terms]',
        "Psoriasis",
    ),
    Topic(
        "lupus",
        "Systemic lupus erythematosus",
        "condition",
        '"lupus erythematosus, systemic"[MeSH Terms]',
        "Systemic Lupus Erythematosus",
    ),
)

DRUG_TOPICS: tuple[Topic, ...] = (
    Topic(
        "nsaid",
        "NSAIDs",
        "drug_class",
        '"anti-inflammatory agents, non-steroidal"[MeSH Terms]',
    ),
    Topic(
        "corticosteroid",
        "Corticosteroids",
        "drug_class",
        '"glucocorticoids"[MeSH Terms] AND (prednisone OR methylprednisolone)',
    ),
    Topic(
        "tnf_inhibitor",
        "TNF inhibitors",
        "drug_class",
        '"tumor necrosis factor inhibitors"[MeSH Terms] OR adalimumab OR infliximab OR etanercept',
    ),
    Topic(
        "il_inhibitor",
        "IL inhibitors",
        "drug_class",
        "ustekinumab OR secukinumab OR ixekizumab OR risankizumab OR guselkumab OR tocilizumab",
    ),
    Topic(
        "jak_inhibitor",
        "JAK inhibitors",
        "drug_class",
        '"janus kinase inhibitors"[MeSH Terms] OR tofacitinib OR upadacitinib OR baricitinib',
    ),
)

PUBLICATION_TOPICS: tuple[Topic, ...] = CONDITIONS + DRUG_TOPICS


def drug_search_clause(generics: list[str]) -> str:
    """openFDA clause matching any of the given exact generic names."""
    parts = [f'patient.drug.openfda.generic_name.exact:"{name}"' for name in generics]
    if len(parts) == 1:
        return parts[0]
    return "(" + " OR ".join(parts) + ")"


def class_search_clause(class_key: str) -> str:
    return drug_search_clause([drug.generic_name for drug in drugs_in_class(class_key)])


def reaction_clause(reaction: str) -> str:
    escaped = reaction.replace('"', "")
    return f'patient.reaction.reactionmeddrapt.exact:"{escaped}"'


# Sanity checks. JAK thrombosis and MACE are tested against TNF inhibitors,
# the active comparator used in ORAL Surveillance. TNF–tuberculosis and
# NSAID–gastrointestinal bleeding are tested against the rest of FAERS,
# where those signals are historically large.
VALIDATION_CHECKS: tuple[dict[str, str], ...] = (
    {
        "id": "jak_vs_tnf_pulmonary_embolism",
        "group": "JAK inhibitors — thrombosis and MACE",
        "title": "Pulmonary embolism, JAK inhibitors versus TNF inhibitors",
        "key": "jak_inhibitor",
        "reaction": "PULMONARY EMBOLISM",
        "analysis": "active_comparator",
        "comparator": "tnf_inhibitor",
    },
    {
        "id": "jak_vs_tnf_deep_vein_thrombosis",
        "group": "JAK inhibitors — thrombosis and MACE",
        "title": "Deep vein thrombosis, JAK inhibitors versus TNF inhibitors",
        "key": "jak_inhibitor",
        "reaction": "DEEP VEIN THROMBOSIS",
        "analysis": "active_comparator",
        "comparator": "tnf_inhibitor",
    },
    {
        "id": "jak_vs_tnf_thrombosis",
        "group": "JAK inhibitors — thrombosis and MACE",
        "title": "Thrombosis, JAK inhibitors versus TNF inhibitors",
        "key": "jak_inhibitor",
        "reaction": "THROMBOSIS",
        "analysis": "active_comparator",
        "comparator": "tnf_inhibitor",
    },
    {
        "id": "jak_vs_tnf_myocardial_infarction",
        "group": "JAK inhibitors — thrombosis and MACE",
        "title": "Myocardial infarction, JAK inhibitors versus TNF inhibitors",
        "key": "jak_inhibitor",
        "reaction": "MYOCARDIAL INFARCTION",
        "analysis": "active_comparator",
        "comparator": "tnf_inhibitor",
    },
    {
        "id": "jak_vs_tnf_cerebrovascular_accident",
        "group": "JAK inhibitors — thrombosis and MACE",
        "title": "Cerebrovascular accident, JAK inhibitors versus TNF inhibitors",
        "key": "jak_inhibitor",
        "reaction": "CEREBROVASCULAR ACCIDENT",
        "analysis": "active_comparator",
        "comparator": "tnf_inhibitor",
    },
    {
        "id": "tnf_tuberculosis",
        "group": "TNF inhibitors — tuberculosis",
        "title": "Tuberculosis, TNF inhibitors versus all other FAERS reports",
        "key": "tnf_inhibitor",
        "reaction": "TUBERCULOSIS",
        "analysis": "database",
        "comparator": "all_faers",
    },
    {
        "id": "tnf_pulmonary_tuberculosis",
        "group": "TNF inhibitors — tuberculosis",
        "title": "Pulmonary tuberculosis, TNF inhibitors versus all other FAERS reports",
        "key": "tnf_inhibitor",
        "reaction": "PULMONARY TUBERCULOSIS",
        "analysis": "database",
        "comparator": "all_faers",
    },
    {
        "id": "nsaid_gi_haemorrhage",
        "group": "NSAIDs — gastrointestinal bleeding",
        "title": "Gastrointestinal haemorrhage, NSAIDs versus all other FAERS reports",
        "key": "nsaid",
        "reaction": "GASTROINTESTINAL HAEMORRHAGE",
        "analysis": "database",
        "comparator": "all_faers",
    },
    {
        "id": "nsaid_gastric_ulcer",
        "group": "NSAIDs — gastrointestinal bleeding",
        "title": "Gastric ulcer, NSAIDs versus all other FAERS reports",
        "key": "nsaid",
        "reaction": "GASTRIC ULCER",
        "analysis": "database",
        "comparator": "all_faers",
    },
    {
        "id": "nsaid_melaena",
        "group": "NSAIDs — gastrointestinal bleeding",
        "title": "Melaena, NSAIDs versus all other FAERS reports",
        "key": "nsaid",
        "reaction": "MELAENA",
        "analysis": "database",
        "comparator": "all_faers",
    },
)


DISCLAIMER = (
    "Inflammation Signal Monitor is for research and public-health surveillance. "
    "It is not medical advice, and it does not estimate how often an adverse reaction "
    "occurs or prove that a drug caused it. FAERS is a spontaneous-report system with "
    "under-reporting, duplicate reports, and no exposure denominator. Do not start or "
    "stop a medicine based on this site. Talk with a clinician. Report adverse events "
    "to FDA MedWatch."
)
