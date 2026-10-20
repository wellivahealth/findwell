"""Build the place-lookup files used by the location search.

Source: the BSD-licensed zipcodes package by Dav Glass
(https://github.com/davglass/zipcodes), which bundles US ZIP code and
Canadian postal area (FSA) centroids. Clone it, then run:

    python3 make_geo.py /path/to/zipcodes

Writes public/assets/geo/:
  zip/<first 3 digits>.json   {"85704": [lat, lng], ...}
  ca.json                     {"T2P": [lat, lng], ...}  (first 3 postal characters)
  places/<first letter>.json  {"tucson": [["AZ", lat, lng], ...], ...}
                              candidates sorted largest first, so a bare
                              "Springfield" resolves to the biggest one.
"""
import json, os, re, sys
from collections import defaultdict

SRC = sys.argv[1] if len(sys.argv) > 1 else "../davglass/zipcodes"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public", "assets", "geo")

PROVINCES = {"Alberta": "AB", "British Columbia": "BC", "Manitoba": "MB",
             "New Brunswick": "NB", "Newfoundland": "NL", "Newfoundland and Labrador": "NL",
             "Nova Scotia": "NS", "Northwest Territories": "NT", "Nunavut": "NU",
             "Ontario": "ON", "Prince Edward Island": "PE", "Quebec": "QC",
             "Saskatchewan": "SK", "Yukon": "YT"}
CA_SUFFIX = re.compile(r"\s+(north|south|east|west|central|northeast|northwest|southeast|"
                       r"southwest|inner|outer|outskirts|city|region|downtown|core|"
                       r"inner \w+|\w+ central)$", re.I)


CA_PREFIX = re.compile(r"^(downtown|central|east|west|north|south|old)\s+", re.I)


def median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2]


def load(path):
    text = open(path, encoding="utf-8").read()
    return json.JSONDecoder().raw_decode(text[text.index("{"):])[0]


def put(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, separators=(",", ":"), sort_keys=True)


def norm(s):
    s = s.lower().replace(".", "").replace("'", "")
    s = re.sub(r"\bsaint\b", "st", s)
    return re.sub(r"\s+", " ", s).strip()


def main():
    us = load(os.path.join(SRC, "lib", "codes.js"))
    ca = load(os.path.join(SRC, "lib", "codesCanada.js"))

    zips = defaultdict(dict)
    places = defaultdict(list)          # (name, region) -> [(lat, lng)]
    for z, r in us.items():
        if not re.fullmatch(r"\d{5}", z) or r.get("latitude") is None:
            continue
        if not (15 < r["latitude"] < 72 and -180 < r["longitude"] < -60):
            continue                    # a handful of source rows have flipped signs
        lat, lng = round(r["latitude"], 3), round(r["longitude"], 3)
        zips[z[:3]][z] = [lat, lng]
        places[(norm(r["city"]), r["state"])].append((lat, lng))

    fsa = {}
    for z, r in ca.items():
        if r.get("latitude") is None:
            continue
        lat, lng = round(r["latitude"], 3), round(r["longitude"], 3)
        fsa[z.upper()] = [lat, lng]
        prov = PROVINCES.get(r["state"])
        name = re.sub(r"\s*\(.*?\)\s*", " ", r["city"]).strip()
        if re.search(r"government|business reply|po boxes|processing", name, re.I):
            continue
        for _ in range(2):
            name = CA_SUFFIX.sub("", name)
            name = CA_PREFIX.sub("", name)
        if prov and name:
            places[(norm(name), prov)].append((lat, lng))
            if name.lower().endswith(" city"):
                places[(norm(name[:-5]), prov)].append((lat, lng))

    for pre, d in zips.items():
        put(os.path.join(OUT, "zip", pre + ".json"), d)
    put(os.path.join(OUT, "ca.json"), fsa)

    by_letter = defaultdict(lambda: defaultdict(list))
    for (name, region), pts in places.items():
        lat = median([p[0] for p in pts])
        lng = median([p[1] for p in pts])
        key = name[0] if name[0].isalpha() else "0"
        by_letter[key][name].append((len(pts), [region, round(lat, 3), round(lng, 3)]))
    for letter, names in by_letter.items():
        put(os.path.join(OUT, "places", letter + ".json"),
            {n: [c for _, c in sorted(v, key=lambda t: -t[0])] for n, v in names.items()})
    print(f"{sum(len(d) for d in zips.values())} ZIPs, {len(fsa)} Canadian areas, "
          f"{len(places)} places")


if __name__ == "__main__":
    main()
