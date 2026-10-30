#!/usr/bin/env python3

import argparse
import subprocess
import re
import sys
import os

parser = argparse.ArgumentParser(description="Get times for different models",
                                 epilog="Example: bench.py")

parser.add_argument("--K",default="10",help="Maximum number of categories, or a range 'Kmin:Kmax' (default: 10 = 1:10)")
parser.add_argument("--threads",type=int,default=10,help="Max number of threads to consider")
parser.add_argument("--replicates",type=int,default=9,help="Number of replicates")
parser.add_argument("--output",type=str,default="timings.tsv",help="Name of output file")
parser.add_argument("--overwrite",action='store_true',help="Can we overwrite the output file")
parser.add_argument("--noaction",action='store_true',help="Don't run action version")
parser.add_argument("--noexp",action='store_true',help="Don't non-action version (without eigen)")
parser.add_argument("--noexpeigen",action='store_true',help="Don't run non-action version (with eigen)")
parser.add_argument("--verbose",action='store_true',help="Print debugging info")
parser.add_argument("--xml-dir",default="xmls/MarkovModulated",help="Directory holding the yeast_codon_hmc_K*.xml files")
args = parser.parse_args()

TIMER_UNITS = {"seconds": 1, "minutes": 60, "hours": 60*60, "days": 60*60*24}

def get_time(filename,threads,fastdecomp,fasteigmult):
    # NOTE: "beast" and "beast-slow" are the wrappers in docker/; both put EigenJNI on the library path.
    if fastdecomp:
        cmd = ["beast","-beagle_threads",str(threads),filename]
    else:
        cmd = ["beast-slow","-beagle_threads",str(threads),filename]
    if args.verbose:
        print(cmd,file=sys.stderr)

    # NOTE: the fast BEAGLE build uses Eigen to compute the transition probabilities from the
    #       eigensystem, and the slow build does not.  The wrappers load whichever $BEAGLE_LIB names.
    env = os.environ.copy()
    if fasteigmult:
        env["BEAGLE_LIB"] = env.get("BEAGLE_FAST_LIB", "/opt/beagle-fast/lib")
    else:
        env["BEAGLE_LIB"] = env.get("BEAGLE_SLOW_LIB", "/opt/beagle-slow/lib")

    p = subprocess.run(cmd, env=env, capture_output=True, text=True)
    out = p.stdout
    T = None
    for line in out.splitlines():
        m = re.fullmatch(r"([0-9.]+) (seconds|minutes|hours|days)", line)
        if m:
            T = float(m.group(1))*TIMER_UNITS[m.group(2)]
    if T is None:
        print(f"No time in output for command {cmd}!", file=sys.stderr)
        print(out, file=sys.stderr)
        print(p.stderr, file=sys.stderr)
        sys.exit(1)
    else:
        return T

def parse_K(K):
    ks = [int(k) for k in K.split(":")]
    if len(ks) == 1:
        return [1,ks[0]]
    elif len(ks) == 2:
        return ks
    else:
        print(f"Can't parse --K='{K}'", file=sys.stderr)
        sys.exit(1)

print(f"Writing to output file '{args.output}'", file=sys.stderr)

if os.path.exists(args.output) and not args.overwrite:
    print(f"Error: file '{args.output}' exists!  Add --overwrite to overwrite it.")
    sys.exit(1)


if args.output=="-":
    outfile=sys.stdout
else:
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    outfile = open(args.output,"w")
print(f"K\tmethod\tthreads\ttime", file=outfile)
Kmin,Kmax = parse_K(args.K)
for i in range(args.replicates):
    for threads in range(1,args.threads+1):
        for K in range(Kmin,Kmax+1):
            print(f"K={K} threads={threads} replicates={i+1}/{args.replicates}", file=sys.stderr)
            if not args.noexp:
                t_exp = get_time(os.path.join(args.xml_dir, f"yeast_codon_hmc_K{K}.xml"),threads,False, False)
                print(f"{K}\texp\t{threads}\t{t_exp}", file=outfile, flush=True)
            if not args.noexpeigen:
                t_exp = get_time(os.path.join(args.xml_dir, f"yeast_codon_hmc_K{K}.xml"),threads, True, True)
                print(f"{K}\texp-eigen\t{threads}\t{t_exp}", file=outfile, flush=True)
            if not args.noaction:
                t_action = get_time(os.path.join(args.xml_dir, f"action_yeast_codon_hmc_K{K}.xml"),threads, True, True)
                print(f"{K}\taction\t{threads}\t{t_action}",file=outfile, flush=True)
if outfile is not sys.stdout:
    outfile.close()
print("Finished!",file=sys.stderr)
