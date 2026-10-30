#!/usr/bin/env Rscript
library(ggplot2)
library(dplyr)
library('ggthemes')

# Figures go to $FIGURES_DIR (default: figures/).
out_dir <- Sys.getenv("FIGURES_DIR", "figures")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

timings = read.table("data/timings-IGC.tsv",header=T)

# Collapse to median time
summary_data <- timings |>
  group_by(method, threads) |>
    summarize(median_time = median(time),
              lower_time = quantile(time, 0.25),
              upper_time = quantile(time, 0.75),
              .groups = "drop")

g = ggplot(summary_data, aes(x = threads, y = median_time, fill = method, color = method, shape=method)) +
    geom_line() +
    geom_point() +
    geom_ribbon(aes(ymin = lower_time, ymax = upper_time), alpha = 0.2, color = NA) +
    scale_x_continuous(breaks = function(x) unique(floor(pretty(seq(min(x), (max(x) + 1) * 1.1))))) +
    scale_y_continuous(limits = ~ c(0, max(.x) + 0.1), expand=c(0,0)) +
    labs(title = "Median Time by Method",
         x = "Number of Threads",
         y = "Median Time (seconds)",
         fill = "Method",
         shape= "Method",
         color = "Method")

g = g +
    theme_tufte() +
    theme(
        axis.line = element_line(),
        strip.background = element_rect(fill = "gray91", color = NA),
    )


ggsave(file.path(out_dir, "timings-IGC.pdf"), g, height=5, width=8.5)

