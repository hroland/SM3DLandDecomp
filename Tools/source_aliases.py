"""Validate symbolic aliases to actual compiled functions, never fixed addresses."""

import json
import re

IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_.$]*\Z")


def alias_script(rows, definitions):
    result, seen = [], set()
    for row in rows:
        if set(row) - {"alias", "target", "reason"}:
            raise ValueError("source aliases cannot contain addresses or unrecognized fields")
        alias, target = row["alias"], row["target"]
        if not isinstance(alias, str) or not isinstance(target, str):
            raise ValueError("source aliases require symbol names")
        if not IDENTIFIER.fullmatch(alias) or not IDENTIFIER.fullmatch(target) or alias == target:
            raise ValueError("invalid source alias names")
        if alias in seen or definitions.get(alias):
            raise ValueError("duplicate or already defined source alias: " + alias)
        targets = definitions.get(target, [])
        if len(targets) != 1:
            raise ValueError("source alias must target one actual compiled function: " + target)
        definition = targets[0]
        if ("stub" in definition["section"].lower() or definition["size"] <= 0
                or definition["binding"] not in ("STB_GLOBAL", "STB_WEAK")):
            raise ValueError("source alias cannot target a placeholder or local/empty definition")
        result.append(f"{json.dumps(alias)} = {json.dumps(target)};")
        seen.add(alias)
    return result
