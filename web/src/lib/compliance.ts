/** Verbatim openFDA / FAERS caveat. */
export const FDA_CAVEAT =
  "There is no certainty that the reported event was actually due to the product. The information in these reports has not been scientifically or otherwise verified as to a cause and effect relationship and cannot be used to estimate the incidence of these events.";

export const RESEARCH_LINE =
  "For research and informational purposes only. Not medical advice. Do not stop or change any medication without talking to your doctor.";

export const FDA_ATTRIBUTION =
  "Data provided by the U.S. Food and Drug Administration (https://open.fda.gov)";

export const FDA_INDEPENDENCE =
  "This site is not affiliated with or endorsed by the U.S. Food and Drug Administration.";

export const NCBI_DISCLAIMER_URL = "https://www.ncbi.nlm.nih.gov/home/about/policies/";

export const SITE_NAME = "Open Health Signals";
export const PROJECT_NAME = "Inflammation Signal Monitor";
export const OPERATOR_NAME = "Rakesh Pai";
export const CONTACT_EMAIL = "contact@openhealthsignals.org";
export const COPYRIGHT_LINE = "© 2026 Open Health Signals";
export const SIGNAL_CAVEAT = "A reporting signal is not proof a drug caused an event.";
export const MEDWATCH_URL =
  "https://www.fda.gov/safety/medwatch-fda-safety-information-and-adverse-event-reporting-program";

export function publicPostalAddress(): string {
  return (process.env.NEXT_PUBLIC_POSTAL_ADDRESS || "").trim();
}
