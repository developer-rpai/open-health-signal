"""Wording shared by the dashboard copy and the weekly newsletter."""

from __future__ import annotations

import os

# Verbatim openFDA / FAERS caveat.
FDA_CAVEAT = (
    "There is no certainty that the reported event was actually due to the product. "
    "The information in these reports has not been scientifically or otherwise verified "
    "as to a cause and effect relationship and cannot be used to estimate the incidence "
    "of these events."
)

RESEARCH_LINE = (
    "For research and informational purposes only. Not medical advice. "
    "Do not stop or change any medication without talking to your doctor."
)

# Exact attribution string, including the URL. No FDA logo is used.
FDA_ATTRIBUTION = "Data provided by the U.S. Food and Drug Administration (https://open.fda.gov)"

FDA_INDEPENDENCE = (
    "This site is not affiliated with or endorsed by the U.S. Food and Drug Administration."
)

NCBI_DISCLAIMER_URL = "https://www.ncbi.nlm.nih.gov/home/about/policies/"

POSTAL_PLACEHOLDER = "Postal address placeholder — set NEWSLETTER_POSTAL_ADDRESS"


def postal_address() -> str:
    value = os.environ.get("NEWSLETTER_POSTAL_ADDRESS", "").strip()
    return value or POSTAL_PLACEHOLDER
