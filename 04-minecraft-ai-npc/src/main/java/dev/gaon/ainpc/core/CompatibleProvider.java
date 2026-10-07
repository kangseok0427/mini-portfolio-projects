package dev.gaon.ainpc.core;
import com.google.gson.*;
import java.net.URI;
import java.net.http.*;
import java.time.Duration;
import java.util.List;
public final class CompatibleProvider implements DialogueProvider {
    @FunctionalInterface public interface Transport { Result send(HttpRequest request) throws Exception; }
    public record Result(int status, String body) {}
    private final URI endpoint;
    private final String model, key;
    private final Duration timeout;
    private final int maxTokens;
    private final Transport transport;
    public CompatibleProvider(String base, String model, String key, int timeoutSeconds, int maxTokens) {
        this(base, model, key, timeoutSeconds, maxTokens, defaultTransport());
    }
    public CompatibleProvider(String base, String model, String key, int timeoutSeconds, int maxTokens, Transport transport) {
        endpoint = URI.create(base.replaceAll("/+$", "") + "/chat/completions");
        if (!List.of("https", "http").contains(endpoint.getScheme()) || endpoint.getHost() == null || endpoint.getUserInfo() != null)
            throw new IllegalArgumentException("Invalid API base URL");
        if (endpoint.getScheme().equals("http") && !List.of("localhost", "127.0.0.1", "::1", "[::1]").contains(endpoint.getHost()))
            throw new IllegalArgumentException("Remote API requires HTTPS");
        this.model = model; this.key = key; this.timeout = Duration.ofSeconds(timeoutSeconds);
        this.maxTokens = maxTokens; this.transport = transport;
    }
    private static Transport defaultTransport() {
        HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).followRedirects(HttpClient.Redirect.NEVER).build();
        return request -> { var r = client.send(request, HttpResponse.BodyHandlers.ofString()); return new Result(r.statusCode(), r.body()); };
    }
    public String label() { return "LLM API · " + model; }
    public String reply(String personality, List<Message> history, String question) throws Exception {
        if (key == null || key.isBlank()) throw new IllegalStateException("API key environment variable is missing");
        JsonArray messages = new JsonArray();
        add(messages, "system", personality); history.forEach(m -> add(messages, m.role(), m.content())); add(messages, "user", question);
        JsonObject body = new JsonObject(); body.addProperty("model", model); body.add("messages", messages);
        body.addProperty("max_tokens", maxTokens); body.addProperty("temperature", 0.7);
        HttpRequest request = HttpRequest.newBuilder(endpoint).timeout(timeout).header("Authorization", "Bearer " + key)
            .header("Content-Type", "application/json").POST(HttpRequest.BodyPublishers.ofString(body.toString())).build();
        Result result = transport.send(request);
        if (result.status() < 200 || result.status() >= 300) throw new IllegalStateException("LLM API HTTP " + result.status());
        try {
            String answer = JsonParser.parseString(result.body()).getAsJsonObject().getAsJsonArray("choices").get(0).getAsJsonObject()
                .getAsJsonObject("message").get("content").getAsString();
            if (answer.isBlank()) throw new IllegalArgumentException();
            return answer;
        } catch (RuntimeException e) { throw new IllegalStateException("Invalid LLM response"); }
    }
    private static void add(JsonArray list, String role, String content) {
        JsonObject m = new JsonObject(); m.addProperty("role", role); m.addProperty("content", content); list.add(m);
    }
}
