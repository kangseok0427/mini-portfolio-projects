package dev.gaon.ainpc.core;
import java.util.List;
import java.util.Locale;
public final class DemoProvider implements DialogueProvider {
    public String label() { return "DEMO · scripted dialogue, no LLM call"; }
    public String reply(String personality, List<Message> history, String question) {
        String q = question.toLowerCase(Locale.ROOT);
        boolean korean = question.codePoints().anyMatch(c -> c >= 0xAC00 && c <= 0xD7A3);
        boolean remember = q.contains("아까") || q.contains("기억") || q.contains("remember") || q.contains("earlier");
        if (remember) {
            String previous = history.stream().filter(m -> m.role().equals("user")).map(Message::content).findFirst().orElse(null);
            if (previous == null) return korean ? "아직 기억에 남은 대화가 없네. 무엇을 찾고 있나?" : "We have no earlier conversation yet. What are you looking for?";
            return korean ? "아까 ‘" + previous + "’라고 물었지. 우리 대화는 기억하고 있네." : "Earlier you asked: “" + previous + "”. I remember our conversation.";
        }
        if (q.contains("철") || q.contains("iron")) return korean ? "철을 찾는군! 이 데모 세계 이야기로는 북쪽 광산에서 구할 수 있다네." : "Looking for iron? In our demo world's lore, try the northern mine.";
        if (personality.contains("village guide")) return korean ? "마을 안내인이라네. 어디로 가고 싶은가?" : "I'm the village guide. Where would you like to go?";
        return korean ? "반갑네, 여행자! 오늘은 어떤 물건을 찾고 있나?" : "Welcome, traveler! What goods are you looking for today?";
    }
}
