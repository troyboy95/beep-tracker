"""Probe candidate ATS boards: does the board exist, how many India posts, how many fresher-ish?

Used to build/verify `beep/sources/companies.toml`. Run: python scripts/probe_boards.py
"""

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

UA = "BeepTracker/0.1 (board probe)"
INDIA = re.compile(
    r"\b(india|bengaluru|bangalore|mumbai|delhi|new delhi|gurgaon|gurugram|noida|hyderabad|pune|"
    r"chennai|kolkata|ahmedabad|jaipur|kochi|coimbatore|chandigarh|indore|trivandrum|"
    r"thiruvananthapuram|mysore|mysuru|nagpur|vadodara|bhubaneswar|lucknow|goa)\b",
    re.I,
)
FRESHER = re.compile(
    r"\b(intern(ship)?|trainee|graduate|fresher|entry[- ]level|junior|jr\.?|apprentice|"
    r"new grad|campus|sde[- ]?(1|i)\b|engineer[- ](1|i)\b|associate (software|engineer|analyst))",
    re.I,
)
SENIOR = re.compile(r"\b(senior|sr\.?|lead|manager|director|principal|staff|head|vp|architect)\b", re.I)

CANDIDATES = {
    "greenhouse": [
        "razorpaysoftwareprivatelimited", "razorpay", "phonepe", "groww", "meesho", "cred",
        "postman", "browserstack", "druva", "rubrik", "databricks", "stripe", "mongodb",
        "confluent", "okta", "twilio", "cloudflare", "purestorage", "rippling", "sprinklr",
        "cohesity", "airbnb", "gitlab", "elastic", "coinbase", "zscaler", "hackerrank",
        "chargebee", "innovaccer", "sharechat", "dream11", "zomato", "swiggy", "unacademy",
        "upgrad", "whatfix", "mindtickle", "darwinbox", "zeta", "slice", "jupiter", "khatabook",
        "urbancompany", "lenskart", "nykaa", "policybazaar", "pinelabs", "turing", "uniphore",
        "observeai", "highradius", "moengage", "clevertap", "netomi", "gupshup", "acko",
        "dunzo", "spinny", "cars24", "oyo", "makemytrip", "inmobi", "glance", "verse",
        "toast", "samsara", "datadog", "figma", "notion", "canva", "atlassian", "zendesk",
        "hubspot", "dropbox", "discord", "pinterest", "lyft", "doordash", "instacart",
        "robinhood", "affirm", "chime", "brex", "plaid", "gusto", "anthropic", "openai",
        "nutanix", "paloaltonetworks", "crowdstrike", "fivetran", "dbtlabs", "hashicorp",
        "sumologic", "newrelic", "appdynamics", "thoughtspot", "gojek", "grab", "agoda",
    ],
    "lever": [
        "razorpay", "cred", "meesho", "paytm", "zeta", "upstox", "jupiter", "smallcase",
        "cleartax", "unacademy", "dunzo", "swiggy", "zomato", "sharechat", "mpl", "dream11",
        "fampay", "jar", "kreditbee", "slice", "ofbusiness", "zepto", "blinkit", "licious",
        "porter", "rapido", "bharatpe", "groww", "coindcx", "polygon", "atlan", "hasura",
        "postman", "browserstack", "freshworks", "chargebee", "leadsquared", "capillary",
        "simplilearn", "byjus", "vedantu", "physicswallah", "scaler", "interviewbit",
        "mindtickle", "darwinbox", "eightfold", "sigmoid", "tredence", "fractal", "mu-sigma",
        "latentview", "tiger-analytics", "quantiphi", "thoughtworks", "nium", "pine-labs",
        "palantir", "netflix", "spotify", "zoox", "shopify", "plaid", "ripple",
    ],
    "ashby": [
        "sarvam", "atlan", "zepto", "plivo", "mercor", "hasura", "composio", "supabase",
        "posthog", "linear", "vercel", "ramp", "deel", "remote", "openai", "cohere",
        "notion", "airtable", "replit", "krutrim", "neysa", "pocketfm", "kuku", "rupeek",
        "jar", "fi", "smallest", "giva", "snitch", "bluestone", "classplus", "sprinto",
        "rocketlane", "zluri", "hevo", "hevodata", "chargebee", "clear", "cleartax",
    ],
    "smartrecruiters": [
        "Visa", "BoschGroup", "Ubisoft2", "ServiceNow", "Freshworks", "Equinix", "Wipro",
        "SiemensHealthineers", "Continental", "Philips", "SAP", "NielsenIQ", "IKEA",
        "McDonalds", "Sodexo", "Accor", "Experian", "Western Digital", "WesternDigital",
        "Publicis", "PublicisGroupe", "Capgemini", "Infosys", "Mphasis", "Hitachi",
        "AbbVie", "Pfizer", "Novartis", "Sanofi", "Uber", "Swiggy", "Zomato", "Delhivery",
        "Bajaj", "TataCommunications", "Mastercard", "LinkedIn3", "SquarePoint", "Avaya",
        "Sutherland", "Teleperformance", "Concentrix", "TTEC", "Genpact", "EXL",
    ],
}

