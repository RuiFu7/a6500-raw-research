// Dump 32-bit words from the current program's memory.
// Usage (headless):
//   -postScript GhidraDumpWords.java 403b2ea8 403b2ed8 out words.txt
// @category A6500

import java.io.FileWriter;
import java.io.PrintWriter;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.Memory;

public class GhidraDumpWords extends GhidraScript {

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String outPath = null;
        long start = -1;
        long end = -1;
        for (int i = 0; i < args.length; i++) {
            if (args[i].equals("out") && i + 1 < args.length) {
                outPath = args[++i];
            }
            else if (start < 0) {
                start = Long.parseLong(args[i], 16);
            }
            else {
                end = Long.parseLong(args[i], 16);
            }
        }
        if (start < 0 || end < 0 || end < start) {
            println("usage: start end [out path]");
            return;
        }

        Memory memory = currentProgram.getMemory();
        StringBuilder out = new StringBuilder();
        Address current = toAddr(start);
        Address last = toAddr(end);
        while (current.compareTo(last) <= 0) {
            int value = memory.getInt(current);
            out.append(current).append("  ").append(Long.toHexString(value & 0xffffffffL)).append('\n');
            current = current.add(4);
        }

        if (outPath == null) {
            println(out.toString());
        }
        else {
            try (PrintWriter writer = new PrintWriter(new FileWriter(outPath))) {
                writer.print(out.toString());
            }
        }
    }
}
