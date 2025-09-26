import requests
import json
import os
from pathlib import Path

# =========================
# ⚙️ Nastavenia (z environment variables)
# =========================
URL = "https://api.bezrealitky.cz/graphql/"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

SEEN_FILE = Path("seen.json")

QUERY = """query AdvertList(
  $estateType: [EstateType]
  $offerType: [OfferType]
  $disposition: [Disposition]
  $priceTo: Int
  $regionOsmIds: [ID]
  $boundaryPoints: [GPSPointInput]
  $currency: Currency
  $limit: Int = 15
  $offset: Int = 0
  $order: ResultOrder = TIMEORDER_DESC
) {
  listAdverts(
    offerType: $offerType
    estateType: $estateType
    disposition: $disposition
    priceTo: $priceTo
    regionOsmIds: $regionOsmIds
    boundaryPoints: $boundaryPoints
    currency: $currency
    limit: $limit
    offset: $offset
    order: $order
  ) {
    list {
      id
      uri
      price
      isNew
    }
    totalCount
  }
}"""

VARIABLES = {
    "offerType": ["PRONAJEM"],
    "estateType": ["BYT"],
    "disposition": ["GARSONIERA","DISP_1_KK","DISP_1_1"],
    "priceTo": 18000,
    "regionOsmIds": [],
    "boundaryPoints":[
        {"lng":14.542766752113863,"lat":50.129848668740635},
        {"lng":14.293500639030896,"lat":50.129848668740635},
        {"lng":14.293500639030896,"lat":50.033045643935},
        {"lng":14.542766752113863,"lat":50.033045643935},
        {"lng":14.542766752113863,"lat":50.129848668740635}
    ],
    "currency":"CZK"
}

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set; skipping telegram send.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        r = requests.post(url, data=payload, timeout=15)
        print("Telegram status:", r.status_code)
    except Exception as e:
        print("Chyba pri posielaní Telegram správy:", e)

def load_seen():
    if SEEN_FILE.exists():
        try:
            return set(json.loads(SEEN_FILE.read_text()))
        except Exception:
            return set()
    return set()

def save_seen(seen):
    try:
        SEEN_FILE.write_text(json.dumps(list(seen)))
    except Exception as e:
        print("Chyba pri ukladaní seen.json:", e)

def main():
    print("Volám API...")

    try:
        r = requests.post(
            URL,
            json={"query": QUERY, "variables": VARIABLES},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
    except Exception as e:
        print("Request error:", e)
        return 1

    print("Status:", r.status_code)
    if r.status_code != 200:
        print("Body:", r.text)
        return 1

    payload = r.json()
    adverts = payload.get("data", {}).get("listAdverts", {}).get("list", [])
    print(f"Nájdených inzerátov: {len(adverts)}")

    seen = load_seen()

    for ad in adverts:
        ad_id = ad.get("id")
        if not ad_id:
            continue
        if ad_id not in seen and ad.get("isNew", False):
            link = f"https://www.bezrealitky.cz/nemovitosti-byty-domy/{ad['uri']}"
            msg = f"🆕 Nová ponuka!\n{link}\nCena: {ad.get('price')} Kč"
            send_telegram(msg)
            print("Posielam notifikáciu pre:", ad_id, link)
        seen.add(ad_id)

    save_seen(seen)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
