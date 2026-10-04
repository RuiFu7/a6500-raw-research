"""Print ELF metadata and function symbols."""

import argparse
import sys

from elftools.elf.elffile import ELFFile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    args = parser.parse_args()

    with open(args.input, "rb") as f:
        elf = ELFFile(f)
        print(
            "machine:",
            elf.header["e_machine"],
            "type:",
            elf.header["e_type"],
            "endian:",
            "big" if elf.little_endian is False else "little",
        )
        for sec in elf.iter_sections():
            print(
                f"section {sec.name}: {sec['sh_type']} addr=0x{sec['sh_addr']:x} "
                f"size=0x{sec['sh_size']:x}"
            )
        for sec in elf.iter_sections():
            if sec["sh_type"] not in ("SHT_SYMTAB", "SHT_DYNSYM"):
                continue
            print(f"== {sec.name}")
            for sym in sec.iter_symbols():
                if not sym.name:
                    continue
                if sym["st_info"]["type"] in ("STT_FUNC", "STT_NOTYPE"):
                    print(f"  {sym['st_value']:#010x} {sym.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
