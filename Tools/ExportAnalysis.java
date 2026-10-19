// Export automatic analysis separately from reviewed, rebuild-verified source.
// @category Decomp
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.address.AddressRange;
import ghidra.program.model.address.AddressRangeIterator;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.mem.MemoryBlock;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.charset.StandardCharsets;
import java.io.BufferedWriter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.Map;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

public class ExportAnalysis extends GhidraScript {
    public void run() throws Exception {
        var info = currentProgram.getOptions("Program Information");
        if (info.contains("CRO analysis warning") && !info.getBoolean("CRO names complete", false)) {
            throw new IllegalStateException("CRO pre-analysis did not complete; refusing export.");
        }
        Path out = Path.of(getScriptArgs()[0]);
        Files.createDirectories(out.resolve("pseudocode"));
        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleSyntaxTree(false);
        decompiler.toggleCCode(true);
        if (!decompiler.openProgram(currentProgram)) {
            throw new IllegalStateException(decompiler.getLastMessage());
        }
        Gson gson = new Gson();
        int count = 0, success = 0;
        AddressSet covered = new AddressSet();
        try (BufferedWriter index = Files.newBufferedWriter(out.resolve("functions.jsonl"))) {
            FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
            while (functions.hasNext() && !monitor.isCancelled()) {
                Function f = functions.next();
                if (f.isExternal()) continue;
                long address = f.getEntryPoint().getOffset();
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("address", address);
                row.put("name", f.getName());
                row.put("signature", f.getPrototypeString(false, true));
                row.put("size", f.getBody().getNumAddresses());
                ArrayList<long[]> chunks = new ArrayList<>();
                AddressRangeIterator ranges = f.getBody().getAddressRanges();
                while (ranges.hasNext()) {
                    AddressRange range = ranges.next();
                    chunks.add(new long[]{range.getMinAddress().getOffset(),
                                          range.getMaxAddress().getOffset() + 1});
                }
                row.put("chunks", chunks);
                covered.add(f.getBody());
                ArrayList<Long> calls = new ArrayList<>();
                for (Function target : f.getCalledFunctions(monitor)) {
                    calls.add(target.getEntryPoint().getOffset());
                }
                row.put("calls", calls);
                DecompileResults result = decompiler.decompileFunction(f, 30, monitor);
                if (result.decompileCompleted() && result.getDecompiledFunction() != null) {
                    String filename = String.format("pseudocode/%08x.c", address);
                    Files.writeString(out.resolve(filename),
                        "/* Machine output. Not rebuild-verified source. */\n" +
                        result.getDecompiledFunction().getC(), StandardCharsets.UTF_8);
                    row.put("pseudocode", filename);
                    row.put("status", "machine-pseudocode-unreviewed");
                    success++;
                } else {
                    row.put("status", "decompile-failed");
                    row.put("error", result.getErrorMessage());
                }
                index.write(gson.toJson(row));
                index.newLine();
                if (++count % 250 == 0) {
                    index.flush();
                    println("Exported " + count + " functions");
                }
            }
        } finally {
            decompiler.dispose();
        }
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("functions", count);
        summary.put("pseudocode", success);
        summary.put("failed", count - success);
        summary.put("discovered_function_body_bytes", covered.getNumAddresses());
        long executableBytes = 0;
        for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            if (block.isExecute()) executableBytes += block.getSize();
        }
        summary.put("executable_section_bytes_including_literals", executableBytes);
        summary.put("verified_recompiled_functions", 0);
        summary.put("complete", false);
        summary.put("interrupted", monitor.isCancelled());
        if (info.contains("CRO analysis warning")) {
            summary.put("cro_analysis_warning", info.getString("CRO analysis warning", ""));
            summary.put("cro_source_sha256", info.getString("CRO source SHA256", ""));
            summary.put("import_names_complete", info.getBoolean("CRO names complete", false));
        }
        summary.put("warning", "Automatic discovery may miss functions or mistake data for code; pseudocode is not a complete decompilation.");
        Files.writeString(out.resolve("summary.json"),
            new GsonBuilder().setPrettyPrinting().create().toJson(summary) + "\n");
        println(gson.toJson(summary));
    }
}
