// Dump listing and decompilation for the functions containing the given
// addresses. Usage (headless):
//   -postScript GhidraDumpFunctions.java 005050c4 005016f0 out out.txt
// @category A6500

import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.List;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;

public class GhidraDumpFunctions extends GhidraScript {

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        List<Long> addresses = new ArrayList<>();
        String outPath = null;
        for (int i = 0; i < args.length; i++) {
            if (args[i].equals("out") && i + 1 < args.length) {
                outPath = args[++i];
            }
            else {
                addresses.add(Long.parseLong(args[i], 16));
            }
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);

        StringBuilder out = new StringBuilder();
        for (Long value : addresses) {
            Address address = toAddr(value);
            Function function = currentProgram.getFunctionManager()
                    .getFunctionContaining(address);
            out.append("ADDRESS ").append(address).append('\n');
            if (function == null) {
                out.append("NO FUNCTION\n\n");
                continue;
            }
            out.append("FUNCTION ").append(function.getName())
                    .append(" entry=").append(function.getEntryPoint())
                    .append(" body=").append(function.getBody()).append('\n');

            out.append("CALLERS\n");
            for (Object ref : getReferencesTo(function.getEntryPoint())) {
                out.append("  ").append(ref).append('\n');
            }

            out.append("LISTING\n");
            InstructionIterator instructions = currentProgram.getListing()
                    .getInstructions(function.getBody(), true);
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                out.append(instruction.getAddress()).append("  ")
                        .append(instruction).append('\n');
            }

            out.append("DECOMPILED\n");
            DecompileResults results = decompiler.decompileFunction(
                    function, 60, monitor);
            if (results != null && results.decompileCompleted()) {
                out.append(results.getDecompiledFunction().getC()).append('\n');
            }
            else {
                out.append("decompile failed\n");
            }
            out.append('\n');
        }
        decompiler.dispose();

        if (outPath == null) {
            println(out.toString());
        }
        else {
            try (PrintWriter writer = new PrintWriter(new FileWriter(outPath))) {
                writer.print(out.toString());
            }
        }
        println("Dumped " + addresses.size() + " functions");
    }
}
