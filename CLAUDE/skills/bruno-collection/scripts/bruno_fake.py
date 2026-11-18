"""Realistic random values for the generated collection.

`FAKE_JS` is the JavaScript library (`fake`) that lives once in the collection-level
script (`globalThis.__lib.fake`); `fake_expr` picks the call for one request field from
its name and its declared example. Python 3.9 and newer, stdlib only.

Values are ASCII. `fake.opts.spaces = false` (edit it in the collection script) removes
spaces from names, addresses and places, for a receiver that cannot take them.
"""

from __future__ import annotations

import json
import re

FAKE_JS = r"""const fake = (() => {
  const opts = { spaces: true };
  const FIRST = ["Budi", "Siti", "Agus", "Dewi", "Rina", "Andi", "Wahyu", "Ratna", "Eko", "Fitri", "Hendra", "Putri", "Joko", "Lestari", "Dian", "Rizky", "Bayu", "Ayu", "Yoga", "Nur"];
  const LAST = ["Santoso", "Wijaya", "Saputra", "Hidayat", "Pratama", "Kusuma", "Nugroho", "Setiawan", "Rahayu", "Utomo", "Firmansyah", "Susanto", "Permana", "Wibowo", "Handayani", "Purnomo", "Ramadhan", "Maulana", "Siregar", "Gunawan"];
  const PROV = [11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 31, 32, 33, 34, 35, 36, 51, 52, 53, 61, 62, 63, 64, 65, 71, 72, 73, 74, 75, 76, 81, 82, 91, 92, 93, 94];
  const WORDS = ["Mawar", "Melati", "Kenanga", "Anggrek", "Cempaka", "Dahlia", "Merdeka", "Sudirman", "Pahlawan", "Cendana"];
  const sp = (s) => (opts.spaces ? s : s.replace(/ /g, ""));
  const digits = (n) => chars(n, "0123456789");
  const two = (n) => String(n).padStart(2, "0");
  const iso = (ms) => new Date(ms).toISOString();
  const day = 86400000;
  return {
    opts,
    sp,
    uuid: () => ["bruno" + chars(3, "0123456789abcdef"), chars(4, "0123456789abcdef"), "4" + chars(3, "0123456789abcdef"), pick(["8", "9", "a", "b"]) + chars(3, "0123456789abcdef"), chars(12, "0123456789abcdef")].join("-"),
    name: () => sp(pick(FIRST) + " " + pick(LAST)),
    company: () => sp("PT " + pick(LAST) + " " + pick(["Sejahtera", "Makmur", "Abadi", "Mandiri", "Jaya"])),
    email: () => (pick(FIRST) + "." + pick(LAST) + rnd(1, 99) + "@example.com").toLowerCase(),
    phone: () => "+62-8" + pick(["11", "12", "13", "19", "21", "22", "31", "38", "52", "53", "57", "78", "81", "82", "85", "95", "96", "97"]) + digits(8),
    ktp: () => two(pick(PROV)) + two(rnd(1, 79)) + two(rnd(1, 30)) + two(rnd(1, 28) + (rnd(0, 1) ? 40 : 0)) + two(rnd(1, 12)) + two((1970 + rnd(0, 35)) % 100) + String(rnd(1, 9999)).padStart(4, "0"),
    dob: () => iso(Date.UTC(1970, 0, 1) + rnd(0, 33 * 365) * day).slice(0, 10),
    date: () => iso(Date.now() - rnd(1, 3 * 365) * day).slice(0, 10),
    datetime: () => iso(Date.now() - rnd(1, 2 * 365) * day).replace(/\.\d{3}Z$/, "Z"),
    address: () => sp("Jl. " + pick(WORDS) + " No. " + rnd(1, 150)),
    word: () => pick(WORDS).toUpperCase(),
    words: (n) => sp(Array.from({ length: n }, () => pick(WORDS)).join(" ")),
    gender: () => pick(["M", "F"]),
    provinceId: () => String(pick(PROV)),
    province: () => sp(pick(["BANTEN", "DKI JAKARTA", "JAWA BARAT", "JAWA TENGAH", "JAWA TIMUR"])),
    city: () => sp(pick(["KOTA TANGERANG SELATAN", "KOTA BEKASI", "KOTA BANDUNG", "KOTA SURABAYA", "KOTA SEMARANG"])),
    district: () => sp(pick(["PONDOK AREN", "BEKASI TIMUR", "COBLONG", "TEGALSARI", "GAJAH MUNGKUR"])),
    subDistrict: () => sp(pick(["PONDOK KARYA", "MARGAHAYU", "LEBAK GEDE", "KEPUTRAN", "BENDAN NGISOR"])),
    plate: () => sp(pick(["B", "D", "F", "L", "N", "AB", "AD", "DK", "BK", "H"]) + " " + rnd(1, 9999) + " " + chars(rnd(1, 3), "ABCDEFGHIJKLMNOPQRSTUVWXYZ")),
    latitude: () => Math.round((-10 + 15 * Math.random()) * 1e6) / 1e6,
    longitude: () => Math.round((95 + 46 * Math.random()) * 1e6) / 1e6,
    ip: () => [rnd(11, 223), rnd(0, 255), rnd(0, 255), rnd(1, 254)].join("."),
    like: (ex) => ex.replace(/[A-Z]/g, () => chars(1, "ABCDEFGHIJKLMNOPQRSTUVWXYZ")).replace(/[a-z]/g, () => chars(1, "abcdefghijklmnopqrstuvwxyz")).replace(/[0-9]/g, () => digits(1)),
  };
})();
"""

