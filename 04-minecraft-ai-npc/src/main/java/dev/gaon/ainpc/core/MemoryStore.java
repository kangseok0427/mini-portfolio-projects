package dev.gaon.ainpc.core;
import com.google.gson.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.io.IOException;
import java.util.*;
public final class MemoryStore {
    public record Snapshot(long revision, List<Message> history) {}
    private final Path file;
    private final int maxMessages, maxConversations;
    private final LinkedHashMap<String, List<Message>> conversations = new LinkedHashMap<>(16, .75f, true);
    private final Map<String, Long> revisions = new HashMap<>();
    private final Object diskLock = new Object();
    public MemoryStore(Path file, int turns, int maxConversations) throws IOException {
        this.file = file; this.maxMessages = Math.max(1, turns) * 2; this.maxConversations = Math.max(1, maxConversations);
        if (Files.exists(file)) {
            try {
                JsonObject data = JsonParser.parseString(Files.readString(file)).getAsJsonObject();
                for (var entry : data.entrySet()) {
                    List<Message> list = new ArrayList<>();
                    for (var value : entry.getValue().getAsJsonArray()) {
                        JsonObject m = value.getAsJsonObject(); String role = m.get("role").getAsString(), text = m.get("content").getAsString();
                        if (List.of("user", "assistant").contains(role)) list.add(new Message(role, text));
                    }
                    conversations.put(entry.getKey(), trim(list));
                }
                evict();
            } catch (RuntimeException e) { throw new IOException("Invalid memory JSON; restore a backup or rename memory.json", e); }
        }
    }
    private String key(UUID player, String npc) { return player + ":" + npc; }
    public synchronized Snapshot snapshot(UUID player, String npc) {
        return new Snapshot(revisions.getOrDefault(npc, 0L), List.copyOf(conversations.getOrDefault(key(player, npc), List.of())));
    }
    public synchronized boolean commit(UUID player, String npc, long expectedRevision, String question, String answer) {
        if (expectedRevision != revisions.getOrDefault(npc, 0L)) return false;
        List<Message> next = new ArrayList<>(conversations.getOrDefault(key(player, npc), List.of()));
        next.add(new Message("user", question)); next.add(new Message("assistant", answer));
        conversations.put(key(player, npc), trim(next)); evict(); return true;
    }
    public synchronized void clearNpc(String npc) {
        conversations.keySet().removeIf(k -> k.endsWith(":" + npc)); revisions.merge(npc, 1L, Long::sum);
    }
    private List<Message> trim(List<Message> list) { return new ArrayList<>(list.subList(Math.max(0, list.size() - maxMessages), list.size())); }
    private void evict() { while (conversations.size() > maxConversations) conversations.remove(conversations.keySet().iterator().next()); }
    public void save() throws IOException {
        synchronized (diskLock) {
            String json;
            synchronized (this) { json = new GsonBuilder().setPrettyPrinting().create().toJson(conversations); }
            Files.createDirectories(file.toAbsolutePath().getParent()); Path tmp = file.resolveSibling(file.getFileName() + ".tmp");
            Files.writeString(tmp, json, StandardCharsets.UTF_8);
            try { Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE); }
            catch (AtomicMoveNotSupportedException e) { Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING); }
        }
    }
}
