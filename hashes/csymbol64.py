#!/usr/bin/env python3
"""CSymbol64: the 64-bit name hash of the engine behind Lone Echo, Lone Echo II and Echo VR.

    h = 0xffffffffffffffff
    for each byte c of the name, ASCII 'A'-'Z' folded to 'a'-'z':
        h = (h << 8) ^ T[h >> 56] ^ c            (mod 2**64)

T[i] is the carry-less product of P = 0x95ac9329ac4bc9b5 and 2*i, truncated to 64 bits (no reduction: it is not
a textbook CRC-64 table). The result is printed as "0x" + 16 lowercase hex digits. Names are ASCII; case folds,
so a hash never tells you the authored capitalisation.

    python3 hashes/csymbol64.py mpl_arena_a          # 0x576ed3f8428ebc4b
"""
import sys

P = 0x95AC9329AC4BC9B5
MASK = (1 << 64) - 1


def _clmul(a, b):
    r = 0
    while b:
        if b & 1:
            r ^= a
        a <<= 1
        b >>= 1
    return r & MASK


TABLE = [_clmul(P, 2 * i) for i in range(256)]
_FOLD = bytes(c + 32 if 0x41 <= c <= 0x5A else c for c in range(256))


def csymbol64(name):
    """Hash `name` (str or bytes) to an unsigned 64-bit int."""
    data = name.encode("ascii") if isinstance(name, str) else bytes(name)
    h = MASK
    for c in data.translate(_FOLD):
        h = ((h << 8) & MASK) ^ TABLE[h >> 56] ^ c
    return h


def canonical(h):
    return "0x%016x" % h


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(canonical(csymbol64(arg)), arg, sep="\t")
