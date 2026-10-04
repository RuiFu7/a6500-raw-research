// Search defined string data and raw memory for target strings, then report
// cross-references from code. Usage (headless):
//   -postScript GhidraXrefSearch.java "SET_RAW_EXTERNAL_OUTPUT" out=firmware/manifests/ghidra_xrefs.tsv
// @category A6500

import java.io.FileWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.StringDataInstance;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;

public class GhidraXrefSearch extends GhidraScript {

    private final List<List<String>> rows = new ArrayList<>();
    private final Set<String> seen = new HashSet<>();

    @Override
    public void run() throws Exception {
        List<String> targets = new ArrayList<>();
        String outPath = null;
        String[] args = getScriptArgs();
        for (int i = 0; i < args.length; i++) {
            String arg = args[i];
            if (arg.equals("out") && i + 1 < args.length) {
                outPath = args[++i];
            }
            else {
                targets.add(arg);
            }
        }
        if (targets.isEmpty()) {
            println("No search strings provided");
            return;
        }

        Listing listing = currentProgram.getListing();
        for (Data data : listing.getDefinedData(true)) {
            if (!data.hasStringValue()) {
                continue;
            }
            String text = stringText(data);
            if (text == null) {
                continue;
            }
            for (String target : targets) {
                if (text.contains(target)) {
                    record(data.getAddress(), target, text);
                }
            }
        }

        Memory memory = currentProgram.getMemory();
        for (MemoryBlock block : memory.getBlocks()) {
            if (!block.isInitialized()) {
                continue;
            }
            byte[] bytes = new byte[(int) block.getSize()];
            block.getBytes(block.getStart(), bytes);
            String blob = new String(bytes, StandardCharsets.ISO_8859_1);
            for (String target : targets) {
                int index = blob.indexOf(target);
                while (index >= 0) {
                    int end = Math.min(index + 200, blob.length());
                    Address address = block.getStart().add(index);
                    record(address, target, blob.substring(index, end));
                    index = blob.indexOf(target, index + 1);
                }
            }
        }

        PrintWriter writer = outPath == null
                ? null
                : new PrintWriter(new FileWriter(outPath));
        if (writer != null) {
            writer.println(
                "target\tstring_address\tstring\tfrom\tref_type\tfunction\tfunction_addr");
        }
        println("Matched strings: " + rows.size());
        for (List<String> row : rows) {
            String line = String.join("\t", row);
            println(line);
            if (writer != null) {
                writer.println(line);
            }
        }
        if (writer != null) {
            writer.close();
        }
    }

    private String stringText(Data data) {
        try {
            Object value = data.getValue();
            if (value instanceof StringDataInstance) {
                return ((StringDataInstance) value).getStringValue();
            }
            return String.valueOf(value);
        }
        catch (Exception e) {
            return null;
        }
    }

    private void record(Address address, String target, String text) {
        String key = address + "|" + target;
        if (!seen.add(key)) {
            return;
        }

        List<String> base = new ArrayList<>();
        base.add(target);
        base.add(address.toString());
        base.add(text);

        Reference[] refs = getReferencesTo(address);
        if (refs.length == 0) {
            List<String> row = new ArrayList<>(base);
            for (int i = 0; i < 4; i++) {
                row.add("");
            }
            rows.add(row);
            return;
        }

        for (Reference ref : refs) {
            Address fromAddress = ref.getFromAddress();
            Function function = currentProgram.getFunctionManager()
                    .getFunctionContaining(fromAddress);
            List<String> row = new ArrayList<>(base);
            row.add(fromAddress.toString());
            row.add(ref.getReferenceType().toString());
            row.add(function == null ? "" : function.getName());
            row.add(function == null ? "" : function.getEntryPoint().toString());
            rows.add(row);
        }
    }
}
