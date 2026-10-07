package dev.gaon.ainpc;
import org.bukkit.Location;
import java.util.UUID;
final class Npc {
    final String id;
    String name, personality;
    boolean memory;
    final Location location;
    UUID entity;
    Npc(String id, String name, String personality, boolean memory, Location location, UUID entity) {
        this.id=id; this.name=name; this.personality=personality; this.memory=memory; this.location=location; this.entity=entity;
    }
}
