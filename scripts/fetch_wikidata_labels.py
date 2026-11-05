#!/usr/bin/env python3
"""Pulls each linked monument's Spanish label and aliases ("also known as")
from Wikidata.

Two things come out of it that the JCyL catalogue cannot give:

- the label is written the way people write the name (with its accents -
  JCyL ships names in capitals without them, "IGLESIA DE LA ASUNCION"), and
- the aliases are the other names the same monument goes by, which is what
  someone searching for it may type instead of the catalogue's name.

build_monument_pages.py puts both into each page's HTML and JSON-LD.

Run: python3 scripts/fetch_wikidata_labels.py
Needs: web/data/cyl_monuments_wikidata.json (scripts/build_dataset.py)
Writes: data/raw/wikidata_labels.json - {jcyl_id: {"qid", "label", "aliases"}}
        for every linked monument that has a Spanish label. Rewritten from
        scratch on each run (about 45 requests, 50 items each): unlike a
        Wikipedia extract this is cheap, and labels and aliases are edited
        often enough that "already fetched" is not a reason to skip one.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from project import user_agent

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
DATASET_FILE = os.path.join(os.path.dirname(__file__), "..", "web", "data", "cyl_monuments_wikidata.json")
OUT_FILE = os.path.join(RAW_DIR, "wikidata_labels.json")
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
UA = user_agent("patrimonioabierto-labels")
BATCH = 50


def api_get(url, retries=4):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.load(resp)
            if "error" in data:
                raise RuntimeError(data["error"].get("info", data["error"]))
            return data
        except (urllib.error.URLError, RuntimeError):
            if attempt == retries - 1:
                raise
            time.sleep(2 ** (attempt + 1))


def main():
    records = json.load(open(DATASET_FILE, encoding="utf-8"))
    # Same exclusion as fetch_wikipedia_extracts.py: a multi-QID conflict has
    # no single right item to take a label from.
    by_qid = {}
    for r in records:
        q = r["wikidata_qid"]
        if r["already_linked"] and not r["wikidata_conflict"] and q:
            by_qid[q[0] if isinstance(q, list) else q] = r["jcyl_id"]
    qids = sorted(by_qid)
    print(f"{len(qids)} linked monuments")

    out = {}
    batches = [qids[i : i + BATCH] for i in range(0, len(qids), BATCH)]
    for i, batch in enumerate(batches, 1):
        url = WIKIDATA_API + "?" + urllib.parse.urlencode(
            {
                "action": "wbgetentities",
                "props": "labels|aliases",
                "languages": "es",
                "format": "json",
                "ids": "|".join(batch),
            }
        )
        for qid, ent in api_get(url).get("entities", {}).items():
            label = ent.get("labels", {}).get("es", {}).get("value")
            if not label:
                continue
            aliases = [a["value"] for a in ent.get("aliases", {}).get("es", [])]
            out[str(by_qid[qid])] = {"qid": qid, "label": label, "aliases": aliases}
        if i % 10 == 0 or i == len(batches):
            print(f"  {i}/{len(batches)} batches ({len(out)} with a Spanish label so far)")
        time.sleep(0.2)

    os.makedirs(RAW_DIR, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    with_aliases = sum(1 for v in out.values() if v["aliases"])
    print(f"DONE: {len(out)} labels ({with_aliases} with aliases) written to {OUT_FILE}")


if __name__ == "__main__":
    main()
