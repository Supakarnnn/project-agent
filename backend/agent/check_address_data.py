import json
import os
import re
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
#data from https://github.com/earthchie/jquery.Thailand.js/blob/master/jquery.Thailand.js/database/raw_database/raw_database.json
DEFAULT_PATH = BASE_DIR / "raw_Thailand_database.json"

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
        prov = clean_name(r.get("province"))
        amph = clean_name(r.get("amphoe")) #เขต
        subdist = clean_name(r.get("district")) #แขวง

        try:
            z = int(r.get("zipcode"))
        except:
            continue

        #ใช้เพื่อเช็คตรงครบหมดเลยไหม
        idx_full.add((prov, amph, subdist, z))

        #ใช้เช็คว่า ชื่อถูก แต่ zipcode ผิด
        idx_nozip.setdefault((prov, amph, subdist), set()).add(z)
        
        #ใช้เช็คว่า zipcode มีจริง แต่ชื่อไม่ตรง
        idx_zip.setdefault(z, []).append((prov, amph, subdist))

    return idx_full, idx_nozip, idx_zip


def val_address(
    province: str,# จังหวัด
    district: str,# เขต / อำเภอ
    subdistrict: str,# แขวง / ตำบล
    zipcode
) -> dict:
    prov = clean_name(province)
    amph = clean_name(district)
    dist = clean_name(subdistrict)

    try:
        z = int(zipcode)
    except:
        return {
            "ok": False,
            "reason": "zipcode_not_number"
        }

    idx_full, idx_nozip, idx_zip = load_address()

    #ตรงหมด
    if (prov, amph, dist, z) in idx_full:
        return {
            "ok": True,
            "reason": "match"
        }

    #zipcode ไม่ตรง
    if (prov, amph, dist) in idx_nozip:
        return {
            "ok": False,
            "reason": "zipcode_mismatch",
        }

    #zipcode มี แต่ชื่อไม่ตรง
    if z in idx_zip:
        return {
            "ok": False,
            "reason": "name_mismatch_for_zip",
        }

    return {
        "ok": False,
        "reason": "not_found",
    }
