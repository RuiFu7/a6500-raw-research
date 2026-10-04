// List functions whose name contains the given substring. Usage:
//   -postScript GhidraListFunctions.java DualRec
// @category A6500

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;

public class GhidraListFunctions extends GhidraScript {

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String filter = args.length == 0 ? "" : args[0];
        FunctionIterator functions = currentProgram.getFunctionManager()
                .getFunctions(true);
        int count = 0;
        while (functions.hasNext()) {
            Function function = functions.next();
            if (filter.isEmpty() || function.getName().contains(filter)) {
                println(function.getEntryPoint() + "  " + function.getName());
                count++;
            }
        }
        println("Total matched: " + count);
    }
}
