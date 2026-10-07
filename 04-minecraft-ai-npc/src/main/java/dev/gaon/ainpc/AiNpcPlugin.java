package dev.gaon.ainpc;

import dev.gaon.ainpc.core.*;
import io.papermc.paper.event.player.AsyncChatEvent;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import net.kyori.adventure.text.event.ClickEvent;
import net.kyori.adventure.text.serializer.plain.PlainTextComponentSerializer;
import org.bukkit.*;
import org.bukkit.command.*;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.entity.*;
import org.bukkit.event.*;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.event.player.*;
import org.bukkit.persistence.PersistentDataType;
import org.bukkit.plugin.java.JavaPlugin;

import java.io.File;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;
import java.util.logging.Level;

public final class AiNpcPlugin extends JavaPlugin implements Listener, CommandExecutor, TabCompleter {
    private final Map<String,Npc> npcs = new LinkedHashMap<>(); // Main thread only.
    private final ConcurrentMap<UUID,String> selected = new ConcurrentHashMap<>(); // Async chat reads this.
    private final Set<UUID> busy = ConcurrentHashMap.newKeySet();
    private final Map<UUID,Long> lastRequest = new HashMap<>();
    private final AtomicLong generation = new AtomicLong();
    private ThreadPoolExecutor workers;
    private MemoryStore memory;
    private DialogueProvider provider;
    private NamespacedKey npcKey;
    private boolean registryReady;
    private final Set<String> removedIds = new HashSet<>();