# Round 2: India-heavy employers (startups + MNC GCCs). Merged into CANDIDATES.
ROUND2 = {
    "greenhouse": [
        "juspay", "zeptonow", "cultfit", "curefit", "practo", "pharmeasy", "delhivery",
        "shiprocket", "yellowai", "haptik", "nobroker", "eruditus", "emeritus", "greatlearning",
        "tekion", "icertis", "amagi", "netskope", "rapid7", "pubmatic", "gainsight", "cloudera",
        "commvault", "zuora", "thoughtworks", "deliveryhero", "wayfair", "zoominfo", "mediaocean",
        "games24x7", "moveinsync", "bluestacks", "nference", "headout", "smallcase", "sprinklr",
        "zinnia", "wingify", "vwo", "freshtohome", "groupon", "expedia", "bookingcom",
        "unity3d", "ea", "zynga", "riotgames", "sonyinteractiveentertainment", "mpl",
        "mobileprogrammingleague", "chargebee", "postmanlabs", "browserstackinc", "acceldata",
        "lambdatest", "hevodata", "signzy", "perfios", "m2p", "cashfree", "razorpayx",
        "paypal", "intuit", "walmart", "target", "lowes", "sabre", "amadeus", "honeywell",
        "philips", "ge", "gehealthcare", "siemens", "schneiderelectric", "abb", "hp", "dell",
        "cisco", "vmware", "broadcom", "redhat", "suse", "canonical", "jfrog", "harness",
        "sentinelone", "tanium", "rubrikinc", "cohesityinc", "appian", "pega", "mulesoft",
        "tiket", "tokopedia", "shopee", "carousell", "xendit", "nium", "airwallex", "wise",
        "revolut", "n26", "klarna", "adyen", "checkout", "dlocal", "ebanx",
    ],
    "lever": [
        "pharmeasy", "cars24", "spinny", "upgrad", "eruditus", "hiver", "leena-ai", "kapture",
        "exotel", "yellow", "whatfix", "bigbasket", "dailyhunt", "verse", "pocketfm", "kukufm",
        "jupiter-money", "fi-money", "navi", "acko", "plum", "onecard", "uni", "stashfin",
        "lendingkart", "cashfree", "juspay", "setu", "perfios", "m2p", "zolve", "fittr",
        "healthifyme", "innovaccer", "qure", "tricog", "shipsy", "locus", "fareye", "loginext",
        "increff", "unbxd", "netcore", "webengage", "moengage", "zoho", "kissflow", "chargebee",
        "sprinklr", "druva", "rippling", "lenskart", "nykaa", "mamaearth", "honasa", "boat",
        "licious", "country-delight", "milkbasket", "bluestone", "caratlane", "urbanic",
        "myntra", "flipkart", "phonepe", "ola", "olaelectric", "ather", "ultraviolette",
        "agnikul", "skyroot", "pixxel", "dhruva", "ideaforge", "zipline", "zetwerk", "infra-market",
        "moglix", "udaan", "jumbotail", "dealshare", "citymall", "apna", "workindia",
    ],
    "ashby": [
        "cashfree", "juspay", "setu", "pocketfm", "plum", "rocketlane", "zeta", "kuku",
        "trupeer", "sarvamai", "krutrim", "gnani", "observe", "unify", "atomicwork",
        "spotdraft", "zenskar", "airbase", "sprinto", "scalekit", "superops", "chargeflow",
        "rapido", "zepto", "swiggy", "cred", "groww", "dezerv", "smallcase", "neo",
        "fold", "jar-app", "kreditbee", "slice", "uniapp", "stable-money", "powerup",
    ],
    "smartrecruiters": [
        "Ericsson", "Atos", "AtosSyntel", "Allianz", "Decathlon", "SocieteGenerale",
        "SchneiderElectric", "Valeo", "ZF", "ZFFriedrichshafenAG", "Mahle", "Forvia", "Unilever",
        "Nestle", "DHL", "KuehneNagel", "Cargill", "Syngenta", "Bayer", "Merck", "Medtronic",
        "Skechers", "Visa1", "Square", "Lululemon", "Hilton", "Marriott", "Hyatt", "IHG",
        "Wolterskluwer", "WoltersKluwer", "RELX", "Elsevier", "LSEG", "Moodys", "SPGlobal",
        "Fitch", "Morningstar", "Gartner", "Ipsos", "Kantar", "Dentsu", "WPP", "Omnicom",
        "Havas", "ITC", "Infineon", "NXP", "STMicroelectronics", "Renesas", "Micron",
        "AppliedMaterials", "LamResearch", "KLA", "ASML", "Synopsys", "Cadence", "Ansys",
        "Autodesk", "Dassault", "PTC", "Hexagon", "Trimble", "Bentley", "Zebra", "Honeywell",
        "Emerson", "Rockwell", "Eaton", "Cummins", "Caterpillar", "Deere", "Volvo", "Daimler",
        "MercedesBenz", "BMW", "Stellantis", "Renault", "Hyundai", "Kia", "Tata", "Mahindra",
    ],
}
for _ats, _tokens in ROUND2.items():
    CANDIDATES[_ats] = list(dict.fromkeys(CANDIDATES[_ats] + _tokens))


