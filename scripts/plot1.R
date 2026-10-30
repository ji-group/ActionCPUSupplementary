#!/usr/bin/env Rscript
library(ggplot2)
library(dplyr)
library('ggthemes')
library(tidyr)
library(stringr)

# Figures go to $FIGURES_DIR (default: figures/).
out_dir <- Sys.getenv("FIGURES_DIR", "figures")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

timings = read.table("data/timings.tsv",header=T)

# Drop K=9 to better fit into 2 rows.
# timings = timings[timings$K<9,]

# Collapse to median time
summary_data <- timings |>
  group_by(K, method, threads) |>
    summarize(median_time = median(time),
              lower_time = quantile(time, 0.25),
              upper_time = quantile(time, 0.75),
              .groups = "drop")


g = ggplot(summary_data, aes(x = threads, y = median_time, fill = method, color = method, shape=method)) +
    geom_line() +
    geom_point() +
    geom_ribbon(aes(ymin = lower_time, ymax = upper_time), alpha = 0.2, color = NA) +
    facet_wrap(~ K, nrow=2, scales = "free", labeller = labeller(K = function(x) paste0("M=", x))) +
    scale_x_continuous(breaks = function(x) unique(floor(pretty(seq(min(x), (max(x) + 1) * 1.1))))) +
    scale_y_continuous(expand=c(0,0)) +
    coord_cartesian(ylim=c(0,NA)) +
    labs(title = "Median Time by Method and M",
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


ggsave(file.path(out_dir, "timings.pdf"), g, height=5, width=8.5)

T1data = summary_data[summary_data$threads==1,]


g2 = ggplot(summary_data, aes(x = K, y = median_time, fill = method, color = method, shape=method)) +
     geom_line() +
     geom_point() +
     geom_ribbon(aes(ymin = lower_time, ymax = upper_time), alpha = 0.2, color = NA) +
     facet_wrap(~ threads, nrow=2, scales = "free",labeller = labeller(threads = function(x) paste0("threads=", x))) +
     scale_x_continuous(breaks = function(x) unique(floor(pretty(seq(min(x), (max(x) + 1) * 1.1))))) +
     scale_y_continuous(expand=c(0,0)) +
     coord_cartesian(ylim = c(0, 175)) +
     labs(title = "Median Time by Method and Threads",
          x = "M",
          y = "Median Time (seconds)",
          fill = "Method",
          shape= "Method",
          color = "Method")

g2 = g2 +
     theme_tufte() +
     theme(
         axis.line = element_line(),
         strip.background = element_rect(fill = "gray91", color = NA),
     )


ggsave(file.path(out_dir, "timings2.pdf"), g2, height=5, width=10.5)
