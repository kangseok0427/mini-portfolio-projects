package dev.gaon.ainpc.core;
import java.util.List;
public interface DialogueProvider {
    String reply(String personality, List<Message> history, String question) throws Exception;
    String label();
}