def _loc_text(*parts) -> str:
    return " | ".join(p for p in parts if p)


def probe_greenhouse(c: httpx.Client, t: str):
    r = c.get(f"https://boards-api.greenhouse.io/v1/boards/{t}/jobs")
    if r.status_code != 200:
        return None
    jobs = r.json().get("jobs", [])
    return [(j["title"], _loc_text((j.get("location") or {}).get("name"))) for j in jobs]


def probe_lever(c: httpx.Client, t: str):
    r = c.get(f"https://api.lever.co/v0/postings/{t}", params={"mode": "json"})
    if r.status_code != 200:
        return None
    out = []
    for j in r.json():
        cat = j.get("categories") or {}
        locs = cat.get("allLocations") or [cat.get("location")]
        out.append((j.get("text", ""), _loc_text(*locs, j.get("country"))))
    return out


def probe_ashby(c: httpx.Client, t: str):
    r = c.get(f"https://api.ashbyhq.com/posting-api/job-board/{t}")
    if r.status_code != 200:
        return None
    out = []
    for j in r.json().get("jobs", []):
        sec = [s.get("location") for s in j.get("secondaryLocations") or []]
        country = (((j.get("address") or {}).get("postalAddress")) or {}).get("addressCountry")
        out.append((j.get("title", ""), _loc_text(j.get("location"), *sec, country)))
    return out


def probe_smartrecruiters(c: httpx.Client, t: str):
    out, offset = [], 0
    while True:
        r = c.get(
            f"https://api.smartrecruiters.com/v1/companies/{t}/postings",
            params={"country": "in", "limit": 100, "offset": offset},
        )
        if r.status_code != 200:
            return None
        data = r.json()
        content = data.get("content", [])
        for j in content:
            loc = j.get("location") or {}
            lvl = (j.get("experienceLevel") or {}).get("id", "")
            out.append((f"{j.get('name', '')} [{lvl}]", _loc_text(loc.get("city"), "India")))
        offset += len(content)
        if not content or offset >= data.get("totalFound", 0) or offset >= 3000:
            break
        time.sleep(0.3)
    # SR returns 200 + empty for unknown companies; treat empty as "not found"
    return out or None


PROBES = {
    "greenhouse": probe_greenhouse,
    "lever": probe_lever,
    "ashby": probe_ashby,
    "smartrecruiters": probe_smartrecruiters,
}


def run_one(ats: str, token: str):
    with httpx.Client(headers={"User-Agent": UA}, timeout=20) as c:
        try:
            jobs = PROBES[ats](c, token)
        except Exception as e:  # noqa: BLE001
            return ats, token, None, str(e)[:60]
    if jobs is None:
        return ats, token, None, "not found"
    india = [j for j in jobs if INDIA.search(j[1]) or (ats == "smartrecruiters")]
    fresh = [j for j in india if not SENIOR.search(j[0].split(" [")[0])
             and (FRESHER.search(j[0]) or "[entry_level]" in j[0] or "[internship]" in j[0])]
    return ats, token, {"total": len(jobs), "india": len(india), "fresher": len(fresh),
                        "sample": [t for t, _ in fresh[:4]]}, None


def main() -> int:
    tasks = [(a, t) for a, ts in CANDIDATES.items() for t in ts]
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda x: run_one(*x), tasks))
    hits = [r for r in results if r[2] and r[2]["india"] > 0]
    hits.sort(key=lambda r: -r[2]["fresher"])
    for ats, tok, s, _ in hits:
        print(f"{ats:16} {tok:32} total={s['total']:4} india={s['india']:4} "
              f"fresher={s['fresher']:3}  {s['sample']}")
    print(f"\nboards w/ India posts: {len(hits)}; "
          f"sum india={sum(r[2]['india'] for r in hits)}; "
          f"sum fresher-ish={sum(r[2]['fresher'] for r in hits)}")
    json.dump([{"ats": a, "token": t, **s} for a, t, s, _ in hits],
              open("scripts/probe_results.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
