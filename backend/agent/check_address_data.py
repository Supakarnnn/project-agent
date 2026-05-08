import json
import os
import re
from functools import lru_cache
from pathlib import Path

#data from https://github.com/earthchie/jquery.Thailand.js/blob/master/jquery.Thailand.js/database/raw_database/raw_database.json


BASE_DIR = Path(__file__).parent
DEFAULT_PATH = BASE_DIR / "thailand_database_edit.json"
DATA = Path(os.getenv("TH_ADDR_DB_PATH", str(DEFAULT_PATH))).resolve()


def clean_name(s: str) -> str:
    if not s:
        return ""
    s = str(s).strip()
    s = re.sub(r"^(จังหวัด|จ\.|อำเภอ|อ\.|เขต|ตำบล|ต\.|แขวง)\s*", "", s)
    s = re.sub(r"\s+", " ", s)
    if s in ["กรุงเทพ", "กรุงเทพฯ", "กทม", "กทม."]:
        s = "กรุงเทพมหานคร"
    return s


@lru_cache(maxsize=1)
def load_address():
    rows = json.loads(DATA.read_text(encoding="utf-8"))

    idx_full = set()
    idx_nozip = {}
    idx_zip = {}

    for r in rows:
        prov    = clean_name(r.get("province"))
        dist    = clean_name(r.get("district"))      # อำเภอ / เขต
        subdist = clean_name(r.get("subdistrict"))   # ตำบล / แขวง

        try:
            z = int(r.get("zipcode"))
        except (TypeError, ValueError):
            continue

        idx_full.add((prov, dist, subdist, z))
        idx_nozip.setdefault((prov, dist, subdist), set()).add(z)
        idx_zip.setdefault(z, []).append((prov, dist, subdist))

    return idx_full, idx_nozip, idx_zip


def val_address(
    province: str,      # จังหวัด
    district: str,      # อำเภอ / เขต
    subdistrict: str,   # ตำบล / แขวง
    zipcode,
) -> dict:
    prov    = clean_name(province)
    dist    = clean_name(district)
    subdist = clean_name(subdistrict)

    try:
        z = int(zipcode)
    except (TypeError, ValueError):
        return {"ok": False, "reason": "zipcode_not_number"}

    idx_full, idx_nozip, idx_zip = load_address()

    # ✅ ตรงหมดทุก field
    if (prov, dist, subdist, z) in idx_full:
        return {"ok": True, "reason": "match"}

    # ❌ ชื่อถูกหมด แต่ zipcode ผิด
    if (prov, dist, subdist) in idx_nozip:
        valid_zips = sorted(idx_nozip[(prov, dist, subdist)])
        return {
            "ok": False,
            "reason": "zipcode_mismatch",
            "suggested_zipcode": valid_zips,
        }

    # ❌ zipcode มีในระบบ แต่ชื่อไม่ตรง
    if z in idx_zip:
        suggestions = [
            {"province": p, "district": d, "subdistrict": s}
            for p, d, s in idx_zip[z]
        ]
        return {
            "ok": False,
            "reason": "name_mismatch_for_zip",
            "suggested_address": suggestions,
        }

    # ❌ ไม่พบเลย
    return {"ok": False, "reason": "not_found"}