package dev.gaon.ainpc.core;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;
import com.google.gson.*;
import java.nio.file.*;
import java.net.http.HttpRequest;
import java.util.*;
import java.util.concurrent.Flow;
import java.nio.ByteBuffer;
import java.io.ByteArrayOutputStream;
class CoreTest {
    @TempDir Path dir;
    @Test void isolatesPlayersAndNpcsAndPersists() throws Exception {
        Path file=dir.resolve("memory.json");MemoryStore m=new MemoryStore(file,6,500);UUID a=UUID.randomUUID(),b=UUID.randomUUID();
        assertTrue(m.commit(a,"merchant",0,"철 어디서 구해?","북쪽 광산"));m.save();
        assertEquals(2,m.snapshot(a,"merchant").history().size());assertTrue(m.snapshot(b,"merchant").history().isEmpty());assertTrue(m.snapshot(a,"guide").history().isEmpty());
        assertEquals("철 어디서 구해?",new MemoryStore(file,6,500).snapshot(a,"merchant").history().getFirst().content());
    }
    @Test void clearsRejectLateRepliesAndBoundsHistory() throws Exception {
        MemoryStore m=new MemoryStore(dir.resolve("m.json"),2,2);UUID player=UUID.randomUUID();
        for(int i=0;i<10;i++)assertTrue(m.commit(player,"a",0,"q"+i,"r"+i));
        assertEquals(4,m.snapshot(player,"a").history().size());assertEquals("q8",m.snapshot(player,"a").history().getFirst().content());
        var old=m.snapshot(player,"a");m.clearNpc("a");assertFalse(m.commit(player,"a",old.revision(),"late","late"));
        m.commit(player,"a",1,"new","new");m.commit(player,"b",0,"b","b");m.commit(player,"c",0,"c","c");assertTrue(m.snapshot(player,"a").history().isEmpty());
    }
    @Test void demoRecallsOnlySuppliedHistory() throws Exception {
        DemoProvider p=new DemoProvider();assertTrue(p.reply("merchant",List.of(),"철 어디서 구해?").contains("북쪽"));
        assertTrue(p.reply("merchant",List.of(new Message("user","철 어디서 구해?"),new Message("assistant","북쪽")),"아까 뭐 찾았지?").contains("철"));
        assertTrue(p.reply("merchant",List.of(),"아까 뭐 찾았지?").contains("아직"));assertTrue(p.label().contains("no LLM"));
    }
    @Test void compatibleProviderBuildsRequestAndParsesResponse() throws Exception {
        CompatibleProvider provider=new CompatibleProvider("https://example.com/v1","test-model","not-a-real-key",5,100,request -> {
            assertEquals("https://example.com/v1/chat/completions",request.uri().toString());assertEquals("Bearer not-a-real-key",request.headers().firstValue("Authorization").orElseThrow());
            assertEquals(5,request.timeout().orElseThrow().toSeconds());
            JsonObject json=JsonParser.parseString(body(request)).getAsJsonObject();assertEquals("test-model",json.get("model").getAsString());assertEquals(4,json.getAsJsonArray("messages").size());
            assertEquals("system",json.getAsJsonArray("messages").get(0).getAsJsonObject().get("role").getAsString());
            return new CompatibleProvider.Result(200,"{\"choices\":[{\"message\":{\"content\":\"북쪽 광산에서 구할 수 있어.\"}}]}");
        });
        assertTrue(provider.reply("merchant",List.of(new Message("user","hello"),new Message("assistant","hi")),"iron?").contains("북쪽"));
    }
    @Test void providerFailuresDoNotExposeBodiesOrKeys() {
        CompatibleProvider p=new CompatibleProvider("https://example.com","model","secret",5,100,r -> new CompatibleProvider.Result(429,"private secret body"));
        Exception e=assertThrows(IllegalStateException.class,() -> p.reply("p",List.of(),"q"));assertEquals("LLM API HTTP 429",e.getMessage());
        CompatibleProvider missing=new CompatibleProvider("https://example.com","m","",5,100,r -> {fail("must not call network");return null;});
        assertThrows(IllegalStateException.class,() -> missing.reply("p",List.of(),"q"));
        CompatibleProvider bad=new CompatibleProvider("https://example.com","m","k",5,100,r -> new CompatibleProvider.Result(200,"{}"));
        assertEquals("Invalid LLM response",assertThrows(IllegalStateException.class,() -> bad.reply("p",List.of(),"q")).getMessage());
    }
    @Test void corruptMemoryIsNotSilentlyDestroyed() throws Exception {
        Path file=dir.resolve("broken.json");Files.writeString(file,"broken");assertThrows(java.io.IOException.class,() -> new MemoryStore(file,6,500));assertEquals("broken",Files.readString(file));
    }
    private static String body(HttpRequest request) {
        ByteArrayOutputStream stream=new ByteArrayOutputStream();
        request.bodyPublisher().orElseThrow().subscribe(new Flow.Subscriber<ByteBuffer>() {
            public void onSubscribe(Flow.Subscription s){s.request(Long.MAX_VALUE);}
            public void onNext(ByteBuffer b){byte[] bytes=new byte[b.remaining()];b.get(bytes);stream.writeBytes(bytes);}
            public void onError(Throwable t){throw new RuntimeException(t);}
            public void onComplete(){}
        });return stream.toString(java.nio.charset.StandardCharsets.UTF_8);
    }
}
