"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";

import { functionsBase } from "@/lib/functions";
import { buildPageView, intlRegion, localWallClock, shouldTrack, tabSessionId } from "@/lib/pageview";

let lastTrackedPath = "";

export function PageViewLogger() {
  const pathname = usePathname() || "/";

  useEffect(() => {
    if (lastTrackedPath === pathname) return;
    const view = window;
    if (
      !shouldTrack({
        hostname: view.location.hostname,
        userAgent: view.navigator.userAgent,
        doNotTrack: view.navigator.doNotTrack,
        globalPrivacyControl: (view.navigator as Navigator & { globalPrivacyControl?: boolean }).globalPrivacyControl,
      })
    ) {
      return;
    }
    const base = functionsBase();
    if (!base) return;
    lastTrackedPath = pathname;
    const locale = Intl.DateTimeFormat().resolvedOptions();
    const payload = buildPageView({
      path: pathname,
      referrer: document.referrer,
      search: view.location.search,
      localTime: localWallClock(new Date()),
      timeZone: locale.timeZone,
      region: intlRegion(view.navigator.language, locale.locale),
      userAgent: view.navigator.userAgent,
      screenWidth: view.screen?.width || view.innerWidth,
      language: view.navigator.language,
      maxTouchPoints: view.navigator.maxTouchPoints || 0,
      sessionId: tabSessionId(view.sessionStorage, () => view.crypto.randomUUID()),
    });
    const body = JSON.stringify(payload);
    const url = `${base}/pageview`;
    try {
      if (typeof view.navigator.sendBeacon === "function") {
        const blob = new Blob([body], { type: "text/plain;charset=UTF-8" });
        if (view.navigator.sendBeacon(url, blob)) return;
      }
    } catch {
      // fetch keepalive below
    }
    fetch(url, {
      method: "POST",
      body,
      headers: { "content-type": "application/json" },
      keepalive: true,
      mode: "cors",
    }).catch(() => {});
  }, [pathname]);

  return null;
}
