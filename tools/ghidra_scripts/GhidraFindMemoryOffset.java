// Find instructions that reference a numeric memory/operand offset.
// Usage: -postScript GhidraFindMemoryOffset.java 1f0 out hits.txt
// @category A6500

import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.address.Address;

public class GhidraFindMemoryOffset extends GhidraScript {

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        List<String> offsets = new ArrayList<>();
        String outPath = null;
        for (int i = 0; i < args.length; i++) {
            if (args[i].equals("out") && i + 1 < args.length) {
                outPath = args[++i];
            }
            else {
                offsets.add(args[i]);
            }
        }
        if (offsets.isEmpty()) {
            println("usage: offset ... out path");
            return;
        }

        StringBuilder out = new StringBuilder();
        Listing listing = currentProgram.getListing();
        InstructionIterator instructions = listing.getInstructions(true);
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            String text = instruction.toString();
            for (String offset : offsets) {
                String needle = "#0x" + offset.toLowerCase();
                if (!text.toLowerCase().contains(needle)) {
                    continue;
                }
                Address address = instruction.getAddress();
                Function function = currentProgram.getFunctionManager()
                        .getFunctionContaining(address);
                String line = address + " offset=0x" + offset + " "
                        + instruction + " function="
                        + (function == null ? "" : function.getName());
                println(line);
                out.append(line).append('\n');
                break;
            }
        }

        if (outPath != null) {
            try (PrintWriter writer = new PrintWriter(new FileWriter(outPath))) {
                writer.print(out.toString());
            }
        }
    }
}
