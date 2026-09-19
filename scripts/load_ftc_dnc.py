"""
Bulk-load the FTC Do Not Call Reported Calls CSV(s) into MongoDB Atlas.

Get the data from https://www.ftc.gov/policy-notices/open-government/data-sets/do-not-call-data
(daily/monthly CSV downloads), then:

    python scripts/load_ftc_dnc.py path/to/dnc_complaints_*.csv [more.csv ...]

Reads MONGODB_URI / MONGODB_DB from .env. Numbers are aggregated per file set
(one doc per number with a report count) and upserted, so re-running is safe.
The free Atlas tier is 512 MB: use --limit to cap distinct numbers if needed.
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from pymongo import UpdateOne

from pipeline.phone import normalize_e164
from pipeline.scam_number_gate import get_collection

PHONE_COLUMNS = ("company_phone_number", "phone_number", "phone", "number")
DATE_COLUMNS = ("violation_date", "created_dateofviolation", "date")


def _pick(fieldnames, candidates):
    lowered = {name.lower().strip(): name for name in fieldnames}
    return next((lowered[c] for c in candidates if c in lowered), None)


def aggregate(paths, limit=None):
    numbers: dict[str, dict] = {}
    for path in paths:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            phone_col = _pick(reader.fieldnames or [], PHONE_COLUMNS)
            date_col = _pick(reader.fieldnames or [], DATE_COLUMNS)
            if not phone_col:
                sys.exit(f"{path}: no phone column found in header {reader.fieldnames}")
            for row in reader:
                number = normalize_e164(row.get(phone_col))
                if not number:
                    continue
                entry = numbers.get(number)
                if entry is None:
                    if limit and len(numbers) >= limit:
                        continue
                    entry = numbers[number] = {"report_count": 0, "last_reported": None}
                entry["report_count"] += 1
                date = (row.get(date_col) or "").strip() if date_col else ""
                if date and (entry["last_reported"] is None or date > entry["last_reported"]):
                    entry["last_reported"] = date
    return numbers


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", nargs="+")
    parser.add_argument("--limit", type=int, help="cap the number of distinct numbers loaded")
    args = parser.parse_args()

    if not os.getenv("MONGODB_URI"):
        sys.exit("MONGODB_URI is not set — add it to .env (see .env.example)")

    numbers = aggregate(args.csv, args.limit)
    print(f"{len(numbers)} distinct numbers aggregated; writing to Atlas...")
    coll = get_collection()
    ops = [
        UpdateOne({"_id": n}, {"$set": {"report_count": v["report_count"], "last_reported": v["last_reported"]}}, upsert=True)
        for n, v in numbers.items()
    ]
    for i in range(0, len(ops), 5000):
        coll.bulk_write(ops[i : i + 5000], ordered=False)
        print(f"  {min(i + 5000, len(ops))}/{len(ops)}")
    print("done. collection count:", coll.estimated_document_count())


if __name__ == "__main__":
    main()