    @Override public void onEnable() {
        saveDefaultConfig(); npcKey = new NamespacedKey(this,"npc_id");
        workers = new ThreadPoolExecutor(2,2,0,TimeUnit.SECONDS,new ArrayBlockingQueue<>(16),
            r -> { Thread t = new Thread(r,"gaon-ainpc-api");t.setDaemon(true);return t; }, new ThreadPoolExecutor.AbortPolicy());
        try {
            memory = new MemoryStore(getDataFolder().toPath().resolve("memory.json"), bounded("memory.turns",6,1,20), bounded("memory.max-conversations",500,1,5000));
            provider = createProvider(); loadNpcs();
            Objects.requireNonNull(getCommand("ainpc")).setExecutor(this);
            getCommand("ainpc").setTabCompleter(this);
            getServer().getPluginManager().registerEvents(this,this);
            getLogger().info("Ready: " + npcs.size() + " NPC(s), " + provider.label());
        } catch (Exception e) {
            getLogger().severe("Startup failed: " + e.getMessage()); getServer().getPluginManager().disablePlugin(this);
        }
    }
    @Override public void onDisable() {
        generation.incrementAndGet(); selected.clear();
        if (workers != null) workers.shutdownNow();
        if (memory != null) { try { memory.save(); } catch (IOException e) { getLogger().severe("Memory could not be saved"); } }
        if (npcKey != null) saveNpcs();
    }
    private int bounded(String path,int fallback,int min,int max) { return Math.clamp(getConfig().getInt(path,fallback),min,max); }
    private DialogueProvider createProvider() {
        String mode=getConfig().getString("provider","demo");
        if (mode.equals("demo")) return new DemoProvider();
        if (!mode.equals("api")) throw new IllegalArgumentException("provider must be demo or api");
        return new CompatibleProvider(getConfig().getString("api.base-url","https://api.openai.com/v1"),
            getConfig().getString("api.model","SET_YOUR_MODEL_ID"), System.getenv(getConfig().getString("api.key-env","AINPC_API_KEY")),
            bounded("api.timeout-seconds",20,2,60),bounded("api.max-tokens",220,20,1000));
    }
    private void tell(CommandSender sender,String text) { sender.sendMessage(Component.text("[AI NPC] ",NamedTextColor.AQUA).append(Component.text(text,NamedTextColor.WHITE))); }
    private void error(CommandSender sender,String text) { sender.sendMessage(Component.text("[AI NPC] " + text,NamedTextColor.RED)); }
    private Npc require(String id) { Npc npc=npcs.get(id);if(npc==null)throw new IllegalArgumentException("NPC not found: " + id);return npc; }
    private Player requirePlayer(CommandSender sender) { if(sender instanceof Player p)return p;throw new IllegalArgumentException("Run this command in-game"); }
    private static String rest(String[] args,int from) { return String.join(" ",Arrays.copyOfRange(args,from,args.length)); }
    @Override public boolean onCommand(CommandSender sender,Command command,String label,String[] args) {
        try {
            String action=args.length==0?"help":args[0].toLowerCase(Locale.ROOT);
            if(action.equals("help")) {
                tell(sender,"Right-click an NPC, then type in chat. /ainpc exit ends the conversation.");
                tell(sender,"/ainpc list | talk <id> <message> | exit");
                if(sender.hasPermission("ainpc.admin"))tell(sender,"create <id> [name] | remove <id> | name <id> <name> | personality <id> <preset|custom prompt> | memory <id> <on|off|clear> | reload");
                return true;
            }
            if(action.equals("exit")) { selected.remove(requirePlayer(sender).getUniqueId());tell(sender,"Conversation ended. Normal chat restored.");return true; }
            if(action.equals("list")) { tell(sender,"NPCs: " + String.join(", ",npcs.keySet()) + " | " + provider.label());return true; }
            if(action.equals("talk")) {
                if(args.length<3)throw new IllegalArgumentException("/ainpc talk <id> <message>");
                talk(requirePlayer(sender),args[1],rest(args,2));return true;
            }
            if(!sender.hasPermission("ainpc.admin"))throw new IllegalArgumentException("Admin permission required");
            if(action.equals("reload")) {
                reloadConfig(); DialogueProvider next=createProvider();provider=next;generation.incrementAndGet();
                tell(sender,"Configuration reloaded: " + provider.label() + ". Memory limits apply on server restart.");return true;
            }
            if(args.length<2)throw new IllegalArgumentException("Specify an NPC id. /ainpc help");
            String id=args[1];
            if(action.equals("create")) {
                if(!id.matches("[a-zA-Z0-9_-]{1,32}"))throw new IllegalArgumentException("Use 1-32 letters, numbers, underscores or hyphens for id");
                if(npcs.containsKey(id))throw new IllegalArgumentException("NPC id already exists");
                if(npcs.size()>=50)throw new IllegalArgumentException("Demo limit: 50 NPCs");
                Player p=requirePlayer(sender);String name=args.length>2?rest(args,2):id;
                if(name.length()>60)throw new IllegalArgumentException("Name limit: 60 characters");
                Npc npc=new Npc(id,name,"merchant",true,p.getLocation().clone(),null);attach(npc);npcs.put(id,npc);saveNpcs();tell(sender,"Created " + name);return true;
            }
            Npc npc=require(id);
            switch(action) {
                case "remove" -> {
                    npc.location.getChunk().load();Entity entity=Bukkit.getEntity(npc.entity);if(entity!=null)entity.remove();
                    npcs.remove(id);removedIds.add(id);selected.entrySet().removeIf(e -> e.getValue().equals(id));memory.clearNpc(id);persistMemory();saveNpcs();tell(sender,"Removed " + id);
                }
                case "name" -> {
                    if(args.length<3||rest(args,2).length()>60)throw new IllegalArgumentException("/ainpc name <id> <name up to 60 characters>");
                    npc.name=rest(args,2);attach(npc);saveNpcs();tell(sender,"Name updated");
                }
                case "personality" -> {
                    if(args.length<3)throw new IllegalArgumentException("/ainpc personality <id> merchant|guide|custom <prompt>");
                    String value=args[2];
                    if(value.equals("custom")) {
                        if(args.length<4||rest(args,3).length()>2000)throw new IllegalArgumentException("Custom prompt: 1-2000 characters");
                        npc.personality="custom:"+rest(args,3);
                    } else {
                        if(!getConfig().isString("personality."+value))throw new IllegalArgumentException("Unknown personality preset");
                        npc.personality=value;
                    }
                    memory.clearNpc(id);persistMemory();saveNpcs();tell(sender,"Personality updated; previous memory cleared");
                }
                case "memory" -> {
                    if(args.length!=3||!List.of("on","off","clear").contains(args[2]))throw new IllegalArgumentException("/ainpc memory <id> on|off|clear");
                    if(!args[2].equals("clear"))npc.memory=args[2].equals("on");
                    memory.clearNpc(id);persistMemory();saveNpcs();tell(sender,"Memory: "+(npc.memory?"on":"off")+", history cleared");
                }
                default -> throw new IllegalArgumentException("Unknown command. /ainpc help");
            }
        } catch (IllegalArgumentException e) { error(sender,e.getMessage()); }
        catch (Exception e) { error(sender,"Operation failed. Check server logs.");getLogger().log(Level.WARNING,"NPC management failed",e); }
        return true;
    }
    private void talk(Player player,String id,String question) {
        if(!player.hasPermission("ainpc.use")){error(player,"Conversation permission required");return;}
        Npc npc=npcs.get(id);if(npc==null){error(player,"NPC no longer exists");selected.remove(player.getUniqueId());return;}
        if(!player.getWorld().equals(npc.location.getWorld())||player.getLocation().distanceSquared(npc.location)>Math.pow(bounded("dialogue.distance-blocks",12,2,64),2)) {
            error(player,"Move closer to the NPC");return;
        }
        question=question.strip();if(question.isEmpty()||question.length()>bounded("dialogue.max-input-chars",500,10,2000)){error(player,"Message is empty or too long");return;}
        UUID uuid=player.getUniqueId();long now=System.nanoTime();
        if(now-lastRequest.getOrDefault(uuid,0L)<TimeUnit.SECONDS.toNanos(bounded("dialogue.cooldown-seconds",3,0,60))){error(player,"Please wait a moment");return;}
        if(!busy.add(uuid)){error(player,"A reply is already being prepared");return;}
        lastRequest.put(uuid,now);
        MemoryStore.Snapshot snapshot=memory.snapshot(uuid,id);boolean remember=npc.memory;
        String prompt=npc.personality.startsWith("custom:")?npc.personality.substring(7):getConfig().getString("personality."+npc.personality, "You are a friendly NPC. Reply briefly in the player's language.");
        DialogueProvider active=provider;long currentGeneration=generation.get();String input=question;String displayName=npc.name;
        int maxOutput=bounded("dialogue.max-output-chars",900,100,3000);
        tell(player,displayName+" is thinking… ["+active.label()+"]");
        try {
            workers.execute(() -> {
                try {
                    String answer=active.reply(prompt,remember?snapshot.history():List.of(),input);
                    answer=answer.replaceAll("[\\p{Cntrl}&&[^\\n]]","").strip();if(answer.length()>maxOutput)answer=answer.substring(0,maxOutput)+"…";
                    if(currentGeneration!=generation.get())return;
                    // Revision prevents a late API reply from restoring removed/cleared memories.
                    if(remember&&memory.commit(uuid,id,snapshot.revision(),input,answer)) {
                        try{memory.save();}catch(IOException e){getLogger().warning("Reply succeeded, but memory persistence failed");}
                    }
                    String text=answer;
                    onMain(() -> { if(currentGeneration==generation.get()&&npcs.get(id)==npc&&player.isOnline())
                        player.sendMessage(Component.text("["+displayName+"] ",NamedTextColor.GOLD).append(Component.text(text,NamedTextColor.WHITE))); });
                } catch (Exception e) {
                    if(e instanceof InterruptedException)Thread.currentThread().interrupt();
                    // Avoid logging provider bodies, prompts, player messages or secrets.
                    getLogger().warning("NPC API request failed: "+e.getClass().getSimpleName());
                    onMain(() -> { if(player.isOnline())error(player,"Reply unavailable. Check API settings or try again later."); });
                } finally { busy.remove(uuid); }
            });
        } catch(RejectedExecutionException e){busy.remove(uuid);error(player,"Server conversation queue is full; try again shortly");}
    }
    private void onMain(Runnable action) { if(isEnabled())try{Bukkit.getScheduler().runTask(this,action);}catch(IllegalStateException ignored){} }
    private void persistMemory() {
        try { workers.execute(() -> { try{memory.save();}catch(IOException e){getLogger().warning("Memory could not be saved");} }); }
        catch(RejectedExecutionException e){getLogger().warning("Memory save queue full; changes remain in memory until next save");}
    }
    @EventHandler(ignoreCancelled=true) public void interact(PlayerInteractEntityEvent event) {
        if(event.getHand()!=org.bukkit.inventory.EquipmentSlot.HAND)return;
        String id=event.getRightClicked().getPersistentDataContainer().get(npcKey,PersistentDataType.STRING);
        if(id==null||!npcs.containsKey(id))return;event.setCancelled(true);
        Player player=event.getPlayer();if(!player.hasPermission("ainpc.use")){error(player,"Conversation permission required");return;}
        selected.put(player.getUniqueId(),id);tell(player,"Talking to "+npcs.get(id).name+". Type in chat; /ainpc exit returns to normal chat.");
        player.sendMessage(Component.text("[Click to type a question]",NamedTextColor.GREEN).clickEvent(ClickEvent.suggestCommand("/ainpc talk "+id+" ")));
    }
    @EventHandler(priority=EventPriority.HIGH,ignoreCancelled=true) public void chat(AsyncChatEvent event) {
        UUID uuid=event.getPlayer().getUniqueId();String id=selected.get(uuid);if(id==null)return;
        event.setCancelled(true);String text=PlainTextComponentSerializer.plainText().serialize(event.message());
        onMain(() -> { Player player=Bukkit.getPlayer(uuid);if(player!=null)talk(player,id,text); });
    }
    @EventHandler public void quit(PlayerQuitEvent event) { UUID id=event.getPlayer().getUniqueId();selected.remove(id);lastRequest.remove(id); }
    @EventHandler(ignoreCancelled=true) public void protect(EntityDamageEvent event) {
        if(event.getEntity().getPersistentDataContainer().has(npcKey,PersistentDataType.STRING))event.setCancelled(true);
    }
    private void attach(Npc npc) {
        npc.location.getChunk().load();Entity entity=npc.entity==null?null:Bukkit.getEntity(npc.entity);
        if(!(entity instanceof Villager)) {
            entity=Arrays.stream(npc.location.getChunk().getEntities()).filter(e -> npc.id.equals(e.getPersistentDataContainer().get(npcKey,PersistentDataType.STRING))).findFirst().orElse(null);
        }
        Villager villager=entity instanceof Villager v?v:npc.location.getWorld().spawn(npc.location,Villager.class);
        villager.setAI(false);villager.setInvulnerable(true);villager.setPersistent(true);villager.setRemoveWhenFarAway(false);villager.setCollidable(false);
        villager.customName(Component.text(npc.name,NamedTextColor.GOLD));villager.setCustomNameVisible(true);
        villager.getPersistentDataContainer().set(npcKey,PersistentDataType.STRING,npc.id);npc.entity=villager.getUniqueId();
    }
    private void loadNpcs() {
        File file=new File(getDataFolder(),"npcs.yml");YamlConfiguration yaml=YamlConfiguration.loadConfiguration(file);
        for(String id:yaml.getKeys(false)) {
            try {
                String path=id+"."; World world=Bukkit.getWorld(UUID.fromString(Objects.requireNonNull(yaml.getString(path+"world"))));
                if(world==null){getLogger().warning("NPC "+id+" skipped: world unavailable");continue;}
                Location location=new Location(world,yaml.getDouble(path+"x"),yaml.getDouble(path+"y"),yaml.getDouble(path+"z"),(float)yaml.getDouble(path+"yaw"),0);
                String entity=yaml.getString(path+"entity");Npc npc=new Npc(id,yaml.getString(path+"name",id),yaml.getString(path+"personality","merchant"),yaml.getBoolean(path+"memory",true),location,entity==null?null:UUID.fromString(entity));
                attach(npc);npcs.put(id,npc);
            } catch(RuntimeException e){getLogger().warning("Invalid NPC entry skipped: "+id);}
        }
        registryReady=true;saveNpcs();
    }
    private void saveNpcs() {
        // Startup failure must not overwrite an existing registry with an empty file.
        if(!registryReady)return;
        File file=new File(getDataFolder(),"npcs.yml");YamlConfiguration yaml=YamlConfiguration.loadConfiguration(file);
        // Preserve invalid/unavailable-world entries for administrators to repair.
        for(String id:removedIds)yaml.set(id,null);
        for(Npc n:npcs.values()) {
            String p=n.id+".";yaml.set(p+"name",n.name);yaml.set(p+"personality",n.personality);yaml.set(p+"memory",n.memory);yaml.set(p+"world",n.location.getWorld().getUID().toString());
            yaml.set(p+"x",n.location.getX());yaml.set(p+"y",n.location.getY());yaml.set(p+"z",n.location.getZ());yaml.set(p+"yaw",n.location.getYaw());yaml.set(p+"entity",n.entity.toString());
        }
        try{yaml.save(file);}catch(IOException e){getLogger().severe("NPC configuration could not be saved");}
    }
    @Override public List<String> onTabComplete(CommandSender sender,Command command,String alias,String[] args) {
        List<String> choices;
        if(args.length==1)choices=sender.hasPermission("ainpc.admin")?List.of("create","remove","name","personality","memory","reload","list","talk","exit","help"):List.of("list","talk","exit","help");
        else if(args.length==2)choices=new ArrayList<>(npcs.keySet());
        else if(args.length==3&&args[0].equals("personality"))choices=List.of("merchant","guide","custom");
        else if(args.length==3&&args[0].equals("memory"))choices=List.of("on","off","clear");
        else choices=List.of();
        String prefix=args[args.length-1].toLowerCase(Locale.ROOT);return choices.stream().filter(s -> s.toLowerCase(Locale.ROOT).startsWith(prefix)).toList();
    }
}
