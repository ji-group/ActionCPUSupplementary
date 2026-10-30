#!/usr/bin/env Rscript

library(ggplot2)
library('ggthemes')

# Figures go to $FIGURES_DIR (default: figures/).
out_dir <- Sys.getenv("FIGURES_DIR", "figures")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

Shifted = read.table("data/MG94-ds-shifted.txt")
Shifted = Shifted[,-c(1,2)]
dsShifted = as.numeric(colMeans(Shifted))

Unshifted = read.table("data/MG94-ds-unshifted.txt")
Unshifted = Unshifted[,-c(1,2)]
dsUnshifted = as.numeric(colMeans(Unshifted))


x <- 1:9

df <- data.frame(
    index = x,
    shifted = dsShifted,
    unshifted = dsUnshifted
)

g = ggplot(df, aes(x = index)) +
    geom_line(aes(y = shifted, color = "shifted")) +
    geom_line(aes(y = unshifted, color = "unshifted")) +
    geom_point(aes(y = shifted, color = "shifted")) +
    geom_point(aes(y = unshifted, color = "unshifted")) +
    labs(x = "Matrix power", y = expression(d[p](A)), color = "Method") +
    scale_x_continuous(breaks = seq(1, 9)) +
    scale_y_continuous(expand=c(0,0),limits=c(0,NA))

g = g +
    theme_tufte() +
    theme(
        axis.line = element_line(),
        strip.background = element_rect(fill = "gray91", color = NA),
    )


ggsave(file.path(out_dir, "ds-IGC.pdf"), g, height=5, width=8.5)
