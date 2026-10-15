export type SubscribeConfig = {
  provider: "buttondown" | "resend";
  configured: boolean;
  action: string;
  consent: string;
  note: string;
};

const USERNAME = /^[A-Za-z0-9_-]+$/;

export function subscribeConfig(): SubscribeConfig {
  const provider = (process.env.NEXT_PUBLIC_NEWSLETTER_PROVIDER || "buttondown").trim().toLowerCase();
  const consent =
    "I agree to receive the weekly Inflammation Signal Monitor briefing by email. A confirmation message comes first. I am added only after I open that link, and I can unsubscribe from any issue.";

  if (provider === "resend") {
    const endpoint = (process.env.NEXT_PUBLIC_SUBSCRIBE_ENDPOINT || "").trim();
    const configured = endpoint.startsWith("https://") || endpoint.startsWith("http://");
    return {
      provider: "resend",
      configured,
      action: configured ? endpoint : "",
      consent,
      note: configured
        ? "Resend sends the confirmation email. The briefing starts after you open the link."
        : "This build has no subscribe endpoint. Set NEXT_PUBLIC_SUBSCRIBE_ENDPOINT to the Resend function URL and rebuild.",
    };
  }

  const username = (process.env.NEXT_PUBLIC_BUTTONDOWN_USERNAME || "").trim();
  const configured = USERNAME.test(username);
  return {
    provider: "buttondown",
    configured,
    action: configured ? `https://buttondown.com/api/emails/embed-subscribe/${username}` : "",
    consent,
    note: configured
      ? "Buttondown sends the confirmation email. The briefing starts after you open the link."
      : "This build has no Buttondown username. Set NEXT_PUBLIC_BUTTONDOWN_USERNAME and rebuild. The list stays empty until you confirm.",
  };
}
