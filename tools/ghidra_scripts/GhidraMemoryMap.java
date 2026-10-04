// Print the current program's memory map.  Usage:
//   -postScript GhidraMemoryMap.java [addr1 addr2 ...]
// @category A6500

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;

public class GhidraMemoryMap extends GhidraScript {

    @Override
    public void run() throws Exception {
        println("PROGRAM " + currentProgram.getName());
        Memory memory = currentProgram.getMemory();
        for (MemoryBlock block : memory.getBlocks()) {
            println(String.format("BLOCK %s %s-%s perms=%s%s%s size=%d",
                    block.getName(),
                    block.getStart(), block.getEnd(),
                    block.isRead() ? "r" : "-",
                    block.isWrite() ? "w" : "-",
                    block.isExecute() ? "x" : "-",
                    block.getSize()));
        }
        FunctionManager functions = currentProgram.getFunctionManager();
        for (String arg : getScriptArgs()) {
            long value = Long.parseLong(arg, 16);
            Address address = toAddr(value);
            Function function = functions.getFunctionContaining(address);
            println("ADDR " + address
                    + (function == null ? "" : " fn=" + function.getName()
                    + "@" + function.getEntryPoint()));
        }
    }
}
