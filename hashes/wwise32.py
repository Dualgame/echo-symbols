#!/usr/bin/env python3
"""Wwise-32: the 32-bit id Wwise gives a named sound object (event, bus, state, switch, game parameter).

    h = 0x811c9dc5                                  (FNV offset basis)
    for each byte c of the name, ASCII 'A'-'Z' folded to 'a'-'z':
        h = (h * 0x01000193) ^ c                    (mod 2**32; FNV-1: multiply, then xor)

The result is printed as "0x" + 8 lowercase hex digits. This is not CSymbol64: the two hashes never mix.
Case folds, so an id never tells you the authored capitalisation.

    python3 hashes/wwise32.py Play_Collision_01
"""
import sys

_FOLD = bytes(c + 32 if 0x41 <= c <= 0x5A else c for c in range(256))


def wwise32(name):
    """Hash `name` (str or bytes) to an unsigned 32-bit int."""
    data = name.encode("ascii") if isinstance(name, str) else bytes(name)
    h = 0x811C9DC5
    for c in data.translate(_FOLD):
        h = ((h * 0x01000193) & 0xFFFFFFFF) ^ c
    return h


def canonical32(h):
    return "0x%08x" % h


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(canonical32(wwise32(arg)), arg, sep="\t")
