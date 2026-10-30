#!/usr/bin/env Rscript

library(ggplot2)
library(dplyr)
library(ggthemes)

# Figures go to $FIGURES_DIR (default: figures/).
out_dir <- Sys.getenv("FIGURES_DIR", "figures")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

args <- commandArgs(trailingOnly = TRUE)

# Edit these values to choose which K values to include.
selected_K <- c(1, 2, 4, 8, 16, 32)

# Common plot layout settings.
facet_nrow <- 1
plot_height <- 3
plot_width <- 9
method_colors <- c(
  action = "#D55E00",
  exp = "#999999",
  "exp-eigen" = "#0072B2"
)
method_labels <- c(
  action = "action",
  exp = "exp",
  "exp-eigen" = "exp/opt"
)

method_color_scale <- function(data) {
  breaks <- levels(droplevels(data$method))
  scale_color_manual(
    values = method_colors,
    breaks = breaks,
    labels = method_labels[breaks]
  )
}

input_files <- if (length(args) == 0) {
  "data/timings-length.tsv"
} else {
  args
}

timing_tables <- lapply(input_files, function(filename) {
  read.table(filename, header = TRUE)
})

# Optional sanity check: require all files to have exactly the same columns.
column_names <- lapply(timing_tables, names)

if (!all(vapply(column_names, identical, logical(1), column_names[[1]]))) {
  stop("Input files do not all have the same columns.")
}

# Read data from either data/timings-length.tsv, or a given list of file names.
timings <- bind_rows(timing_tables)


# Keep only selected K values, and make facet order follow selected_K.
timings <- timings |>
  filter(K %in% selected_K) |>
  mutate(
    K = factor(K, levels = selected_K),
    threads = factor(threads),
    method = factor(method, levels = c("action", "exp", "exp-eigen"))
  )

# Collapse replicates to median time and interquartile range.
summary_data <- timings |>
  group_by(K, method, threads, length) |>
  summarize(
      median_time = median(time),
    lower_time = quantile(time, 0.25),
    upper_time = quantile(time, 0.75),
    n = n(),
    .groups = "drop"
  )

base_time_plot <- function(data) {
  ggplot(
    data,
    aes(
      x = length,
      y = median_time,
      color = method,
      linetype = threads,
      group = interaction(method, threads)
    )
  ) +
    geom_line() +
    facet_wrap(
      ~ K,
      nrow = facet_nrow,
      scales = "free_y",
      axes = "all_x",
      labeller = labeller(K = function(x) paste0("M=", x))
    ) +
    labs(
#      title = "Median Time by Method and K",
      x = "Number of unique site patterns",
      y = "Median Time (seconds)",
      linetype = "Threads",
      color = "Method"
    ) +
    method_color_scale(data) +
    guides(
      color = guide_legend(order = 1),
      linetype = guide_legend(order = 2)
    ) +
    theme_tufte() +
    theme(
      axis.line = element_line(),
      strip.background = element_rect(fill = "gray91", color = NA)
    )
}

g <- base_time_plot(summary_data) +
  scale_x_continuous(
    expand = expansion(mult = c(0.01, 0.03)),
    breaks = c(1,1000,2000,3000),
    minor_breaks = c(500,1500,2500,3500),
    guide = guide_axis(minor.ticks = TRUE)
#    breaks = function(x) unique(floor(pretty(seq(min(x), max(x)))))
  ) +
  scale_y_continuous(
    expand = expansion(mult = c(0.01, 0.05))
  )


ggsave(file.path(out_dir, "timings-length.pdf"), g, height = plot_height, width = plot_width)

summary_data_log <- summary_data |>
  filter(length > 0, median_time > 0)

g2 <- base_time_plot(summary_data_log) +
  scale_x_log10(
    expand = expansion(mult = c(0.01, 0.03))
  ) +
  scale_y_log10(
    expand = expansion(mult = c(0.01, 0.05))
  )


if (Sys.getenv("LOG_PLOTS") != "") ggsave(file.path(out_dir, "timings-length-log.pdf"), g2, height = plot_height, width = plot_width)

# Baseline: method = exp-eigen, threads = 1, matched by K and length.
baseline_data <- summary_data |>
  filter(method == "exp-eigen", threads == "1") |>
  select(K, length, baseline_time = median_time)

ratio_data <- summary_data |>
  left_join(baseline_data, by = c("K", "length")) |>
  mutate(speedup = baseline_time / median_time) |>
  filter(!is.na(speedup), speedup > 0)

g3 <- ggplot(
  ratio_data,
  aes(
    x = length,
    y = speedup,
    color = method,
    linetype = threads,
    group = interaction(method, threads)
  )
) +
  geom_hline(yintercept = 1, linewidth = 0.3) +
  geom_line() +
  facet_wrap(
    ~ K,
    nrow = facet_nrow,
    axes = "all_x",
    labeller = labeller(K = function(x) paste0("M=", x))
  ) +
 scale_x_log10(
    breaks = c(1, 4, 16, 64, 256, 1024),
    labels = c("1", "4", "16", "64", "256", "1k"),
    minor_breaks = c(2, 8, 32, 128, 512, 2048),
    guide = guide_axis(minor.ticks = TRUE),
    expand = expansion(mult = c(0.01, 0.03))
  ) +
  scale_y_log10(
    expand = expansion(mult = c(0.01, 0.05)),
    guide = guide_axis(minor.ticks = TRUE)
  ) +
  labs(
#    title = "Speedup Relative to directly forming matrix exponential (1 thread, optimized kernel)",
    x = "Number of unique site patterns",
    y = "Speedup relative to baseline",
    linetype = "Threads",
    color = "Method"
  ) +
  method_color_scale(ratio_data) +
  guides(
    color = guide_legend(order = 1),
    linetype = guide_legend(order = 2)
  ) +
  theme_tufte() +
  theme(
    axis.line = element_line(),
    strip.background = element_rect(fill = "gray91", color = NA)
  )


ggsave(file.path(out_dir, "timings-length-speedup.pdf"), g3, height = plot_height, width = plot_width)
