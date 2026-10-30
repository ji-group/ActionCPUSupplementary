#!/usr/bin/env Rscript

library(dplyr)

args <- commandArgs(trailingOnly = TRUE)

mm_file <- if (length(args) >= 1) args[1] else "data/timings-length.tsv"
igc_file <- if (length(args) >= 2) args[2] else "data/timings-length-IGC.tsv"
output_file <- if (length(args) >= 3) args[3] else "figures/timing-table.tex"

selected_K <- c(1, 8, 32)
selected_threads <- c(1, 10)
selected_lengths <- c(1, 64, 512)

format_percent <- function(x) {
  sprintf("%.2f\\%%", 100 * x)
}

# Format table entries with fixed decimal places and LaTeX thin-space thousands separators.
format_number <- function(x, digits) {
  formatC(x, format = "f", digits = digits, big.mark = "\\\\,")
}

summarize_timings <- function(data, group_columns) {
  data |>
    group_by(across(all_of(group_columns))) |>
    summarize(median_time = median(time), .groups = "drop")
}

make_mm_rows <- function(filename) {
  timings <- read.table(filename, header = TRUE)

  summary_data <- summarize_timings(
    timings,
    c("K", "method", "threads", "length")
  )

  baseline_data <- summary_data |>
    filter(method == "exp-eigen", threads == 1) |>
    select(K, length, baseline_time = median_time)

  full_length <- max(summary_data$length)

  table_lengths <- c(selected_lengths, full_length)

  rows <- expand.grid(
    K = selected_K,
    length = table_lengths,
    stringsAsFactors = FALSE
  )

  rows |>
    left_join(
      summary_data |>
        filter(method == "action", threads %in% selected_threads) |>
        left_join(baseline_data, by = c("K", "length")) |>
        mutate(speedup = baseline_time / median_time) |>
        select(K, length, threads, action_time = median_time, speedup),
      by = c("K", "length")
    ) |>
    mutate(
      model = paste0("MM, $\\numModules=", K, "$"),
      states = 61 * K,
      nonzero = 587 * K + K * (K - 1) * 61,
      density = nonzero / states^2
    ) |>
    select(model, states, nonzero, density, patterns = length, threads, action_time, speedup)
}

make_igc_rows <- function(filename) {
  timings <- read.table(filename, header = TRUE)

  summary_data <- summarize_timings(
    timings,
    c("method", "threads", "length")
  )

  baseline_data <- summary_data |>
    filter(method == "exp-eigen", threads == 1) |>
    select(length, baseline_time = median_time)

  full_length <- max(summary_data$length)

  table_lengths <- c(selected_lengths, full_length)

  rows <- data.frame(length = table_lengths)

  rows |>
    left_join(
      summary_data |>
        filter(method == "action", threads %in% selected_threads) |>
        left_join(baseline_data, by = "length") |>
        mutate(speedup = baseline_time / median_time) |>
        select(length, threads, action_time = median_time, speedup),
      by = "length"
    ) |>
    mutate(
      model = "IGC",
      states = 3721,
      nonzero = 74161,
      density = nonzero / states^2
    ) |>
    select(model, states, nonzero, density, patterns = length, threads, action_time, speedup)
}

wide_rows <- bind_rows(
  make_mm_rows(mm_file),
  make_igc_rows(igc_file)
) |>
  group_by(model, states, nonzero, density, patterns) |>
  mutate(thread_speedup = action_time[threads == 1] / action_time[threads == 10]) |>
  ungroup() |>
  mutate(
    speedup = format_number(speedup, 1),
    thread_speedup = format_number(thread_speedup, 2)
  ) |>
  select(-action_time) |>
  tidyr::pivot_wider(
    names_from = threads,
    values_from = speedup,
    names_prefix = "speedup_"
  ) |>
  arrange(
    ifelse(model == "IGC", 1, 0),
    states,
    patterns
  )

table_rows <- wide_rows |>
  mutate(
    states = format_number(states, 0),
    nonzero = format_number(nonzero, 0),
    patterns = format_number(patterns, 0),
    density = format_percent(density),
    line = sprintf(
      "\t%s & %s & %s & %s & %s & %s & %s & %s \\\\",
      model,
      states,
      nonzero,
      density,
      patterns,
      speedup_1,
      speedup_10,
      thread_speedup
    )
  ) |>
  pull(line)

latex_lines <- c(
  "\\begin{table}[H]",
  "\t\\centering",
  "\t\\setlength{\\tabcolsep}{4pt}",
  "\\begin{tabular}{lrrrrrrS[table-format=1.2]}",
  "\t\\toprule",
  "\tModel & $\\numStates$ & $\\#>0$ & density & patterns & \\multicolumn{2}{c}{Baseline speedup} & \\multicolumn{1}{c}{Thread speedup} \\\\",
  "\t\\cmidrule(lr){6-7}\\cmidrule(l){8-8}",
  "\t& & & & & \\multicolumn{1}{r}{1 Thr} & \\multicolumn{1}{r}{10 Thr} & \\multicolumn{1}{c}{10 vs 1 Thr} \\\\",
  "\t\\midrule",
  table_rows,
  "\t\\bottomrule",
  "\\end{tabular}",
  "",
  "\t\\caption{",
  "\tRepresentative speedups for action-based likelihood computation.",
  "\tSpeedups are computed as the time for optimized exponentiation with one thread divided by the time for the action-based method with the indicated number of threads, matched by model and number of site patterns.",
  "\tThe final column reports the action-based runtime with one thread divided by the action-based runtime with 10 threads; the ideal value is 10.",
  "\tAll rows are from the time-per-iteration length benchmarks.",
  "\t\\label{tab:times}",
  "}",
  "\\end{table}"
)

writeLines(latex_lines, output_file)
