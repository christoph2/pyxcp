#!/usr/bin/env python
"""Bin-packing algorithms.
"""
from typing import List, Optional

from pyxcp.cpp_ext import Bin


def first_fit_decreasing(items, bin_size: int, initial_bin_size: Optional[int] = None) -> List[Bin]:
    """bin-packing with first-fit-decreasing algorithm.

    Parameters
    ----------
    items: list
        items that need to be stored/allocated.

    bin_size: int

    Returns
    -------
    list
        Resulting bins
    """
    if initial_bin_size is None:
        initial_bin_size = bin_size
    # bin_size = max(bin_size, initial_bin_size)
    bins = [Bin(size=initial_bin_size)]  # Initial bin
    for item in sorted(items, key=lambda x: x.length, reverse=True):
        if item.length > bin_size:
            raise ValueError(f"Item {item!r} is too large to fit in a {bin_size} byte sized bin.")
        for bin in bins:
            if bin.residual_capacity >= item.length:
                bin.append(item)
                bin.residual_capacity -= item.length
                break
        else:
            new_bin = Bin(size=bin_size)
            bins.append(new_bin)
            new_bin.append(item)
            new_bin.residual_capacity -= item.length
    return bins
