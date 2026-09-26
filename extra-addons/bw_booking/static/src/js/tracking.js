/** @odoo-module **/

/**
 * Brothers Wash — booking conversion tracking.
 *
 * 1. On every page: remembers the ad click (gclid / fbclid / utm_*) in a first-party
 *    cookie for 90 days, so a booking made later is still attributed to the ad.
 * 2. After a booking is submitted: fires the conversion into
 *      - dataLayer  (event "bw_booking_submitted", for Google Tag Manager)
 *      - gtag       (GA4 "generate_lead" + Google Ads conversion)
 *      - fbq        (Meta Pixel "Lead", eventID shared with the Conversions API)
 *
 * Exposed as window.bwTracking so both booking forms (theme homepage widget and
 * the /booking page) can use it.
 */

const ATTR_COOKIE = "bw_attr";
const ATTR_DAYS = 90;
const CLICK_PARAMS = ["gclid", "gbraid", "wbraid", "fbclid"];
const UTM_PARAMS = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"];

function readCookie(name) {
    const match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[1]) : "";
}

function writeCookie(name, value, days) {
    document.cookie = name + "=" + encodeURIComponent(value) +
        "; path=/; max-age=" + days * 86400 + "; SameSite=Lax";
}

function getConfig() {
    const el = document.getElementById("bw_tracking_config");
    if (!el || !el.dataset.config) {
        return {};
    }
    try {
        return JSON.parse(el.dataset.config);
    } catch {
        return {};
    }
}

function log(...args) {
    if (getConfig().test_mode) {
        console.info("[bw_tracking]", ...args);
    }
}

function readStoredAttribution() {
    try {
        return JSON.parse(readCookie(ATTR_COOKIE) || "{}");
    } catch {
        return {};
    }
}

function captureAttribution() {
    const params = new URLSearchParams(window.location.search);
    const found = {};
    for (const key of [...CLICK_PARAMS, ...UTM_PARAMS]) {
        const value = params.get(key);
        if (value) {
            found[key] = value.slice(0, 255);
        }
    }
    const referrer = document.referrer || "";
    const external = referrer && !referrer.startsWith(window.location.origin);
    if (Object.keys(found).length) {
        // Last ad click wins
        found.landing_url = window.location.href.slice(0, 500);
        found.referrer = external ? referrer.slice(0, 500) : "";
        found.ts = Date.now();
        writeCookie(ATTR_COOKIE, JSON.stringify(found), ATTR_DAYS);
        log("attribution stored", found);
    } else if (external && !readCookie(ATTR_COOKIE)) {
        // Organic visit: remember where the visitor came from, never overwrite an ad click
        writeCookie(ATTR_COOKIE, JSON.stringify({
            landing_url: window.location.href.slice(0, 500),
            referrer: referrer.slice(0, 500),
            ts: Date.now(),
        }), ATTR_DAYS);
    }
}

/**
 * Attribution sent together with the booking.
 */
function getAttribution() {
    const attr = readStoredAttribution();
    attr.fbp = readCookie("_fbp");
    attr.fbc = readCookie("_fbc");
    if (!attr.fbc && attr.fbclid) {
        attr.fbc = "fb.1." + (attr.ts || Date.now()) + "." + attr.fbclid;
    }
    if (!attr.landing_url) {
        attr.landing_url = window.location.href.slice(0, 500);
    }
    delete attr.ts;
    return attr;
}

/**
 * Fire the booking conversion. `payload` comes from the server
 * (bw.booking._bw_tracking_payload): event_id, booking_ref, value, currency, email, phone, items.
 */
function bookingSubmitted(payload) {
    if (!payload || !payload.event_id) {
        return;
    }
    const config = getConfig();
    const currency = payload.currency || config.currency || "CZK";
    const value = Number(payload.value) || 0;

    window.dataLayer = window.dataLayer || [];
    const dlEvent = {
        event: "bw_booking_submitted",
        booking_id: payload.booking_ref,
        event_id: payload.event_id,
        value: value,
        currency: currency,
        vehicle: payload.vehicle,
        items: payload.items || [],
        user_data: { email: payload.email, phone_number: payload.phone },
    };
    window.dataLayer.push(dlEvent);
    log("dataLayer", dlEvent);

    if (typeof window.gtag === "function") {
        if (payload.email || payload.phone) {
            // Enhanced conversions: Google hashes these itself
            window.gtag("set", "user_data", {
                email: payload.email || undefined,
                phone_number: payload.phone || undefined,
            });
        }
        const ga4 = {
            currency: currency,
            value: value,
            transaction_id: payload.booking_ref,
            items: payload.items || [],
        };
        if (config.test_mode) {
            ga4.debug_mode = true;
        }
        window.gtag("event", "generate_lead", ga4);
        log("gtag generate_lead", ga4);
        if (config.ads_send_to) {
            const conversion = {
                send_to: config.ads_send_to,
                value: value,
                currency: currency,
                transaction_id: payload.booking_ref,
            };
            if (config.test_mode) {
                // Test mode (dev server): never count a Google Ads conversion
                log("gtag conversion SKIPPED (test mode)", conversion);
            } else {
                window.gtag("event", "conversion", conversion);
                log("gtag conversion", conversion);
            }
        }
    } else {
        log("gtag not loaded - GA4 / Google Ads skipped");
    }

    if (typeof window.fbq === "function") {
        const data = {
            value: value,
            currency: currency,
            content_name: "Booking",
            content_type: "product",
            content_ids: (payload.items || []).map((item) => item.item_id),
            num_items: (payload.items || []).length,
        };
        window.fbq("track", "Lead", data, { eventID: payload.event_id });
        log("fbq Lead", data, payload.event_id);
    } else {
        log("fbq not loaded - Meta Pixel skipped");
    }
}

window.bwTracking = { getAttribution, bookingSubmitted };

captureAttribution();

// /booking thank-you page renders the payload server side
function fireServerRenderedConversion() {
    const el = document.getElementById("bw_booking_conversion");
    if (el && el.dataset.tracking) {
        try {
            bookingSubmitted(JSON.parse(el.dataset.tracking));
        } catch (e) {
            console.warn("[bw_tracking]", e);
        }
    }
}
// The frontend bundle is loaded lazily, DOMContentLoaded may be long gone
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fireServerRenderedConversion);
} else {
    fireServerRenderedConversion();
}
