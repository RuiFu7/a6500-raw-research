// Dump instructions and defined data in an address range. Usage (headless):
//   -postScript GhidraDumpRange.java 005016b0 005017f0 out range.txt
// @category A6500

import java.io.FileWriter;
import java.io.PrintWriter;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;

public class GhidraDumpRange extends GhidraScript {

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
        if (start < 0 || end < 0) {
            println("usage: start end [out path]");
            return;
        }

        Address startAddress = toAddr(start);
        Address endAddress = toAddr(end);
        StringBuilder out = new StringBuilder();

        out.append("RANGE ").append(startAddress).append('-')
                .append(endAddress).append('\n');

        DataIterator data = currentProgram.getListing()
                .getDefinedData(startAddress, true);
        while (data.hasNext()) {
            Data item = data.next();
            if (item.getAddress().compareTo(endAddress) > 0) {
                break;
            }
            out.append("DATA ").append(item.getAddress()).append("  ")
                    .append(item).append('\n');
        }

        InstructionIterator instructions = currentProgram.getListing()
                .getInstructions(startAddress, true);
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            if (instruction.getAddress().compareTo(endAddress) > 0) {
                break;
            }
            out.append(instruction.getAddress()).append("  ")
                    .append(instruction).append('\n');
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
