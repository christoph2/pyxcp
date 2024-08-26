#!/usr/bin/env python
"""Optimize data-structures like memory sections."""

from itertools import groupby
from operator import attrgetter
from typing import List

from pyxcp.cpp_ext import McObject


def make_continuous_blocks(chunks: List[McObject], upper_bound=None, upper_bound_initial=None) -> List[McObject]:
    """Try to make continous blocks from a list of small, unordered `chunks`.

    Parameters
    ----------
    chunks: list of `McObject`

    Returns
    -------
    sorted list of `McObject`
    """

    def key_func(x):
        return (x.ext, x.address)

    values = []
    # 1. Groupy by address.
    for _key, value in groupby(sorted(chunks, key=key_func), key=key_func):
        # 2. Pick the largest one.
        values.append(max(value, key=attrgetter("length")))
    result_sections = []
    last_section = None
    last_ext = None
    first_section = True
    if upper_bound_initial is None:
        upper_bound_initial = upper_bound
    while values:
        section = values.pop(0)
        if (last_section and section.address <= last_section.address + last_section.length) and not (section.ext != last_ext):
            last_end = last_section.address + last_section.length - 1
            current_end = section.address + section.length - 1
            if last_end > section.address:
                pass
            else:
                offset = current_end - last_end
                if upper_bound:
                    if first_section:
                        upper_bound = upper_bound_initial
                        first_section = False
                    if last_section.length + offset <= upper_bound:
                        last_section.length += offset
                        last_section.add_component(section)
                    else:
                        result_sections.append(
                            McObject(name="", address=section.address, ext=section.ext, length=section.length, components=[section])
                        )
                else:
                    last_section.length += offset
                    last_section.add_component(section)
        else:
            # Create a new section.
            result_sections.append(
                McObject(name="", address=section.address, ext=section.ext, length=section.length, components=[section])
            )
        last_section = result_sections[-1]
        last_ext = last_section.ext
    return result_sections
