"""Patch the alpha6500 kernel for QEMU: register a RAM bank in the Sony
allocator's private bank table.

In QEMU the mach-cxd90014 memory-bank handoff is empty, so the Sony boot
allocator sees bank0 = {0, 0}.  Its first request ("0x1000 bytes below 0x0",
the initial page table) then fails and panic() halts the kernel.  This tool
replaces the private bank-table init (FUN_403baea0) with an equivalent that
registers one 1GB bank at physical 0x80000000, and NOPs the later "set default
end" helper so a zero DRAM-size handoff cannot overwrite it.  Offline
emulator aid only; never applied to a camera.
"""

import struct
import sys

BASE = 0x40038000

# Replacement body for FUN_403baea0 (26 instructions, 104 bytes).
BANK_INIT_WORDS = [
    0xe59f0060,  # ldr  r0, [pc, #0x60] ; &init flag
    0xe3a01001,  # mov  r1, #1
    0xe5801000,  # str  r1, [r0]
    0xe59f0058,  # ldr  r0, [pc, #0x58] ; bank table base
    0xe3a02080,  # mov  r2, #0x80
    0xe5802010,  # str  r2, [r0, #0x10]
    0xe580201c,  # str  r2, [r0, #0x1c]
    0xe2802028,  # add  r2, r0, #0x28   ; bank0 array
    0xe5802014,  # str  r2, [r0, #0x14]
    0xe2803e43,  # add  r3, r0, #0x430  ; bank1 array
    0xe5803020,  # str  r3, [r0, #0x20]
    0xe59f2038,  # ldr  r2, [pc, #0x38] ; 0x80000000
    0xe5802028,  # str  r2, [r0, #0x28] ; bank0 start
    0xe59f2030,  # ldr  r2, [pc, #0x30] ; 0x40000000
    0xe580202c,  # str  r2, [r0, #0x2c] ; bank0 size
    0xe3a02000,  # mov  r2, #0
    0xe5832000,  # str  r2, [r3]
    0xe5832004,  # str  r2, [r3, #4]
    0xe59f2018,  # ldr  r2, [pc, #0x18] ; bank magic
    0xe5802428,  # str  r2, [r0, #0x428]
    0xe5802830,  # str  r2, [r0, #0x830]
    0xe580100c,  # str  r1, [r0, #0xc]  ; bank count
    0xe5801018,  # str  r1, [r0, #0x18]
    0xe3e02000,  # mvn  r2, #0
    0xe5802004,  # str  r2, [r0, #4]    ; default end
    0xe1a0f00e,  # mov  pc, lr
]

BANK_INIT_LITERALS = [
    0x403d3190,  # init flag address
    0x40430ecc,  # bank table base
    0x80000000,  # QEMU RAM start
    0x40000000,  # 1GB
    0x9d74e35b,  # original bank magic
]

# FUN_403baea0 spans 0x403baea0..0x403baf1f (file 0x382ea0..0x382f1f).
FUNC_403BAEA0 = 0x403baea0

# sm_mem_set_default_end: ldr r3,[pc,#4] / str r0,[r3,#4] / ...
# NOP the store so a zero handoff size cannot clobber the default end.
SET_END_STORE = 0x400d5344


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: patch_kernel_qemu_mem.py <kernel.bin> <out.bin>')
        return 1
    kernel = bytearray(open(sys.argv[1], 'rb').read())
    base_off = FUNC_403BAEA0 - BASE
    code = b''.join(struct.pack('<I', w) for w in BANK_INIT_WORDS)
    literals = b''.join(struct.pack('<I', w) for w in BANK_INIT_LITERALS)
    if len(code) + len(literals) > 0x80:
        raise SystemExit('bank init replacement too large')
    kernel[base_off:base_off + len(code)] = code
    lit_off = base_off + len(code)
    kernel[lit_off:lit_off + len(literals)] = literals

    set_end = SET_END_STORE - BASE
    old = bytes(kernel[set_end:set_end + 4])
    kernel[set_end:set_end + 4] = struct.pack('<I', 0xe320f000)  # nop
    print('bank init: wrote %d code + %d literal bytes at 0x%x'
          % (len(code), len(literals), FUNC_403BAEA0))
    print('default-end store at 0x%x: %s -> nop'
          % (SET_END_STORE, old.hex()))
    with open(sys.argv[2], 'wb') as out:
        out.write(kernel)
    return 0


if __name__ == '__main__':
    sys.exit(main())
