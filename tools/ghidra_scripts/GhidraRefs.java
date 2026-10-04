// Print incoming and outgoing references for the given addresses. Usage:
//   -postScript GhidraRefs.java 005050c4 005016c4 out refs.txt
// @category A6500

import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.List;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

public class GhidraRefs extends GhidraScript {

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

        StringBuilder out = new StringBuilder();
        for (Long value : addresses) {
            Address address = toAddr(value);
            out.append("ADDRESS ").append(address).append('\n');

            out.append("TO ").append(address).append('\n');
            for (Reference ref : getReferencesTo(address)) {
                out.append(formatRef(ref)).append('\n');
            }

            out.append("FROM ").append(address).append('\n');
            for (Reference ref : getReferencesFrom(address)) {
                out.append(formatRef(ref)).append('\n');
            }
            out.append('\n');
        }

        if (outPath == null) {
            println(out.toString());
        }
        else {
            try (PrintWriter writer = new PrintWriter(new FileWriter(outPath))) {
                writer.print(out.toString());
            }
        }
        println("Dumped references for " + addresses.size() + " addresses");
    }

    private String formatRef(Reference ref) {
        Address fromAddress = ref.getFromAddress();
        Function function = currentProgram.getFunctionManager()
                .getFunctionContaining(fromAddress);
        String functionName = function == null
                ? ""
                : function.getName() + ":" + function.getEntryPoint();
        return "  " + fromAddress + " -> " + ref.getToAddress()
                + " type=" + ref.getReferenceType()
                + " op=" + ref.getOperandIndex()
                + " fn=" + functionName;
    }
}
