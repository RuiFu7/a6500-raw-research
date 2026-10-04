"""Patch the alpha6500 kernel so panic() dumps its message to ttyAM0 UART.

The full alpha6500 kernel panics inside setup_arch in QEMU, before the serial
console is registered, so the reason text is lost.  This tool replaces the
printk call in panic() with a tiny ARM routine that writes the formatted panic
buffer (still in r1 at that point) to the PL011 UART at 0xf2000000, then
halts.  The routine fits a 44-byte alignment gap inside .text.  It is an
offline emulator aid only; it is never applied to a camera.
"""

import os
import struct
import sys

UART_DR = 0xf2000000
UART_FR = UART_DR + 0x18
PANIC_BUF = 0x4042b710
PANIC_PRINTK_OFFSET = 0x2afa4c       # file offset of `bl printk` in panic()
# 44-byte zero gap inside .text, directly after a function epilogue.
PANIC_ROUTINE_OFFSET = 0x2abbc0


def encode_bl(addr: int, target: int) -> bytes:
    offset = target - (addr + 8)
    if offset < -0x2000000 or offset >= 0x2000000:
        raise ValueError('BL target out of range: %d' % offset)
    return struct.pack('<I', 0xeb000000 | ((offset >> 2) & 0x00ffffff))


def build_uart_dump() -> bytes:
    # r1 still points at the formatted panic buffer when printk is replaced.
    # 11 instructions, 44 bytes; fits the .text gap exactly.
    words = [
        0xe3002000,  # movw r2, #0
        0xe3402f20,  # movt r2, #0xf200     ; UART base
        0xe4d13001,  # loop: ldrb r3, [r1], #1
        0xe3530000,  # cmp  r3, #0
        0x0a000004,  # beq  halt
        0xe5924018,  # wait: ldr r4, [r2, #0x18] ; FR
        0xe3140020,  # tst  r4, #0x20       ; TXFF
        0x1afffffc,  # bne  wait
        0xe5823000,  # str  r3, [r2]        ; DR
        0xeafffff7,  # b    loop
        0xeafffffe,  # halt: b halt
    ]
    return b''.join(struct.pack('<I', w) for w in words)


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: patch_panic_uart.py <kernel.bin> <out.bin>')
        return 1
    kernel = bytearray(open(sys.argv[1], 'rb').read())
    base = 0x40038000
    routine = build_uart_dump()
    routine_addr = base + PANIC_ROUTINE_OFFSET
    if len(routine) > len(kernel) - PANIC_ROUTINE_OFFSET:
        raise SystemExit('not enough free space for UART routine')
    kernel[PANIC_ROUTINE_OFFSET:PANIC_ROUTINE_OFFSET + len(routine)] = routine
    old = kernel[PANIC_PRINTK_OFFSET:PANIC_PRINTK_OFFSET + 4]
    kernel[PANIC_PRINTK_OFFSET:PANIC_PRINTK_OFFSET + 4] = encode_bl(
        base + PANIC_PRINTK_OFFSET, routine_addr)
    with open(sys.argv[2], 'wb') as out:
        out.write(kernel)
    print('patched BL at file 0x%x: %s -> %s -> 0x%x'
          % (PANIC_PRINTK_OFFSET, old.hex(),
             bytes(kernel[PANIC_PRINTK_OFFSET:PANIC_PRINTK_OFFSET + 4]).hex(),
             routine_addr))
    print('placed %d-byte UART dump routine at 0x%x'
          % (len(routine), routine_addr))
    return 0


if __name__ == '__main__':
    sys.exit(main())
