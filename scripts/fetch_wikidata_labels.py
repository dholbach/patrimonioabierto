#!/usr/bin/env python3
"""Pulls each linked monument's Spanish label and aliases ("also known as")
from Wikidata.

Two things come out of it that the JCyL catalogue cannot give:

- the label is written the way people write the name (with its accents -
  JCyL ships names in capitals without them, "IGLESIA DE LA ASUNCION"), and
- the aliases are the other names the same monument goes by, which is what
  someone searching for it may type instead of the catalogue's name.

build_dataset.py takes the accents from the label (see names.py), and
build_monument_pages.py puts the aliases into each page's HTML and JSON-LD.

Runs as part of `make fetch`, after fetch_wikidata.py and before the build:
it reads the QIDs from that query's raw result, not from the built dataset,
so the build can use the labels of the same run.

Run: python3 scripts/fetch_wikidata_labels.py
Needs: data/raw/wikidata_p3177.json (scripts/fetch_wikidata.py)
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
P3177_FILE = os.path.join(RAW_DIR, "wikidata_p3177.json")
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
    rows = json.load(open(P3177_FILE, encoding="utf-8"))["results"]["bindings"]
    qids_by_jcyl = {}
    for row in rows:
        jcyl_id = row["jcylID"]["value"].strip()
        qids_by_jcyl.setdefault(jcyl_id, set()).add(row["item"]["value"].rsplit("/", 1)[-1])
    # Same exclusion as fetch_wikipedia_extracts.py: an id claimed by several
    # items is a conflict, with no single right item to take a label from.
    by_qid = {next(iter(qs)): jcyl_id for jcyl_id, qs in qids_by_jcyl.items() if len(qs) == 1}
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
