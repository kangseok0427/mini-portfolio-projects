package dev.gaon.ainpc.core;
import java.nio.file.Files;
import java.util.UUID;
/** Executes the real dialogue/memory core without pretending to be a Minecraft client. */
public final class DemoConsole {
    public static void main(String[] args) throws Exception {
        if(args.length!=1||!args[0].equals("--demo")) { System.out.println("Install this JAR in Paper plugins/, or run with --demo for a scripted core demonstration.");return; }
        var folder=Files.createTempDirectory("ainpc-demo-");var file=folder.resolve("memory.json");
        try {
            MemoryStore memory=new MemoryStore(file,6,500);DialogueProvider provider=new DemoProvider();
            UUID alice=UUID.nameUUIDFromBytes("alice".getBytes()),bob=UUID.nameUUIDFromBytes("bob".getBytes());
            System.out.println(provider.label()+" | Java dialogue core; not in-game footage");
            turn(memory,provider,alice,"merchant","철 어디서 구해?");turn(memory,provider,alice,"merchant","내가 아까 뭐 찾는다고 했지?");
            turn(memory,provider,bob,"merchant","내가 아까 뭐 찾는다고 했지?");turn(memory,provider,alice,"guide","내가 아까 뭐 찾는다고 했지?");
            memory.save();System.out.println("Restart persistence: "+new MemoryStore(file,6,500).snapshot(alice,"merchant").history().size()+" messages");
            memory.clearNpc("merchant");System.out.println("After memory clear: "+memory.snapshot(alice,"merchant").history().size()+" messages");
        } finally {Files.deleteIfExists(file);Files.deleteIfExists(folder);}
    }
    private static void turn(MemoryStore memory,DialogueProvider provider,UUID player,String npc,String question) throws Exception {
        var snapshot=memory.snapshot(player,npc);String answer=provider.reply(npc,snapshot.history(),question);
        memory.commit(player,npc,snapshot.revision(),question,answer);
        System.out.println("Player "+player.toString().substring(0,8)+" -> "+npc+": "+question);System.out.println(npc+": "+answer);
    }
}
