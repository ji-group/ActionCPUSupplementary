#!/usr/bin/env python3

import argparse
import subprocess
import re
import sys
import os

parser = argparse.ArgumentParser(description="Get times for the IGC model with and without the action likelihood",
                                 epilog="Example: bench-IGC.py --noexpeigen --output results/timings-IGC.tsv")

parser.add_argument("--threads",type=int,default=10,help="Max number of threads to consider")
parser.add_argument("--replicates",type=int,default=9,help="Number of replicates")
parser.add_argument("--output",type=str,default="timings-IGC.tsv",help="Name of output file")
parser.add_argument("--overwrite",action='store_true',help="Can we overwrite the output file")
parser.add_argument("--noaction",action='store_true',help="Don't run action version")
parser.add_argument("--noexpeigen","--noexp",dest="noexpeigen",action='store_true',
                    help="Don't run non-action version (fast BEAGLE + EigenJNI; 16-30 h per run)")
parser.add_argument("--verbose",action='store_true',help="Print debugging info")
parser.add_argument("--xml-dir",default="xmls/IGC",help="Directory holding MG94_action.xml and MG94_exp.xml")
args = parser.parse_args()

TIMER_UNITS = {"seconds": 1, "minutes": 60, "hours": 60*60, "days": 60*60*24}

def get_time(filename,threads):
    # NOTE: the non-action run uses the same fast stack as the action run, so its rows are labelled
    #       "exp-eigen".  "beast" loads the BEAGLE build named by $BEAGLE_LIB.
    cmd = ["beast","-overwrite","-beagle_threads",str(threads),filename]
    if args.verbose:
        print(cmd,file=sys.stderr)
    env = os.environ.copy()
    env["BEAGLE_LIB"] = env.get("BEAGLE_FAST_LIB", "/opt/beagle-fast/lib")
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

print(f"Writing to output file '{args.output}'", file=sys.stderr)

if os.path.exists(args.output) and not args.overwrite:
    print(f"Error: file '{args.output}' exists!  Add --overwrite to overwrite it.")
    sys.exit(1)

if args.output=="-":
    outfile=sys.stdout
else:
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    outfile = open(args.output,"w")
print(f"method\tthreads\ttime", file=outfile)
for i in range(args.replicates):
    for threads in range(1,args.threads+1):
        print(f"threads={threads} replicates={i+1}/{args.replicates}", file=sys.stderr)
        if not args.noexpeigen:
            t_exp = get_time(os.path.join(args.xml_dir, "MG94_exp.xml"),threads)
            print(f"exp-eigen\t{threads}\t{t_exp}", file=outfile, flush=True)
        if not args.noaction:
            t_action = get_time(os.path.join(args.xml_dir, "MG94_action.xml"),threads)
            print(f"action\t{threads}\t{t_action}",file=outfile, flush=True)
if outfile is not sys.stdout:
    outfile.close()
print("Finished!",file=sys.stderr)
