"""Branch-following Thumb-2 disassembler for av-cam.bin (base 0)."""

import argparse
import sys

import capstone
import capstone.arm


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--targets", default="")
    parser.add_argument("--max-insns", type=int, default=300000)
    args = parser.parse_args()

    data = open(args.input, "rb").read()
    target_set = {int(t, 16) for t in args.targets.split(",") if t}
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    md.detail = True
    md_probe = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)

    seeds = [0x1C020, 0x1C204, 0x1C298, 0x5C9F68, 0x5C9F86]
    seed_set = set(seeds)

    # Collect all Thumb BL targets as additional function-entry seeds.
    for i in range(0, len(data) - 4, 2):
        hw1 = int.from_bytes(data[i:i + 2], "little")
        hw2 = int.from_bytes(data[i + 2:i + 4], "little")
        if (hw1 & 0xF800) == 0xF000 and (hw2 & 0xD000) == 0xD000:
            s = (hw1 >> 10) & 1
            imm10 = hw1 & 0x3FF
            j1 = (hw2 >> 13) & 1
            j2 = (hw2 >> 11) & 1
            imm11 = hw2 & 0x7FF
            imm = (
                (s << 24)
                | ((~(j1 ^ s) & 1) << 23)
                | ((~(j2 ^ s) & 1) << 22)
                | (imm10 << 12)
                | (imm11 << 1)
            )
            if s:
                imm -= 1 << 24
            target = i + 4 + imm
            if 0 <= target < len(data) and target not in seed_set:
                first = next(
                    iter(md_probe.disasm(data[target:target + 8], target)), None
                )
                if first and first.mnemonic.startswith("push"):
                    seed_set.add(target)
                    seeds.append(target)

    queue = [(a, 0) for a in seeds[:5000]]
    visited = set()
    insn_count = 0
    hits = []

    while queue and insn_count < args.max_insns:
        addr, _mode = queue.pop()
        if addr in visited or addr >= len(data):
            continue
        last_ldr = {}
        window = 0
        for ins in md.disasm(data[addr:], addr):
            if ins.address in visited:
                break
            visited.add(ins.address)
            insn_count += 1
            if insn_count >= args.max_insns:
                break

            if ins.id == capstone.arm.ARM_INS_LDR and len(ins.operands) == 2:
                mem = ins.operands[1]
                if (
                    mem.type == capstone.arm.ARM_OP_MEM
                    and mem.mem.base == capstone.arm.ARM_REG_PC
                    and mem.mem.index == 0
                ):
                    lit = ((ins.address + 4) & ~3) + mem.mem.disp
                    if lit + 4 <= len(data):
                        last_ldr[ins.operands[0].reg] = (
                            ins.address,
                            int.from_bytes(data[lit:lit + 4], "little"),
                        )

            base = (ins.address + 4) & ~3
            candidates = set()
            if ins.mnemonic == "adr" and len(ins.operands) == 2:
                candidates = {base + ins.operands[1].imm, ins.operands[1].imm}
            elif ins.mnemonic == "add" and len(ins.operands) == 3:
                if ins.operands[1].reg == capstone.arm.ARM_REG_PC:
                    candidates = {base + ins.operands[2].imm}
            elif ins.mnemonic == "add" and len(ins.operands) == 2:
                if (
                    ins.operands[1].reg == capstone.arm.ARM_REG_PC
                    and ins.operands[0].reg in last_ldr
                ):
                    candidates = {last_ldr[ins.operands[0].reg][1] + base}
            for target in candidates:
                target &= 0xFFFFFFFF
                if target in target_set:
                    hits.append((ins.address, target))

            # branch handling
            if ins.mnemonic.startswith(("b", "cbz", "cbnz")):
                if ins.mnemonic in ("b", "bl", "blx", "b.w"):
                    for op in ins.operands:
                        if op.type == capstone.arm.ARM_OP_IMM:
                            queue.append((op.imm & 0xFFFFFFFF, 0))
                if ins.mnemonic in ("b", "b.w", "bx", "blx"):
                    break
                elif ins.mnemonic in ("cbz", "cbnz"):
                    for op in ins.operands:
                        if op.type == capstone.arm.ARM_OP_IMM:
                            queue.append((op.imm & 0xFFFFFFFF, 0))
            if "pop" in ins.mnemonic or "ldmia" in ins.mnemonic:
                if any(o.type == capstone.arm.ARM_OP_REG
                       and o.reg == capstone.arm.ARM_REG_PC
                       for o in ins.operands):
                    break
            window += 1
            if window > 8:
                last_ldr.clear()
                window = 0

    for addr, target in hits:
        print(f"0x{addr:x} -> 0x{target:x}")
    print(f"visited {insn_count} instructions, {len(hits)} hits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
