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
    "kroposki2017renewable": "10.1109/mpe.2016.2637122",
    "wang2018netload": "10.1109/tpwrs.2017.2762599",
    "kaur2016benefits": "10.1016/j.renene.2015.09.011",
    "ruggles2020eia": "10.1038/s41597-020-0483-x",
    "hong2016probabilistic": "10.1016/j.ijforecast.2015.11.011",
    "mann1947test": "10.1214/aoms/1177730491",
    # closest prior work (positioning), each checked against its Crossref record and abstract
    "mills2013value": "10.1109/jphotov.2013.2263984",
    "lave2016comparison": "10.1109/pvsc.2016.7749939",
    "shaker2016impacts": "10.1016/j.rser.2015.12.287",
    "huang2018ramp": "10.1109/pesgm.2018.8585852",
    "hou2019probabilistic": "10.1016/j.apenergy.2019.03.067",
    "millstein2021value": "10.1016/j.joule.2021.05.009",
    "ruggles2022peak": "10.1016/j.apenergy.2021.117773",
}
TITLE_FIX = {"California": "{C}alifornia", "Duck": "{D}uck", "PV": "{PV}", "100% Renewable": r"100\% Renewable",
             "׳": "'", "United States": "{U}nited {S}tates", "China": "{C}hina","THE USE OF CONFIDENCE OR FIDUCIAL LIMITS ILLUSTRATED IN THE CASE OF THE BINOMIAL": "The use of confidence or fiducial limits illustrated in the case of the binomial",
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
    bib = re.sub(r"pages=\{(\w+)–(\w+)\}", r"pages={\1--\2}", bib)
    for a, b in TITLE_FIX.items():
        bib = bib.replace(a, b)
    t = re.search(r"title=\{(.*?)\},", bib)
    print(f"{key:26s} {t.group(1)[:95] if t else '??'}")
    out.append(bib)
    time.sleep(0.5)
manual = open(os.path.join(os.path.dirname(__file__), "manual.bib"), encoding="utf-8").read()
open(sys.argv[1], "w", encoding="utf-8").write("\n\n".join(out) + "\n\n" + manual)
print(len(out) + manual.count("\n@") + manual.startswith("@"), "entries written")
