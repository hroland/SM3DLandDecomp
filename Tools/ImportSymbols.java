// Import upstream EU names without changing user-reviewed functions or boundaries.
// @category RedPepper
import ghidra.app.script.GhidraScript;
import ghidra.program.model.symbol.SourceType;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.stream.Stream;

public class ImportSymbols extends GhidraScript {
    @Override
    public void run() throws Exception {
        Path root = Path.of(getScriptArgs()[0]);
        int names = 0;
        try (Stream<Path> paths = Files.walk(root)) {
            for (Path file : paths.filter(p -> p.toString().endsWith(".sym")).sorted().toList()) {
                for (String line : Files.readAllLines(file)) {
                    monitor.checkCancelled();
                    String[] row = line.split(",", -1);
                    if (row.length < 4 || row[0].isEmpty()) continue;
                    var address = toAddr(Long.parseUnsignedLong(row[1], 16));
                    var function = getFunctionAt(address);
                    if (function != null &&
                            (function.getSymbol().getSource() == SourceType.DEFAULT ||
                             function.getSymbol().getSource() == SourceType.ANALYSIS)) {
                        function.setName(row[0], SourceType.IMPORTED);
                    } else if (currentProgram.getSymbolTable().getSymbols(address).length == 0) {
                        createLabel(address, row[0], false, SourceType.IMPORTED);
                    }
                    names++;
                }
            }
        }
        println("Imported EU symbol references: " + names + "; existing reviewed names preserved.");
    }
}
