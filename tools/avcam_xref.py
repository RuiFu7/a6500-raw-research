"""Find pc-relative string references in av-cam.bin (Thumb-2, base 0)."""

import argparse
import sys

import capstone
import capstone.arm


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--targets", default="")
    args = parser.parse_args()

    data = open(args.input, "rb").read()
    targets = [int(t, 16) for t in args.targets.split(",") if t]
    target_set = set(targets)

    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    md.detail = True
    last_ldr = {}
    hits = []
    window = 0
    for ins in md.disasm(data, 0):
        if ins.id == capstone.arm.ARM_INS_LDR:
            ops = ins.operands
            if len(ops) == 2 and ops[1].type == capstone.arm.ARM_OP_MEM:
                mem = ops[1].mem
                if mem.base == capstone.arm.ARM_REG_PC and mem.index == 0:
                    lit = ((ins.address + 4) & ~3) + mem.disp
                    if lit + 4 <= len(data):
                        last_ldr[ops[0].reg] = (
                            ins.address,
                            lit,
                            int.from_bytes(data[lit:lit + 4], "little"),
                        )
        elif (
            ins.mnemonic == "add"
            and len(ins.operands) == 2
            and ins.operands[1].reg == capstone.arm.ARM_REG_PC
            and ins.operands[0].reg in last_ldr
        ):
            reg = ins.operands[0].reg
            ldr_addr, lit_addr, value = last_ldr[reg]
            base = ins.address + 4
            target = (value + base) & 0xFFFFFFFF
            if target in target_set:
                hits.append((ldr_addr, ins.address, lit_addr, target))
        elif (
            (ins.mnemonic == "adr" or ins.mnemonic == "add")
            and len(ins.operands) >= 2
            and ins.operands[1].reg == capstone.arm.ARM_REG_PC
            and ins.operands[0].type == capstone.arm.ARM_OP_REG
        ):
            if len(ins.operands) == 2:
                candidates = {
                    ((ins.address + 4) & ~3) + ins.operands[1].imm,
                    ins.operands[1].imm,
                }
            elif len(ins.operands) == 3:
                candidates = {
                    ((ins.address + 4) & ~3) + ins.operands[2].imm,
                    ins.operands[2].imm,
                }
            else:
                continue
            for target in candidates:
                target &= 0xFFFFFFFF
                if target in target_set:
                    hits.append((ins.address, ins.address, 0, target))
        window += 1
        if window > 8:
            last_ldr.clear()
            window = 0

    for ldr_addr, add_addr, lit_addr, target in hits:
        print(
            f"ldr@0x{ldr_addr:x} add@0x{add_addr:x} lit@0x{lit_addr:x} "
            f"-> 0x{target:x}"
        )
    print(f"total hits: {len(hits)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
