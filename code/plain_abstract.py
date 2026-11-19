"""Plain-text title, abstract and keywords (macros expanded) for submission portals.
Run from the repository root: python -I code/plain_abstract.py"""
import json
import re

M = json.load(open("out/macros.json"))
t = open("paper/main.tex", encoding="utf-8").read()
title = re.search(r"\\title\{(.+?)\}\n", t).group(1)
a = t.split(r"\begin{abstract}", 1)[1].split(r"\end{abstract}", 1)[0]
kw = t.split(r"\begin{IEEEkeywords}", 1)[1].split(r"\end{IEEEkeywords}", 1)[0].strip()


def plain(s):
    s = re.sub(r"\\res\{([^}]+)\}", lambda m: M[m.group(1)], s)
    s = s.replace("$-$", "\u2212").replace("$<$", "<")
    s = re.sub(r"\$p([=<])", lambda m: "p " + m.group(1) + " ", s)
    s = s.replace("$", "").replace("--", "\u2013").replace(r"\%", "%").replace("~", " ")
    s = s.replace("{,}", ",")
    return re.sub(r"\s+", " ", s).strip()


a = plain(a)
title = plain(title)
open("paper/abstract_plain.txt", "w", encoding="utf-8").write(f"{title}\n\n{a}\n\nKeywords: {kw}\n")
print(len(a.split()), "words,", len(a), "chars")
print(title)
print(a)
print("KEYWORDS:", kw)
