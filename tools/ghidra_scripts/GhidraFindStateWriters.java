// Find stores to a fixed object offset and show the preceding instruction context.
// Usage: -postScript GhidraFindStateWriters.java 1f0 out hits.txt
// @category A6500

import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;

public class GhidraFindStateWriters extends GhidraScript {

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

        List<String> needles = new ArrayList<>();
        for (String offset : offsets) {
            needles.add("#0x" + offset.toLowerCase());
        }

        StringBuilder out = new StringBuilder();
        Deque<Instruction> recent = new ArrayDeque<>();
        Listing listing = currentProgram.getListing();
        InstructionIterator instructions = listing.getInstructions(true);
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            String text = instruction.toString().toLowerCase();
            boolean store = instruction.getMnemonicString().toLowerCase().startsWith("str");
            boolean hit = false;
            for (String needle : needles) {
                if (text.contains(needle)) {
                    hit = true;
                    break;
                }
            }
            if (store && hit) {
                Address address = instruction.getAddress();
                Function function = currentProgram.getFunctionManager()
                        .getFunctionContaining(address);
                out.append("STORE ").append(address).append(" ")
                        .append(instruction).append(" function=")
                        .append(function == null ? "" : function.getName()).append('\n');
                for (Instruction prior : recent) {
                    out.append("  PREV ").append(prior).append('\n');
                }
                out.append('\n');
            }
            recent.addLast(instruction);
            if (recent.size() > 8) {
                recent.removeFirst();
            }
        }

        if (outPath != null) {
            try (PrintWriter writer = new PrintWriter(new FileWriter(outPath))) {
                writer.print(out.toString());
            }
        }
    }
}
