"""Find which ELF files define/import symbols matching a substring."""

import argparse
import os
import sys

from elftools.elf.elffile import ELFFile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--defined-only", action="store_true")
    args = parser.parse_args()

    for dirpath, _dirs, files in os.walk(args.root):
        for name in files:
            path = os.path.join(dirpath, name)
            try:
                f = open(path, "rb")
                if f.read(4) != b"\x7fELF":
                    f.close()
                    continue
                f.seek(0)
                elf = ELFFile(f)
            except Exception:
                try:
                    f.close()
                except UnboundLocalError:
                    pass
                continue
            try:
                for sec in elf.iter_sections():
                    if sec["sh_type"] not in ("SHT_SYMTAB", "SHT_DYNSYM"):
                        continue
                    for sym in sec.iter_symbols():
                        if not sym.name or args.symbol not in sym.name:
                            continue
                        defined = sym["st_value"] != 0 or sym["st_shndx"] != "SHN_UNDEF"
                        if args.defined_only and not defined:
                            continue
                        print(
                            f"{path}: {sym['st_info']['type']} "
                            f"{'defined' if defined else 'import'} "
                            f"{sym['st_value'] & ~1:#x} {sym.name}"
                        )
            finally:
                f.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
