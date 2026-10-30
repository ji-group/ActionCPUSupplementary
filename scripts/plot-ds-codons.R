#!/usr/bin/env Rscript

library(tidyr)
library(ggplot2)
library('ggthemes')
library(dplyr)

# Figures go to $FIGURES_DIR (default: figures/).
out_dir <- Sys.getenv("FIGURES_DIR", "figures")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

df = read.table("data/ds.txt", header=TRUE)

# reshape to long format
df_long <- df %>%
  pivot_longer(
    cols = starts_with("d"),   # all columns d1..d9
    names_to = "d",
    values_to = "value"
  ) %>% 
  mutate(d_num = as.numeric(sub("d", "", d)))  # turn "d1".."d9" into numeric 1..9

# average over d<n> values given (nstates, shifted, and n)
df_avg <- df_long %>%
  group_by(nstates, shifted, d_num) %>%
  summarise(mean_value = mean(value), .groups = "drop")


g = ggplot(df_avg, aes(x = d_num, y = mean_value, color = shifted, group = shifted)) +
    geom_line() +
    geom_point() +
    facet_wrap(~ nstates, nrow=2) +
    scale_x_continuous(breaks = seq(1, 9)) +
    scale_y_continuous(breaks = 1:21, labels = function(x) ifelse(x %% 5 == 0, x, "") ) +
    geom_hline(yintercept = 1:21, color = "lightgray", linewidth = 0.3) +
    labs(# title = "Average d_p(A) value by number of states and p",
         x = expression(p),
         y = expression(d[p](A)),
         color = "Method")


g = g +
    theme_tufte() +
    theme(
        axis.line = element_line(),
        strip.background = element_rect(fill = "gray91", color = NA),
    )


ggsave(file.path(out_dir, "ds-codons.pdf"), g, height=5, width=8.5)
