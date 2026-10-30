#!/usr/bin/env python3
"""Emit a Markov-modulated codon XML from the template and a sequences file.

Uses generate_xml() from bench-lengths.py, so the XML is exactly what the
length benchmark runs.
"""

import argparse
import importlib.util
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("bench_lengths", os.path.join(here, "bench-lengths.py"))
bench_lengths = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench_lengths)

parser = argparse.ArgumentParser(description="Generate XML file for the yeast Markov-modulated codon model",
                                 epilog="Example: gen_mm_xml.py xmls/MarkovModulated/yeast_codon_hmc.xml.template "
                                        "xmls/MarkovModulated/yeast_sequences.xml -K 8 --action --chainlength 50 > K8.xml")

parser.add_argument("template", help="Template for XML (e.g. yeast_codon_hmc.xml.template)")
parser.add_argument("sequences", help="File containing sequences XML")
parser.add_argument("-K", type=int, required=True, help="Number of categories")
parser.add_argument("--action", action='store_true', help="Use the action likelihood (useAction=\"true\")")
parser.add_argument("--chainlength", type=int, default=50, help="MCMC chain length (default: 50)")
parser.add_argument("--length", type=int, help="Truncate/repeat the alignment to this many codons")
parser.add_argument("--compress", action='store_true',
                    help="--length counts distinct codon site patterns instead of codon columns")

args = parser.parse_args()

with open(args.template, 'r') as file:
    template = file.read()

with open(args.sequences, 'r') as file:
    sequences_raw = file.read()

sys.stdout.write(bench_lengths.generate_xml(template, sequences_raw, args.K, args.action,
                                            length=args.length, chainlength=args.chainlength,
                                            compress=args.compress))
