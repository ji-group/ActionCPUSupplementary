#!/usr/bin/env python3
"""Emit an IGC (MG94 + gene conversion) XML from the template and a sequences file.

Uses generate_xml() from bench-lengths-IGC.py, so the XML is exactly what the
IGC length benchmark runs.
"""

import argparse
import importlib.util
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("bench_lengths_igc", os.path.join(here, "bench-lengths-IGC.py"))
bench_lengths_igc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench_lengths_igc)

parser = argparse.ArgumentParser(description="Generate XML file for the IGC data set",
                                 epilog="Example: gen_igc_xml.py xmls/IGC/MG94_example.xml.template "
                                        "xmls/IGC/MG94_sequences.xml --length 1 --chainlength 1 --action > igc_action.xml")

parser.add_argument("template", help="Template for XML (e.g. MG94_example.xml.template)")
parser.add_argument("sequences", help="File containing sequences XML")
parser.add_argument("--action", action='store_true', help="Use the action likelihood (useAction=\"true\")")
parser.add_argument("--chainlength", type=int, default=5, help="MCMC chain length (default: 5)")
parser.add_argument("--length", type=int, help="Truncate/repeat the alignment to this many codons")
parser.add_argument("--compress", action='store_true',
                    help="--length counts distinct codon site patterns instead of codon columns")

args = parser.parse_args()

with open(args.template, 'r') as file:
    template = file.read()

with open(args.sequences, 'r') as file:
    sequences_raw = file.read()

sys.stdout.write(bench_lengths_igc.generate_xml(template, sequences_raw, args.action,
                                                length=args.length, chainlength=args.chainlength,
                                                compress=args.compress))
