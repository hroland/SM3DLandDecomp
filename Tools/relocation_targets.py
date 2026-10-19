"""Recover missing direct-call addresses only when all other function bytes agree."""

import struct


def signed_branch_addend(word):
    immediate = word & 0xFFFFFF
    if immediate & 0x800000:
        immediate -= 1 << 24
    return immediate << 2


def infer_targets(actual, original, address, relocations, text_start, text_end):
    if len(actual) != len(original):
        return {}, "different function extents"
    masked_actual, masked_original = bytearray(actual), bytearray(original)
    candidates = {}
    for relocation in relocations:
        offset, kind = relocation["offset"], relocation["type"]
        if offset < 0 or offset + 4 > len(actual):
            return {}, "relocation outside the selected function"
        emitted, stock = (struct.unpack_from("<I", data, offset)[0] for data in (actual, original))
        known = relocation.get("known_address")
        if kind == 2:  # R_ARM_ABS32: require an independently known target.
            if known is None or ((known + emitted) & 0xFFFFFFFF) != stock:
                return {}, "absolute relocation has no confirmed original target"
            masked_actual[offset:offset + 4] = masked_original[offset:offset + 4] = bytes(4)
        elif kind in (1, 28, 29):  # PC24, CALL, JUMP24; ARM instruction encodings only.
            if (emitted >> 24) != (stock >> 24) or (stock & 0x0E000000) != 0x0A000000:
                return {}, "branch form or condition differs"
            target = address + offset + 8 + signed_branch_addend(stock)
            symbol_address = target - signed_branch_addend(emitted) - 8
            if known is not None and known != symbol_address:
                return {}, "branch disagrees with a confirmed original symbol"
            if not text_start <= symbol_address < text_end or symbol_address % 4:
                return {}, "inferred branch target is outside aligned EU ARM code"
            if known is None:
                name = relocation["symbol"]
                if not name or not relocation.get("global", False):
                    return {}, "unknown local branch target requires manual review"
                if name in candidates and candidates[name] != symbol_address:
                    return {}, "one symbol has conflicting branch targets"
                candidates[name] = symbol_address
            masked_actual[offset:offset + 3] = masked_original[offset:offset + 3] = bytes(3)
        elif kind != 40:  # V4BX leaves the ARMv6 BX encoding intact.
            return {}, f"unsupported relocation {kind}"
    if masked_actual != masked_original:
        return {}, "non-relocation instruction or literal bytes differ"
    return candidates, "all non-relocation bytes and branch forms agree"
