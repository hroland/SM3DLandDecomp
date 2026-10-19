"""Translate ARMCC's embedded-assembly output into GNU assembler directives.

Instruction operands are preserved. Unknown directives fail rather than silently
dropping source. This supports the repository's hardware syscall/startup helpers
when the public compiler package has no separate armasm executable.
"""

import re

ASSERTIONS = {"{ENDIAN}=\"little\"", "{INTER}={TRUE}", "{ROPI}={FALSE}",
              "{RWPI}={FALSE}", "{IEEE_FULL}={FALSE}", "{IEEE_PART}={FALSE}",
              "{IEEE_JAVA}={FALSE}"}


def unquote_symbols(text):
    return re.sub(r"\|\|([^|]+)\|\||\|([^|]+)\|", lambda m: m.group(1) or m.group(2), text)


def translate(text):
    output = [".syntax unified", ".cpu mpcore", ".fpu vfp"]
    allocated = False
    current_function = None
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split(";", 1)[0].strip()
        if not line or line.startswith("#"):
            continue
        line = unquote_symbols(line)
        fields = line.split(None, 1)
        operation = fields[0].upper()
        argument = fields[1] if len(fields) == 2 else ""
        if operation == "AREA":
            parts = [p.strip() for p in argument.split(",")]
            allocated = "NOALLOC" not in parts
            if allocated:
                flags = "ax" if "CODE" in parts else "a" if "READONLY" in parts else "aw"
                output.append(f'.section "{parts[0]}","{flags}",%progbits')
                align = next((p.split("=", 1)[1] for p in parts if p.startswith("ALIGN=")), "2")
                output.append(f".p2align {align}")
            continue
        if operation == "ASSERT":
            if re.sub(r"\s+", "", argument) not in ASSERTIONS:
                raise ValueError(f"Unsupported target assertion on line {number}: {line}")
            continue
        if operation in ("ATTR", "PRESERVE8", "REQUIRE8", "END"):
            continue  # Object metadata; no instruction/data bytes.
        if operation == "IMPORT":
            name = argument.split()[0]
            output.append((".weak " if "WEAK" in argument else ".extern ") + name)
            continue
        if not allocated:
            continue
        if operation in ("ARM", "THUMB"):
            output.append(".arm" if operation == "ARM" else ".thumb")
        elif operation == "EXPORT":
            output.append(".global " + argument.split()[0])
        elif argument.upper().startswith("PROC"):
            if current_function:
                raise ValueError("Nested assembler functions are unsupported")
            current_function = fields[0]
            output += [f".type {current_function}, %function", current_function + ":"]
        elif operation == "ENDP":
            if not current_function:
                raise ValueError("ENDP without PROC")
            output.append(f".size {current_function}, .-{current_function}")
            current_function = None
        elif operation in ("DCD", "DCB", "DCW", "DCFS", "DCFD", "SPACE"):
            directive = {"DCD": ".word", "DCB": ".byte", "DCW": ".hword",
                         "DCFS": ".float", "DCFD": ".double", "SPACE": ".space"}[operation]
            output.append(directive + " " + argument)
        elif operation == "ALIGN":
            alignment = int(argument, 0) if argument else 4
            if alignment <= 0 or alignment & (alignment - 1):
                raise ValueError("Assembler alignment must be a power of two")
            output.append(f".balign {alignment}")
        elif operation == "LTORG":
            output.append(".ltorg")
        elif argument.upper().startswith("EQU "):
            output.append(".equ " + fields[0] + ", " + argument[4:])
        elif len(fields) == 1:
            # Branch/no-operand instructions are distinguishable from labels.
            if operation in ("NOP", "WFI", "WFE", "YIELD", "SEV", "CLREX"):
                output.append(line.lower())
            elif re.fullmatch(r"[A-Za-z_.$][\w.$]*|[0-9]+", fields[0]):
                output.append(fields[0] + ":")
            else:
                raise ValueError(f"Unsupported assembler line {number}: {line}")
        else:
            if operation in ("GET", "INCLUDE", "MACRO", "MEND", "IF", "ELSE", "ENDIF", "OPT"):
                raise ValueError(f"Unsupported assembler directive on line {number}: {line}")
            instruction = re.sub(r"%B([0-9]+)", r"\1b", line)
            instruction = re.sub(r"%F([0-9]+)", r"\1f", instruction)
            output.append(instruction)
    if current_function:
        raise ValueError("Unterminated assembler function")
    return "\n".join(output) + "\n"