_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{11,12}")
_ISO_DATETIME = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[a-z]+")
_PLACEHOLDER = re.compile(
    r"\b(SOME|SAMPLE|OPTIONAL|VALUE|NAMA|IDENTIFIER)\b|^[A-Z]+_ID$", re.IGNORECASE
)
PERSON_NAMES = {"name", "mother_name", "account_name"}
COMPANY_NAMES = {"company_name", "merchant_name", "outlet_name"}
PLACES = {
    "province": "fake.province()",
    "city": "fake.city()",
    "district": "fake.district()",
    "sub_district": "fake.subDistrict()",
}


def fake_expr(path: str, example: object) -> str | None:
    """JS expression for a plain string field, or None to keep the `TEST_` fallback.

    The declared example decides the shape (uuid, 16 digits, ISO date, e-mail, phone,
    digit or code pattern); the field name decides what an example cannot (person or
    company name, place, address).
    """
    if not isinstance(example, str) or not example:
        return None
    key = path.rsplit(".", 1)[-1]
    if _UUID.fullmatch(example):
        return "fake.uuid()"
    if re.fullmatch(r"\d{16}", example):
        return "fake.ktp()"
    if _ISO_DATETIME.match(example):
        return "fake.datetime()"
    if _ISO_DATE.fullmatch(example):
        return "fake.dob()" if key == "dob" else "fake.date()"
    if _EMAIL.fullmatch(example):
        return "fake.email()"
    if example.startswith("+62"):
        return "fake.phone()"
    if key in PERSON_NAMES:
        return "fake.name()"
    if key in COMPANY_NAMES:
        return "fake.company()"
    if key in PLACES:
        return PLACES[key]
    if key == "address":
        return "fake.address()"
    if key == "gender":
        return "fake.gender()"
    if key == "province_id":
        return "fake.provinceId()"
    if key == "ip":
        return "fake.ip()"
    if key == "license_plate":
        return "fake.plate()"
    placeholder = bool(_PLACEHOLDER.search(example))
    has_digit = any(ch.isdigit() for ch in example)
    if example.isdigit() and len(example) == 1:
        return json.dumps(example)  # a one-digit code is a choice from a closed list
    if has_digit and " " not in example and len(example) <= 20:
        if "." in example and any(ch.isalpha() for ch in example):
            return json.dumps(example)
        return f"fake.like({json.dumps(example)})"
    if placeholder and " " not in example:
        return "fake.uuid()"
    if placeholder:
        # one word, never two: the receiver signs some forwarded values as they are,
        # and a space in one of them made the HMAC signature fail (tested on dev).
        return "fake.word()"
    if " " in example:
        return f"fake.sp({json.dumps(example)})"
    return json.dumps(example)


def int_expr(path: str, example: object) -> str | None:
    """JS expression for a plain integer field with a declared example, else None."""
    if not isinstance(example, int) or isinstance(example, bool) or example <= 0:
        return None
    key = path.rsplit(".", 1)[-1]
    if "year" in key:
        return "rnd(2012, 2025)"
    low, high = max(1, example // 2), example * 2
    if example >= 100000 and re.search(r"amount|payment|income|price|per_month", key):
        return (
            f"Math.round(rnd({low}, {high}) / 100000) * 100000"  # a round money value
        )
    return f"rnd({low}, {high})"


def float_expr(path: str) -> str | None:
    """Coordinates must be real ones: a random float gave latitude 662."""
    key = path.rsplit(".", 1)[-1]
    if key in ("latitude", "lat"):
        return "fake.latitude()"
    if key in ("longitude", "lng", "lon"):
        return "fake.longitude()"
    return None
