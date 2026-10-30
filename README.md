# BEAGLE in Action: supplementary material

Data, BEAST XML files, benchmark drivers, plotting scripts and a Docker image definition for

> Redelings BD, Wright A, Gangavarapu K, Shao Y, Monti F, Deng W-M, Su S, Rambaut A, Baele G, Lemey P,
> Suchard MA, Ji X. *BEAGLE in Action: Phylogenetic Likelihoods for Very Large State Spaces.*
> (preprint link to be added)

The paper adds an action-based likelihood to BEAGLE: instead of forming the matrix exponential
exp(Qt) and multiplying it into the partial likelihoods, BEAGLE computes the action exp(Qt)·v directly,
which pays off for large, sparse rate matrices. This repository contains everything needed to rerun
the two sets of benchmarks in the paper, a Markov-modulated codon model on a six-taxon yeast alignment
(61·M states, M = 1..32) and an interlocus gene conversion (IGC) codon model on a pair of yeast paralogs
(3 721 states). The plot scripts that drew the figures and Table 1 from the committed timings are
included for reference.

```
docker/      Dockerfile (pinned BEAST, two BEAGLE builds, EigenJNI, Python) and the beast / beast-slow wrappers
xmls/        MarkovModulated/ (template, sequences, 20 fixed-run XMLs) and IGC/ (template, sequences, 2 XMLs)
scripts/     benchmark drivers, XML generators, plot scripts, env.sh
```


## Setup

Two BEAGLE builds are needed, because the `exp` and `exp-eigen` methods differ only in BEAGLE's dense
matrix multiply:

* `beast` runs BEAST with the **fast** BEAGLE build (`faster-mat-mult2`: action kernel + Eigen dense
  multiply), used for `exp-eigen` and `action`;
* `beast-slow` runs the same BEAST with the **slow** BEAGLE build (`df15374a`: hand-written dense
  multiply), used for `exp`.

Both wrappers put EigenJNI on the library path, load the BEAGLE build named by `$BEAGLE_LIB` (default:
their own build) and print `BEAGLE_LIB=…` to stderr, so every log records which build ran.

### Docker image

From the repository checkout:

```bash
docker build --platform linux/amd64 -t beast-action docker
```

(or `--platform linux/arm64`; the `docker/` folder is the build context; 20–40 minutes), then

```bash
docker run --mount type=bind,src="$(pwd)",target=/tmp -it beast-action bash
```

Inside the container the checkout is `/tmp`, `beast` and `beast-slow` are on `PATH`, and Python has
everything the benchmark drivers need. The image does not include R (see "Figures and table").
A prebuilt image can be found at
`beast1/beast-action:x86_64` and `:arm_64`.

### Global installation (Linux)

Requirements: a C++17 compiler, CMake ≥ 3.23, a JDK (11–21) with `ant`, Eigen 3.4, git and Python ≥ 3.9
(standard library only).
Build the four components at the commits listed under "Software versions", following
`docker/Dockerfile`:

1. EigenJNI into e.g. `/opt/eigenjni` (`cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=…`).
2. BEAGLE `c2b9e060` into `/opt/beagle-fast` and BEAGLE `df15374a` into `/opt/beagle-slow`, both with
   `-DBUILD_CUDA=OFF -DBUILD_OPENCL=OFF -DCMAKE_INSTALL_LIBDIR=lib`; pass `-DCMAKE_CXX_FLAGS=-DNDEBUG` to
   the slow build so both are compiled the same way. To reproduce the paper's builds keep BEAGLE's
   default `-march=native`.
3. BEAST `action_likelihood` with `ant dist` (jar at `build/dist/beast.jar`).
4. Edit the paths in `scripts/env.sh`, `source scripts/env.sh`, and install the wrappers:
   `install -m 755 docker/beast docker/beast-slow /usr/local/bin/`.

On macOS the `LD_LIBRARY_PATH` mechanism of the wrappers does not apply; run BEAST directly with both
library directories on `java.library.path`:

```bash
java -Djava.library.path=/opt/beagle-fast/lib:/opt/eigenjni/lib -cp beast.jar dr.app.beast.BeastMain -beagle_threads 1 xmls/IGC/MG94_action.xml
```

## Reproducing the analyses

All commands run from the repository root (`/tmp` inside the container) with `beast` and `beast-slow`
on `PATH`. `data/` holds the authors' runs; the drivers refuse to overwrite an existing output file, so
reruns go to `results/`. Every driver writes its scratch XML to `tmp.xml` in the current directory, so
run one driver per directory at a time.

### Markov-modulated length benchmark (Figs 3–4, Table 1)

`data/timings-length.tsv` is the union of two grids, so reproducing it takes two invocations (days of
run time):

```bash
python3 scripts/bench-lengths.py xmls/MarkovModulated/yeast_codon_hmc.xml.template xmls/MarkovModulated/yeast_sequences.xml --K 1,2,4,8,16,32 --threads 1,10 --length 1,2,4,8,16,32,64,128,256,512,1024,1536,2048,2560,3052 --compress --noexp --replicates 9 --output results/timings-length.tsv
```

