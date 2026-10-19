// Record reviewed EU layouts and initialization order without splitting a shared tail.
// @category RedPepper
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.program.model.data.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.SourceType;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import com.google.gson.*;

public class ReviewNerveRegistration extends GhidraScript {
    private static final String SHA = "e1d7e188ff88467df776c17cec45c44857fadf5b699944baa8cddcae7d939e64";
    private static final CategoryPath CATEGORY = new CategoryPath("/RedPepper/EU/Reviewed");

    private String hash(byte[] data) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(data));
    }

    private PointerDataType ptr(DataType type) {
        return new PointerDataType(type, 4, currentProgram.getDataTypeManager());
    }

    private StructureDataType structure(String name) {
        return new StructureDataType(CATEGORY, name, 0);
    }

    private void comment(long offset, String text) {
        var address = toAddr(offset);
        String old = currentProgram.getListing().getComment(CodeUnit.PLATE_COMMENT, address);
        if (old == null || !old.contains(text)) {
            currentProgram.getListing().setComment(address, CodeUnit.PLATE_COMMENT,
                old == null ? text : old + "\n\n" + text);
        }
    }

    @Override
    public void run() throws Exception {
        Path root = Path.of(getScriptArgs()[0]);
        JsonObject evidence = JsonParser.parseString(
            Files.readString(root.resolve("Build/headless/verification.json"))).getAsJsonObject();
        if (!evidence.get("passed").getAsBoolean() ||
                !evidence.get("code_sha256").getAsString().equals(SHA)) {
            throw new IllegalStateException("Passing EU differential evidence is required.");
        }
        for (var entry : evidence.getAsJsonObject("artifacts_sha256").entrySet()) {
            if (!hash(Files.readAllBytes(root.resolve(entry.getKey()))).equals(entry.getValue().getAsString())) {
                throw new IllegalStateException("Verification artifact changed: " + entry.getKey());
            }
        }
        byte[] code = Files.readAllBytes(root.resolve("code.bin"));
        if (!hash(code).equals(SHA)) throw new IllegalStateException("Wrong EU executable.");
        JsonObject input = JsonParser.parseString(
            Files.readString(root.resolve(".local/analysis/input.json"))).getAsJsonObject();
        for (JsonElement element : input.getAsJsonArray("sections")) {
            JsonObject section = element.getAsJsonObject();
            if (section.get("offset").isJsonNull()) continue;
            int length = section.get("size").getAsInt();
            int offset = section.get("offset").getAsInt();
            byte[] original = java.util.Arrays.copyOfRange(code, offset, offset + length);
            byte[] imported = new byte[length];
            currentProgram.getMemory().getBytes(toAddr(section.get("address").getAsLong()), imported);
            if (!java.util.Arrays.equals(original, imported)) {
                throw new IllegalStateException("Ghidra memory differs from stock: " + section.get("name"));
            }
        }

        var host = structure("IUseNerve");
        var keeper = structure("NerveKeeper");
        var ctrl = structure("NerveStateCtrl");
        var state = structure("NerveStateBase");
        var entry = structure("NerveStateEntry");
        var hostVT = structure("IUseNerveVTable");
        var stateVT = structure("NerveStateBaseVTable");

        var getter = new FunctionDefinitionDataType(CATEGORY, "getNerveKeeper");
        getter.setReturnType(ptr(keeper));
        getter.setArguments(new ParameterDefinition[] {
            new ParameterDefinitionImpl("host", ptr(host), null)});
        var initializer = new FunctionDefinitionDataType(CATEGORY, "initState");
        initializer.setReturnType(VoidDataType.dataType);
        initializer.setArguments(new ParameterDefinition[] {
            new ParameterDefinitionImpl("state", ptr(state), null)});

        hostVT.add(ptr(getter), "getNerveKeeper", "Virtual slot 0");
        host.add(ptr(hostVT), "vtable", null);
        stateVT.add(ptr(getter), "getNerveKeeper", null);
        stateVT.add(ptr(VoidDataType.dataType), "destructor", null);
        stateVT.add(ptr(VoidDataType.dataType), "deletingDestructor", null);
        stateVT.add(ptr(initializer), "init", "Virtual slot at +0x0c");
        state.add(ptr(stateVT), "vtable", null);
        state.add(ptr(keeper), "keeper", null);
        state.add(BooleanDataType.dataType, "isDead", null);
        state.add(new ArrayDataType(Undefined1DataType.dataType, 3, 1), "padding", null);
        entry.add(ptr(state), "state", null);
        entry.add(ptr(VoidDataType.dataType), "nerve", null);
        entry.add(ptr(CharDataType.dataType), "name", null);
        ctrl.add(IntegerDataType.dataType, "capacity", null);
        ctrl.add(IntegerDataType.dataType, "count", null);
        ctrl.add(ptr(entry), "states", null);
        ctrl.add(ptr(entry), "current", null);
        keeper.add(ptr(host), "host", null);
        keeper.add(ptr(VoidDataType.dataType), "active", null);
        keeper.add(ptr(VoidDataType.dataType), "pending", null);
        keeper.add(IntegerDataType.dataType, "step", null);
        keeper.add(ptr(ctrl), "stateCtrl", null);
        keeper.add(ptr(VoidDataType.dataType), "actionCtrl", null);
        if (host.getLength() != 4 || keeper.getLength() != 24 || ctrl.getLength() != 16 ||
                state.getLength() != 12 || entry.getLength() != 12) {
            throw new IllegalStateException("Unexpected ARM32 layout sizes.");
        }
        var manager = currentProgram.getDataTypeManager();
        DataType reviewedHost = manager.resolve(host, DataTypeConflictHandler.KEEP_HANDLER);
        DataType reviewedState = manager.resolve(state, DataTypeConflictHandler.KEEP_HANDLER);

        Function function = getFunctionAt(toAddr(0x001cacb4));
        if (function == null) throw new IllegalStateException("Missing initializer function.");
        if (function.getSignatureSource() == SourceType.USER_DEFINED) {
            throw new IllegalStateException("Initializer already has a reviewed signature; preserve it.");
        }
        function.setName("_ZN2al14initNerveStateEPNS_9IUseNerveEPNS_14NerveStateBaseEPKNS_5NerveEPKc",
                         SourceType.USER_DEFINED);
        function.setReturnType(VoidDataType.dataType, SourceType.USER_DEFINED);
        function.replaceParameters(Function.FunctionUpdateType.DYNAMIC_STORAGE_ALL_PARAMS, true,
            SourceType.USER_DEFINED,
            new ParameterImpl("host", ptr(reviewedHost), currentProgram),
            new ParameterImpl("state", ptr(reviewedState), currentProgram),
            new ParameterImpl("nerve", ptr(VoidDataType.dataType), currentProgram),
            new ParameterImpl("name", ptr(CharDataType.dataType), currentProgram));

        String note = "EU state registration review: invoke state.init(), then fetch host's keeper/controller, " +
            "then append state/nerve/name and increment count. Original initializer falls through into " +
            "shared tail 0x001cad00..0x001cad2c. Behavior-tested GCC source; no byte match claimed.";
        comment(0x001cacb4, note);
        if (currentProgram.getSymbolTable().getSymbols(toAddr(0x001cad00)).length == 0) {
            createLabel(toAddr(0x001cad00), "NerveStateCtrl_registerState_shared_tail_descriptive",
                        false, SourceType.USER_DEFINED);
        }
        comment(0x001cad00, "Shared registration tail; registerState is a descriptive name. " +
            "Keep the overlapping initializer body intact.");

        Path out = root.resolve(".local/analysis/reviewed");
        Files.createDirectories(out);
        DecompInterface decompiler = new DecompInterface();
        try {
            if (!decompiler.openProgram(currentProgram)) throw new IllegalStateException(decompiler.getLastMessage());
            var result = decompiler.decompileFunction(function, 60, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                throw new IllegalStateException(result.getErrorMessage());
            }
            Files.writeString(out.resolve("001cacb4.c"),
                "/* Typed Ghidra output. The recovered source is separately verified; this output is not a byte match. */\n" +
                result.getDecompiledFunction().getC());
        } finally {
            decompiler.dispose();
        }
        JsonObject report = new JsonObject();
        report.addProperty("code_sha256", SHA);
        report.addProperty("verification_sha256", hash(Files.readAllBytes(root.resolve("Build/headless/verification.json"))));
        report.addProperty("script_sha256", hash(Files.readAllBytes(root.resolve("Tools/ReviewNerveRegistration.java"))));
        report.addProperty("typed_initializer", "0x001cacb4");
        report.addProperty("shared_tail_preserved", true);
        report.addProperty("byte_matching", false);
        Files.writeString(out.resolve("nerve-registration.json"), new GsonBuilder().setPrettyPrinting().create().toJson(report) + "\n");
        println("Reviewed EU state initializer; shared tail preserved and typed output exported.");
    }
}
