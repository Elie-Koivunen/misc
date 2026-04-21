#!/usr/bin/env python3
"""
File Size Distribution Chart Generator
=======================================

Reads a file containing the output of the `ll` (a.k.a. `ls -l`) shell command
and renders an ASCII table / bar-chart summarising how many files fall into
each size bucket (1-4 KB, 5-16 KB, ... up to GB as required).

Uses only the Python standard library.

Usage:
    python file_size_chart.py <path_to_ll_output_file>
"""

import os
import sys


# --------------------------------------------------------------------------- #
# Size buckets                                                                 #
# --------------------------------------------------------------------------- #
# Each bucket is (label, lower_bound_inclusive_in_bytes, upper_bound_exclusive)
# Buckets grow roughly by a factor of 4, as hinted in the project spec.
KB = 1024
MB = 1024 * KB
GB = 1024 * MB
TB = 1024 * GB


def build_buckets():
    """Return the canonical list of size buckets."""
    return [
        ("0 B - 1 KB",      0,           1 * KB),
        ("1 - 4 KB",        1 * KB,      4 * KB),
        ("5 - 16 KB",       4 * KB,      16 * KB),
        ("17 - 64 KB",      16 * KB,     64 * KB),
        ("65 - 256 KB",     64 * KB,     256 * KB),
        ("257 KB - 1 MB",   256 * KB,    1 * MB),
        ("1 - 4 MB",        1 * MB,      4 * MB),
        ("5 - 16 MB",       4 * MB,      16 * MB),
        ("17 - 64 MB",      16 * MB,     64 * MB),
        ("65 - 256 MB",     64 * MB,     256 * MB),
        ("257 MB - 1 GB",   256 * MB,    1 * GB),
        ("1 - 4 GB",        1 * GB,      4 * GB),
        ("5 - 16 GB",       4 * GB,      16 * GB),
        ("17 - 64 GB",      16 * GB,     64 * GB),
        ("65 GB - 1 TB",    64 * GB,     1 * TB),
        ("1 TB +",          1 * TB,      float("inf")),
    ]


# --------------------------------------------------------------------------- #
# Parser                                                                       #
# --------------------------------------------------------------------------- #
def parse_ll_file(path):
    """
    Parse a file containing `ll` / `ls -l` output.

    Returns a list of file sizes (bytes) for regular files only
    (directories, symlinks and other non-file entries are skipped).
    """
    sizes = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.strip()

            # Blank line or the "total NNN" header from `ls -l`
            if not line or line.lower().startswith("total"):
                continue

            parts = line.split()
            if len(parts) < 5:
                continue

            perms = parts[0]
            # Regular files start with '-' (directories 'd', links 'l', etc.)
            if not perms or perms[0] != "-":
                continue

            # Column 5 (index 4) is the size in bytes for `ls -l`
            try:
                size = int(parts[4])
            except ValueError:
                continue

            sizes.append(size)
    return sizes


# --------------------------------------------------------------------------- #
# Bucketing                                                                    #
# --------------------------------------------------------------------------- #
def bucket_sizes(sizes, buckets):
    """Return a list of counts (one entry per bucket, same order as buckets)."""
    counts = [0] * len(buckets)
    for size in sizes:
        for i, (_, lo, hi) in enumerate(buckets):
            if lo <= size < hi:
                counts[i] += 1
                break
    return counts


# --------------------------------------------------------------------------- #
# Rendering                                                                    #
# --------------------------------------------------------------------------- #
def render_chart(buckets, counts, bar_width=40):
    """Return a string containing an ASCII table + bar chart."""
    total_files = sum(counts)
    if total_files == 0:
        return "No regular files were found in the provided `ll` output."

    # Trim trailing empty buckets so the chart is compact, but keep all
    # non-empty ones plus everything in between.
    last_non_empty = max(i for i, c in enumerate(counts) if c > 0)
    buckets = buckets[: last_non_empty + 1]
    counts = counts[: last_non_empty + 1]

    max_count = max(counts)
    label_w = max(len("Size Range"), max(len(b[0]) for b in buckets))
    count_w = max(len("Count"), len(str(max_count)))
    pct_w = len("100.0%")

    sep = "+-{}-+-{}-+-{}-+-{}-+".format(
        "-" * label_w, "-" * count_w, "-" * pct_w, "-" * bar_width
    )
    header = "| {:<{lw}} | {:>{cw}} | {:>{pw}} | {:<{bw}} |".format(
        "Size Range", "Count", "%", "Distribution",
        lw=label_w, cw=count_w, pw=pct_w, bw=bar_width,
    )

    lines = [sep, header, sep]
    for (label, _, _), count in zip(buckets, counts):
        pct = (count / total_files) * 100.0
        bar_len = int(round((count / max_count) * bar_width)) if max_count else 0
        bar = "#" * bar_len
        lines.append(
            "| {:<{lw}} | {:>{cw}} | {:>{pw}} | {:<{bw}} |".format(
                label,
                count,
                "{:.1f}%".format(pct),
                bar,
                lw=label_w, cw=count_w, pw=pct_w, bw=bar_width,
            )
        )
    lines.append(sep)
    lines.append("Total regular files: {}".format(total_files))
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Entry point                                                                  #
# --------------------------------------------------------------------------- #
def main(argv):
    if len(argv) != 2:
        print("Usage: python {} <path_to_ll_output_file>".format(
            os.path.basename(argv[0]) if argv else "file_size_chart.py"))
        return 1

    input_path = argv[1]
    if not os.path.isfile(input_path):
        print("Error: '{}' is not a readable file.".format(input_path))
        return 1

    sizes = parse_ll_file(input_path)
    buckets = build_buckets()
    counts = bucket_sizes(sizes, buckets)
    print(render_chart(buckets, counts))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
