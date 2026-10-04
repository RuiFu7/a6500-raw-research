"""Disassemble ARM ET_REL modules and annotate relocation targets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import capstone
from elftools.elf.elffile import ELFFile


def load_symbols(elf: ELFFile) -> tuple[dict[int, str], dict[int, str]]:
    address_names: dict[int, str] = {}
    index_names: dict[int, str] = {}
    sections = [section for section in elf.iter_sections()
                if section["sh_type"] == "SHT_SYMTAB"]
    if not sections:
        sections = [section for section in elf.iter_sections()
                    if section["sh_type"] == "SHT_DYNSYM"]
    for section in sections:
        for index, symbol in enumerate(section.iter_symbols()):
            name = symbol.name
            if not name:
                continue
            index_names[index] = name
            if symbol["st_value"] != 0:
                address_names[symbol["st_value"] & ~1] = name
    return address_names, index_names


def load_functions(elf: ELFFile) -> list[tuple[int, int, str, bool]]:
    functions: list[tuple[int, int, str, bool]] = []
    sections = [section for section in elf.iter_sections()
                if section["sh_type"] == "SHT_SYMTAB"]
    if not sections:
        sections = [section for section in elf.iter_sections()
                    if section["sh_type"] == "SHT_DYNSYM"]
    for section in sections:
        for symbol in section.iter_symbols():
            if (
                symbol.name
                and symbol["st_info"]["type"] == "STT_FUNC"
                and symbol["st_value"] != 0
            ):
                functions.append(
                    (
                        symbol["st_value"] & ~1,
                        symbol["st_size"],
                        symbol.name,
                        bool(symbol["st_value"] & 1),
                    )
                )
    return sorted(set(functions))


def load_relocations(elf: ELFFile) -> dict[int, str]:
    _, index_names = load_symbols(elf)
    by_offset: dict[int, str] = {}
    for section in elf.iter_sections():
        if section.name not in (".rel.text", ".rel.init.text", ".rel.exit.text"):
            continue
        for reloc in section.iter_relocations():
            offset = reloc["r_offset"]
            by_offset[offset] = index_names.get(reloc["r_info_sym"], "")
    return by_offset


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--filter", default="", help="symbol name substring")
    parser.add_argument("--targets", default="", help="comma-separated symbol names")
    args = parser.parse_args()

    targets = {item for item in args.targets.split(",") if item}
    with args.input.open("rb") as stream:
        elf = ELFFile(stream)
        text = next(section for section in elf.iter_sections() if section.name == ".text")
        data = text.data()
        base = text["sh_addr"]
        relocations = load_relocations(elf)
        symbol_names, _ = load_symbols(elf)
        functions = load_functions(elf)

        for address, size, name, thumb in functions:
            if args.filter and args.filter not in name:
                continue
            if targets and name not in targets:
                continue
            start = address - base
            if size:
                end = min(start + size, len(data))
            else:
                end = min(start + 0x400, len(data))
            mode = capstone.CS_MODE_THUMB if thumb else capstone.CS_MODE_ARM
            md = capstone.Cs(capstone.CS_ARCH_ARM, mode)
            md.detail = True
            print(f"== {name} @ 0x{address:x} (thumb={thumb})")
            for instruction in md.disasm(data[start:end], address):
                annotation = ""
                for offset in range(instruction.size):
                    target_name = relocations.get(instruction.address + offset)
                    if target_name:
                        annotation = f"; {target_name}"
                        break
                if instruction.mnemonic in ("bl", "blx", "b", "bx") and not annotation:
                    for operand in instruction.operands:
                        if operand.type == capstone.arm.ARM_OP_IMM and operand.imm in symbol_names:
                            annotation = f"; {symbol_names[operand.imm]}"
                            break
                print(
                    f"  0x{instruction.address:08x}: {instruction.mnemonic:<8} "
                    f"{instruction.op_str} {annotation}".rstrip()
                )
    return 0


if __name__ == "__main__":
    sys.exit(main())
