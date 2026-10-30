#!/usr/bin/env python3
"""Compare generated Markov-modulated XMLs with the committed fixed-run XMLs.

Both sides are normalised before diffing: XML comments, blank lines,
leading/trailing whitespace and the alignment's sequence lines are dropped.
The resulting differences are printed as one block per file, so the output
can be compared with the documented list in data/xml-differences.txt.
"""

import argparse
import difflib
import os
import re
import sys

SEQUENCE_LINE = re.compile(r"[ACGTNRYKMSWBDHV?-]{20,}")


def normalise(path):
    with open(path) as f:
        text = f.read()
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    lines = []
    for line in text.splitlines():
        line = " ".join(line.split())
        if not line or SEQUENCE_LINE.fullmatch(line):
            continue
        lines.append(line)
    return lines


parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--committed", default="xmls/MarkovModulated", help="Directory with the committed XMLs")
parser.add_argument("--generated", default="xmls/MarkovModulated/generated", help="Directory with the generated XMLs")
args = parser.parse_args()

names = [f"{prefix}yeast_codon_hmc_K{K}.xml" for K in range(1, 11) for prefix in ("", "action_")]
for name in names:
    committed = normalise(os.path.join(args.committed, name))
    generated = normalise(os.path.join(args.generated, name))
    print(f"### {name}")
    for line in difflib.unified_diff(generated, committed, "generated", "committed", n=0, lineterm=""):
        if line.startswith(("---", "+++", "@@")):
            continue
        print(line)