```bash
python3 scripts/bench-lengths.py xmls/MarkovModulated/yeast_codon_hmc.xml.template xmls/MarkovModulated/yeast_sequences.xml --K 1-10,16,32 --threads 1,10 --length 1,2,4,8,16,32,64,128,256,512,1024,1536,2048,2560,3052 --compress --noaction --noexpeigen --replicates 9 --output results/timings-length-exp.tsv
```

```bash
tail -n +2 results/timings-length-exp.tsv >> results/timings-length.tsv
```

Quick variant: the first command with `--replicates 3` reproduces the shape of the figures without the
grey `exp` series.

### IGC length benchmark (Fig 5, Table 1)

```bash
python3 scripts/bench-lengths-IGC.py xmls/IGC/MG94_example.xml.template xmls/IGC/MG94_sequences.xml --threads 1,10 --length 1,2,4,8,16,32,64,128,256,512,1024,2048,4096 --noexp --replicates 3 --output results/timings-length-IGC.tsv
```

### Fixed-run benchmarks (Figs S1–S3)

```bash
python3 scripts/bench.py --K 10 --threads 10 --replicates 1 --output results/timings.tsv
```

`bench.py` takes a maximum K and a maximum thread count, not lists. The committed
`xmls/MarkovModulated/yeast_codon_hmc_K10.xml` is a 1-iteration chain, so its K=10 `exp`/`exp-eigen`
rows will not match `data/timings.tsv` or Figs S1–S2 (see `data/README.md`).

```bash
python3 scripts/bench-IGC.py --noexp --output results/timings-IGC.tsv
```

This is the command behind the committed action-only `data/timings-IGC.tsv`. Without `--noexp` the
driver also runs `MG94_exp.xml` (fast BEAGLE + EigenJNI, rows labelled `exp-eigen`), which takes 16–30 h
per run on the Ryzen.

### Single analyses by hand

```bash
beast -overwrite -seed 666 -beagle_threads 10 xmls/MarkovModulated/action_yeast_codon_hmc_K8.xml
```

```bash
beast-slow -overwrite -seed 666 -beagle_threads 1 xmls/MarkovModulated/yeast_codon_hmc_K8.xml
```

```bash
beast -overwrite -seed 666 -beagle_threads 10 xmls/IGC/MG94_action.xml
```

To make XMLs for other settings:

```bash
python3 scripts/gen_mm_xml.py xmls/MarkovModulated/yeast_codon_hmc.xml.template xmls/MarkovModulated/yeast_sequences.xml -K 8 --action --chainlength 50 > K8_action.xml
```

```bash
python3 scripts/gen_igc_xml.py xmls/IGC/MG94_example.xml.template xmls/IGC/MG94_sequences.xml --length 1 --chainlength 1 --action > igc_action.xml
```

### d_p estimates (Figs 1–2)

Procedure to be supplied.

### Figures and table

`figures/` holds the figures and Table 1 as they appear in the paper. Redrawing them is optional and
needs R ≥ 4.1 with ggplot2 ≥ 3.5.0, dplyr ≥ 1.1, tidyr ≥ 1.3, ggthemes and stringr (not in the Docker
image):

```bash
make figures table
```

runs

```
Rscript scripts/plot-length.R data/timings-length.tsv
Rscript scripts/plot-length-IGC.R data/timings-length-IGC.tsv
Rscript scripts/plot-ds-IGC.R
Rscript scripts/plot-ds-codons.R
Rscript scripts/plot1.R
Rscript scripts/plot-IGC.R
Rscript scripts/make-speedup-table.R data/timings-length.tsv data/timings-length-IGC.tsv figures/timing-table.tex
```

and writes the 9 PDFs and `timing-table.tex` into `figures/` (set `FIGURES_DIR` to write elsewhere,
`LOG_PLOTS=1` for the two unused log-scale variants). Reruns in `results/` can be passed to the two
`plot-length*.R` scripts directly. `make check` parses every script, validates every XML, compares the
regenerated fixed-run XMLs with the committed ones and checks that the table regenerates
byte-identically.

## Software versions

| Component | Repository, branch | Commit |
|---|---|---|
| BEAST X | [beast-dev/beast-mcmc](https://github.com/beast-dev/beast-mcmc) `action_likelihood` | `e6398f670d3b6f96f7e80a314c596b3d55a3c087` |
| BEAGLE fast | [ji-group/beagle-lib](https://github.com/ji-group/beagle-lib) `faster-mat-mult2` | `c2b9e060965261712230ccdd2950149410e25f4e` |
| BEAGLE slow | [ji-group/beagle-lib](https://github.com/ji-group/beagle-lib) `action-dev` | `df15374a017f4639645c0ebdbede506e47352be8` |
| EigenJNI | [ji-group/EigenJNI](https://github.com/ji-group/EigenJNI) `main` | `dfcdbd46114a590d438b49ae059d811647fd1001` |

Both BEAGLE builds report themselves as BEAGLE 4.0.2. The action branches keep moving; use the commits,
not the branch names.

