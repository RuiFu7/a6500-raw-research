// Find Thumb PIC ldr+add rN,pc references inside analyzed functions.
// Usage: -postScript GhidraFindPcAddRef.java 909fe9 90a04c out hits.txt
// @category A6500

import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;

public class GhidraFindPcAddRef extends GhidraScript {

    private static class LdrInfo {
        final long literal;
        final long value;

        LdrInfo(long literal, long value) {
            this.literal = literal;
            this.value = value;
        }
    }

    private static final Pattern HEX = Pattern.compile("0x([0-9a-fA-F]+)");
    private final Set<Long> targets = new HashSet<>();

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
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
        Map<String, LdrInfo> lastLdr = new HashMap<>();
        Map<String, Long> movwLow = new HashMap<>();
        StringBuilder out = new StringBuilder();
        long counter = 0;

        InstructionIterator instructions = listing.getInstructions(true);
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            counter++;
            if (counter % 16 == 0) {
                lastLdr.clear();
                movwLow.clear();
            }

            String mnemonic = instruction.getMnemonicString();
            if (mnemonic.equals("movw") || mnemonic.equals("movt")) {
                String destination = operand(instruction, 0);
                Matcher matcher = HEX.matcher(operand(instruction, 1));
                if (!matcher.find()) {
                    continue;
                }
                long immediate = Long.parseLong(matcher.group(1), 16);
                long target;
                if (mnemonic.equals("movw")) {
                    movwLow.put(destination, immediate);
                    continue;
                }
                Long low = movwLow.get(destination);
                if (low == null) {
                    continue;
                }
                target = (low & 0xffffL) | (immediate << 16);
                record(instruction, target, "movw/movt", out);
            }
            else if (mnemonic.startsWith("adr")) {
                Matcher matcher = HEX.matcher(operand(instruction, 1));
                if (matcher.find()) {
                    long target = Long.parseLong(matcher.group(1), 16);
                    record(instruction, target, "adr", out);
                }
            }
            else if (mnemonic.startsWith("ldr")) {
                String destination = operand(instruction, 0);
                String source = operand(instruction, 1);
                Matcher matcher = HEX.matcher(source);
                if (matcher.find()) {
                    long displacement = Long.parseLong(matcher.group(1), 16);
                    long literalAddress;
                    if (source.contains("pc")) {
                        long pc = (instruction.getAddress().getOffset() + 4) & ~3L;
                        literalAddress = pc + displacement;
                    }
                    else {
                        literalAddress = displacement;
                    }
                    try {
                        int value = getInt(toAddr(literalAddress));
                        lastLdr.put(destination,
                                new LdrInfo(literalAddress, value & 0xffffffffL));
                    }
                    catch (Exception e) {
                        // literal outside mapped memory
                    }
                }
            }
            else if (mnemonic.equals("add") && operand(instruction, 1).equals("pc")) {
                String destination = operand(instruction, 0);
                LdrInfo info = lastLdr.get(destination);
                if (info == null) {
                    continue;
                }
                long base = instruction.getAddress().getOffset() + 4;
                long target = (info.value + base) & 0xffffffffL;
                record(instruction, target, "ldr+add literal="
                        + Long.toHexString(info.literal), out);
            }
        }

        if (outPath != null) {
            try (PrintWriter writer = new PrintWriter(new FileWriter(outPath))) {
                writer.print(out.toString());
            }
        }
    }

    private void record(Instruction instruction, long target, String kind,
            StringBuilder out) {
        if (!targets.contains(target)) {
            return;
        }
        Address address = instruction.getAddress();
        Function function = currentProgram.getFunctionManager()
                .getFunctionContaining(address);
        String line = address + " target=" + Long.toHexString(target)
                + " kind=" + kind
                + " function=" + (function == null ? "" : function.getName());
        println(line);
        out.append(line).append('\n');
    }

    private String operand(Instruction instruction, int index) {
        String text = instruction.getDefaultOperandRepresentation(index);
        int comma = text.indexOf(',');
        return (comma < 0 ? text : text.substring(0, comma)).trim();
    }
}
