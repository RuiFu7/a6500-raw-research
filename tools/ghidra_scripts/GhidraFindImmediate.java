// Find instructions with the given scalar immediate operands.
// Usage: -postScript GhidraFindImmediate.java 9ac4 9ac5 out hits.txt
// @category A6500

import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.HashSet;
import java.util.Set;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.scalar.Scalar;

public class GhidraFindImmediate extends GhidraScript {

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        Set<Long> targets = new HashSet<>();
        String outPath = null;
        for (int i = 0; i < args.length; i++) {
            if (args[i].equals("out") && i + 1 < args.length) {
                outPath = args[++i];
            }
            else {
                targets.add(Long.parseLong(args[i], 16));
            }
        }

        Listing listing = currentProgram.getListing();
        StringBuilder out = new StringBuilder();
        InstructionIterator instructions = listing.getInstructions(true);
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            for (int i = 0; i < instruction.getNumOperands(); i++) {
                Object[] objects = instruction.getOpObjects(i);
                for (Object object : objects) {
                    if (!(object instanceof Scalar)) {
                        continue;
                    }
                    long value = ((Scalar) object).getValue() & 0xffffffffL;
                    if (!targets.contains(value)) {
                        continue;
                    }
                    Function function = currentProgram.getFunctionManager()
                            .getFunctionContaining(instruction.getAddress());
                    String line = instruction.getAddress() + " imm="
                            + Long.toHexString(value) + " " + instruction
                            + " function=" + (function == null ? "" : function.getName());
                    println(line);
                    out.append(line).append('\n');
                }
            }
        }

        if (outPath != null) {
            try (PrintWriter writer = new PrintWriter(new FileWriter(outPath))) {
                writer.print(out.toString());
            }
        }
    }
}
