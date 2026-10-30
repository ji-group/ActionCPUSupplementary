#!/usr/bin/env python3

import argparse
import subprocess
import re
import sys
import os
import math
import tempfile
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------------------
#  XML generation helpers  (from gen_mm_xml.py)
# ---------------------------------------------------------------------------
def process_sequences(xml_content, length=None, use_patterns=False):
    """
    Parses the XML string, truncates/repeats sequences,
    and returns the modified XML as a string.

    If use_patterns is False (default), length is treated as a target
    number of codons (each codon = 3 nucleotides).

    If use_patterns is True, length is treated as a target number of
    distinct site patterns (unique alignment columns).
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        print(f"Error parsing sequences XML: {e}", file=sys.stderr)
        sys.exit(1)

    sequences = root.findall(".//sequence")

    # First pass: extract clean sequences and taxon elements
    taxa = []
    clean_seqs = []
    for seq_element in sequences:
        taxon = seq_element.find("taxon")
        raw_text = taxon.tail if taxon is not None and taxon.tail else seq_element.text
        if not raw_text:
            continue
        clean_seq = "".join(raw_text.split())
        taxa.append((seq_element, taxon))
        clean_seqs.append(clean_seq)

    if not clean_seqs:
        return ET.tostring(root, encoding="unicode")

    orig_len = len(clean_seqs[0])

    if length is None:
        target_L = orig_len
    elif use_patterns:
        target_L = _sites_for_n_patterns(clean_seqs, length, orig_len)
#        print(f"want {target_L/3} codons for {length} compressed sites", file=sys.stderr)
    else:
        target_L = length * 3

    # Second pass: truncate or repeat each sequence to target_L
    for clean_seq, (seq_element, taxon) in zip(clean_seqs, taxa):
        seq_len = len(clean_seq)
        if target_L <= seq_len:
            new_seq = clean_seq[:target_L]
        else:
            repeats = math.ceil(target_L / seq_len)
            new_seq = (clean_seq * repeats)[:target_L]

        if taxon is not None:
            taxon.tail = f"\n{new_seq}\n"
        else:
            seq_element.text = f"\n{new_seq}\n"

    return ET.tostring(root, encoding="unicode")

def _sites_for_n_patterns(clean_seqs, target_patterns, orig_len):
    """
    Walk through alignment columns in codon steps (3 nucleotides at a time),
    tracking distinct site patterns. Return the number of nucleotide positions
    needed to reach target_patterns distinct codon patterns.
    """
    seen_patterns = set()
    for i in range(0, orig_len, 3):
        column = tuple(seq[i:i+3] for seq in clean_seqs)
        seen_patterns.add(column)
        if len(seen_patterns) >= target_patterns:
            return i + 3  # number of nucleotide positions consumed

    print(
        f"Warning: only {len(seen_patterns)} distinct codon patterns found "
        f"in {orig_len // 3} codons (requested {target_patterns}).",
        file=sys.stderr,
    )
    return orig_len

def generate_xml(template, sequences_raw, action,
                 length=None, chainlength=5, compress=True):
    """
    Produce the final XML string that would previously have been written
    to disk by gen_mm_xml.py.
    """
    # Optionally adjust sequence lengths
    if length is not None:
#        print(f"generating sequences: action={action}  length={length}",file=sys.stderr)
        sequences = process_sequences(sequences_raw, length=length, use_patterns=compress)
    else:
        sequences = sequences_raw

    useAction = "true" if action else "false"

    output = template.format(
        sequences=sequences,
        useAction=useAction,
        chainlength=chainlength,
        screenlog=math.ceil(chainlength/10),
        filelog=math.ceil(chainlength/50),
    )

#    print(output,file=sys.stderr)

    return output


# ---------------------------------------------------------------------------
#  Benchmarking helpers
# ---------------------------------------------------------------------------

def run_beast(xml_string, threads, fastdecomp, fasteigmult,
              pattern_compression=True, verbose=False, attempts=3):
    """
    Write *xml_string* to a temp file, run beast on it, and return the
    elapsed time in seconds.  Gives up after *attempts* runs without a
    timer line.
    """
    # NOTE: "beast" and "beast-slow" are the wrappers in docker/; both put
    #       EigenJNI on the library path.
    beast_cmd = "beast" if fastdecomp else "beast-slow"

    # NOTE: the fast BEAGLE build uses Eigen for the dense matrix multiply,
    #       the slow build does not.  The wrappers load whichever $BEAGLE_LIB names.
    env = os.environ.copy()
    if fasteigmult:
        env["BEAGLE_LIB"] = env.get("BEAGLE_FAST_LIB", "/opt/beagle-fast/lib")
    else:
        env["BEAGLE_LIB"] = env.get("BEAGLE_SLOW_LIB", "/opt/beagle-slow/lib")

    tmp_path="tmp.xml"
    with open(tmp_path,"w") as file:
        file.write(xml_string)

    for attempt in range(attempts):
        cmd = [beast_cmd, "-overwrite", "-beagle_threads", str(threads)]
        if not pattern_compression:
            cmd += ["-pattern_compression", "off"]
        cmd.append(tmp_path)
        if verbose:
            print(cmd, file=sys.stderr)

        p = subprocess.run(cmd, env=env, capture_output=True, text=True)
        T = parse_timer(p.stdout)

        if T is not None:
            return T
        print(f"No time in output for cmd={cmd} "
              f"(attempt {attempt+1}/{attempts})", file=sys.stderr)
        print(p.stdout, file=sys.stderr)
        print(p.stderr, file=sys.stderr)

    sys.exit(1)


TIMER_UNITS = {"seconds": 1, "minutes": 60, "hours": 60 * 60, "days": 60 * 60 * 24}

def parse_timer(out):
    """Return the last "N seconds|minutes|hours|days" line of BEAST output, in seconds."""
    T = None
    for line in out.splitlines():
        m = re.fullmatch(r"([0-9.]+) (seconds|minutes|hours|days)", line)
        if m:
            T = float(m.group(1)) * TIMER_UNITS[m.group(2)]
    return T


def get_time(template, sequences_raw, action, length,
             threads, fastdecomp, fasteigmult,
             pattern_compression=True, verbose=False,
             min_time=5.0):
    """
    Generate XML and run beast, automatically increasing chainlength
    until the total runtime is at least *min_time* seconds.
    Returns the time per iteration.
    """
    chainlength = 5
    while True:
        xml_string = generate_xml(template, sequences_raw, action,
                                  length=length, chainlength=chainlength, compress=pattern_compression)
        T = run_beast(xml_string, threads, fastdecomp, fasteigmult,
                      pattern_compression, verbose)

        if T >= min_time:
            per_iter = T / chainlength
            if verbose:
                print(f"  chainlength={chainlength}  total={T:.3f}s  "
                      f"per_iter={per_iter:.4f}s", file=sys.stderr)
            return per_iter

        # Estimate chainlength needed for min_time, with a safety margin
        if T > 0:
            chainlength = max(chainlength * 2,
                              int(math.ceil(min_time / T * chainlength * 1.2)))
        else:
            chainlength *= 10

        if verbose:
            print(f"  runtime {T:.3f}s < {min_time}s, retrying with "
                  f"chainlength={chainlength}", file=sys.stderr)


def parse_list(spec):
    """
    Parse a thread specification like '1,3-5,10' into a sorted list
    of unique integers: [1, 3, 4, 5, 10].
    """
    result = set()
    for part in spec.split(","):
        part = part.strip()
        m = re.fullmatch(r"(\d+)-(\d+)", part)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            result.update(range(lo, hi + 1))
        else:
            result.add(int(part))
    return sorted(result)


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Benchmark beast with on-the-fly XML generation",
        epilog="Example: bench-lengths-IGC.py --threads 1,10 --length 1,2,4,8,16,32,64,128",
    )

    # Inputs for XML generation
    parser.add_argument("template",
                        help="Template for XML (e.g. MG94_example.xml.template)", nargs='?', default="xmls/IGC/MG94_example.xml.template")
    parser.add_argument("sequences",
                        help="File containing sequences XML", nargs='?', default="xmls/IGC/MG94_sequences.xml")

    # Benchmark parameters
    parser.add_argument("--threads", type=str, default="1-10",
                        help="Thread counts, e.g. '1,3-5,10' (default: 1-10)")
    parser.add_argument("--replicates", type=int, default=9,
                        help="Number of replicates")
    parser.add_argument("--output", type=str, default="timings-length-IGC.tsv",
                        help="Name of output file (use '-' for stdout)")
    parser.add_argument("--overwrite", action="store_true",
                        help="Allow overwriting the output file")
    parser.add_argument("--noaction", action="store_true",
                        help="Don't run action version")
    parser.add_argument("--noexp", action="store_true",
                        help="Don't run non-action version (without eigen)")
    parser.add_argument("--noexpeigen", action="store_true",
                        help="Don't run non-action version (with eigen)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print debugging info")
    parser.add_argument("--compress", action="store_true",
                        help="--length counts distinct codon site patterns and "
                             "BEAST pattern compression stays on (default: "
                             "--length counts codon columns, compression off)")

    # Sequence manipulation (passed through to generate_xml)
    parser.add_argument("--length", type=str,
                        help="Comma-separated list of codon counts "
                             "(each is multiplied by 3 to get character length), "
                             "e.g. --length=1,4,16,64,256,1024,4096")

    args = parser.parse_args()

    # --- Parse --length into list of character lengths (codon count × 3) ---
    if args.length is not None:
        lengths = [int(x) for x in args.length.split(",")]
    else:
        lengths = [None]  # single entry meaning "use original / fraction"

    # --- Load template and sequences once ---
    with open(args.template, "r") as f:
        template = f.read()
    with open(args.sequences, "r") as f:
        sequences_raw = f.read()

    # --- Open output ---
    if os.path.exists(args.output) and not args.overwrite:
        print(f"Error: file '{args.output}' exists!  "
              "Add --overwrite to overwrite it.")
        sys.exit(1)

    print(f"Writing to output file '{args.output}'", file=sys.stderr)

    if args.output == "-":
        outfile = sys.stdout
    else:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        outfile = open(args.output, "w")

    print("method\tthreads\tlength\ttime", file=outfile)

    thread_list = parse_list(args.threads)
    compressed = args.compress

    # --- Run benchmarks ---
    for i in range(args.replicates):
        for threads in thread_list:
            for L in lengths:
                L_label = L if L is not None else "all"
                print(f"threads={threads}  length={L_label}  "
                      f"replicate={i+1}/{args.replicates}",
                      file=sys.stderr)

                if not args.noexp:
                    t = get_time(template, sequences_raw, False, L,
                                 threads, False, False,
                                 compressed, args.verbose, 5.0)
                    print(f"exp\t{threads}\t{L_label}\t{t}",
                          file=outfile, flush=True)

                if not args.noexpeigen:
                    t = get_time(template, sequences_raw, False, L,
                                 threads, True, True,
                                 compressed, args.verbose)
                    print(f"exp-eigen\t{threads}\t{L_label}\t{t}",
                          file=outfile, flush=True)

                if not args.noaction:
                    t = get_time(template, sequences_raw, True, L,
                                 threads, True, True,
                                 compressed, args.verbose)
                    print(f"action\t{threads}\t{L_label}\t{t}",
                          file=outfile, flush=True)

    if outfile is not sys.stdout:
        outfile.close()
    print("Finished!", file=sys.stderr)


if __name__ == "__main__":
    main()
