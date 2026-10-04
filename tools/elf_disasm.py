"""Disassemble ARM ELF functions with capstone and annotate calls."""

import argparse
import sys

import capstone
from elftools.elf.elffile import ELFFile


def load_symbols(elf):
    syms = {}
    for sec in elf.iter_sections():
        if sec["sh_type"] not in ("SHT_SYMTAB", "SHT_DYNSYM"):
            continue
        for sym in sec.iter_symbols():
            if sym.name and sym["st_value"]:
                syms[sym["st_value"] & ~1] = sym.name
    return syms


def plt_import_map(elf, syms):
    """Map PLT entry addresses to import names using .rel.plt order."""
    mapping = {}
    for sec in elf.iter_sections():
        if sec.name == ".rel.plt":
            relocs = list(sec.iter_relocations())
        elif sec.name == ".plt":
            plt_sec = sec
    try:
        base = plt_sec["sh_addr"] + 16
        for i, rel in enumerate(relocs):
            idx = rel["r_info_sym"]
            for s in elf.iter_sections():
                if s["sh_type"] == "SHT_DYNSYM":
                    name = s.get_symbol(idx).name
                    break
            mapping[base + i * 12] = name
    except UnboundLocalError:
        pass
    return mapping


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--filter", default="", help="only symbols containing this substring")
    args = parser.parse_args()

    with open(args.input, "rb") as f:
        elf = ELFFile(f)
        syms = load_symbols(elf)
        plt_map = plt_import_map(elf, syms)
        text = next(s for s in elf.iter_sections() if s.name == ".text")
        data = text.data()
        base = text["sh_addr"]

        funcs = []
        for sec in elf.iter_sections():
            if sec["sh_type"] not in ("SHT_SYMTAB", "SHT_DYNSYM"):
                continue
            for sym in sec.iter_symbols():
                if (
                    sym.name
                    and sym["st_info"]["type"] == "STT_FUNC"
                    and sym["st_value"] != 0
                    and sym["st_value"] >= base
                    and sym["st_value"] < base + len(data)
                ):
                    funcs.append(
                        (
                            sym["st_value"] & ~1,
                            sym["st_size"],
                            sym.name,
                            bool(sym["st_value"] & 1),
                        )
                    )
        funcs.sort()

        for addr, size, name, thumb in funcs:
            if args.filter and args.filter not in name:
                continue
            start = addr - base
            if size:
                end = min(start + size, len(data))
            else:
                end = min(start + 0x400, len(data))
            md = capstone.Cs(
                capstone.CS_ARCH_ARM,
                capstone.CS_MODE_THUMB if thumb else capstone.CS_MODE_ARM,
            )
            md.detail = True
            print(f"== {name} @ 0x{addr:x} (thumb={thumb})")
            for ins in md.disasm(data[start:end], addr):
                note = ""
                if ins.mnemonic.startswith("b") and ins.operands:
                    t = ins.operands[0].imm
                    if t in plt_map:
                        note = f"; -> {plt_map[t]}"
                    elif t in syms:
                        note = f"; -> {syms[t]}"
                print(f"  0x{ins.address:x}: {ins.mnemonic}\t{ins.op_str} {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
