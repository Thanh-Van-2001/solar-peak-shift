"""Build refs.bib from Crossref BibTeX for DOIs (fails loudly if a DOI does not resolve)
and print each title for a by-eye check. Manual entries live in refs/manual.bib.
Run: python build_bib.py <out.bib>"""
import os
import re
import sys
import time
import urllib.error
import urllib.request

UA = {"User-Agent": "ref-check/0.1 (academic reference verification)"}
DOIS = {
    "denholm2015duck": "10.2172/1226167",
    "kroposki2017renewable": "10.1109/mpe.2016.2637122",
    "wang2018netload": "10.1109/tpwrs.2017.2762599",
    "kaur2016benefits": "10.1016/j.renene.2015.09.011",
    "ruggles2020eia": "10.1038/s41597-020-0483-x",
    "hong2016probabilistic": "10.1016/j.ijforecast.2015.11.011",
    "mann1947test": "10.1214/aoms/1177730491",
}
TITLE_FIX = {"California": "{C}alifornia", "Duck": "{D}uck", "PV": "{PV}", "100% Renewable": r"100\% Renewable","THE USE OF CONFIDENCE OR FIDUCIAL LIMITS ILLUSTRATED IN THE CASE OF THE BINOMIAL": "The use of confidence or fiducial limits illustrated in the case of the binomial",
             "THE TREATMENT OF TIES IN RANKING PROBLEMS": "The treatment of ties in ranking problems"}


def get(url, tries=5):
    for t in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code != 429 or t == tries - 1:
                raise
            time.sleep(20 * (t + 1))
        except urllib.error.URLError:
            if t == tries - 1:
                raise
            time.sleep(5 * (t + 1))


out = []
for key, doi in DOIS.items():
    bib = get(f"https://api.crossref.org/works/{doi}/transform/application/x-bibtex")
    bib = re.sub(r"^@(\w+)\{[^,]+,", lambda m: "@" + m.group(1) + "{" + key + ",", bib.strip(), count=1)
    bib = re.sub(r"\s*url=\{[^}]*\},", "", bib)
    bib = re.sub(r",\s*month=\w+", "", bib)
    bib = bib.replace("&amp;", r"\&")
    for a, b in TITLE_FIX.items():
        bib = bib.replace(a, b)
    t = re.search(r"title=\{(.*?)\},", bib)
    print(f"{key:26s} {t.group(1)[:95] if t else '??'}")
    out.append(bib)
    time.sleep(0.5)
manual = open(os.path.join(os.path.dirname(__file__), "manual.bib"), encoding="utf-8").read()
open(sys.argv[1], "w", encoding="utf-8").write("\n\n".join(out) + "\n\n" + manual)
print(len(out) + manual.count("\n@") + manual.startswith("@"), "entries written")
