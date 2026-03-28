"use client";

import { useCallback, useRef, useState } from "react";
import { API_BASE_URL } from "@/lib/constants";
import type { ChatMessage } from "@/types";

interface UseChatReturn {
  messages: ChatMessage[];
  isStreaming: boolean;
  error: string | null;
  sendMessage: (content: string, overrideId?: string) => Promise<void>;
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
}

export function useChat(conversationId: string | null): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const streamBuf = useRef("");
  const flushTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const sendMessage = useCallback(async (content: string, overrideId?: string) => {
    const targetId = overrideId || conversationId;
    if (!targetId || !content.trim()) return;

    setError(null);

    // Add user message optimistically
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      attachments: null,
      tool_calls: [],
      model: null,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);

    // Create placeholder for assistant response
    const assistantId = crypto.randomUUID();
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      attachments: null,
      tool_calls: [],
      model: null,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, assistantMsg]);

    setIsStreaming(true);
    abortRef.current = new AbortController();

    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      const apiKey = process.env.NEXT_PUBLIC_API_KEY;
      if (apiKey) headers["X-API-Key"] = apiKey;

      const res = await fetch(
        `${API_BASE_URL}/chat/conversations/${targetId}/messages`,
        {
          method: "POST",
          headers,
          body: JSON.stringify({ content }),
          signal: abortRef.current.signal,
        }
      );

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let eventType = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const data = JSON.parse(line.slice(6));
            switch (eventType) {
              case "text_delta":
                streamBuf.current += data.content;
                if (!flushTimer.current) {
                  flushTimer.current = setTimeout(() => {
                    const buf = streamBuf.current;
                    streamBuf.current = "";
                    flushTimer.current = null;
                    setMessages(prev =>
                      prev.map(m =>
                        m.id === assistantId
                          ? { ...m, content: (m.content || "") + buf }
                          : m
                      )
                    );
                  }, 50);
                }
                break;
              case "tool_start":
                setMessages(prev =>
                  prev.map(m =>
                    m.id === assistantId
                      ? {
                          ...m,
                          tool_calls: [
                            ...m.tool_calls,
                            {
                              id: data.tool_call_id,
                              tool_name: data.tool_name,
                              arguments: data.arguments,
                              result: null,
                              error: null,
                              status: "running",
                              duration_ms: null,
                            },
                          ],
                        }
                      : m
                  )
                );
                break;
              case "tool_result":
                setMessages(prev =>
                  prev.map(m =>
                    m.id === assistantId
                      ? {
                          ...m,
                          tool_calls: m.tool_calls.map(tc =>
                            tc.id === data.tool_call_id
                              ? {
                                  ...tc,
                                  result: data.result,
                                  error: data.error,
                                  status: data.error ? "failed" : "completed",
                                }
                              : tc
                          ),
                        }
                      : m
                  )
                );
                break;
              case "turn_complete": {
                // Flush any remaining streaming buffer
                if (flushTimer.current) {
                  clearTimeout(flushTimer.current);
                  flushTimer.current = null;
                }
                const remaining = streamBuf.current;
                streamBuf.current = "";
                setMessages(prev =>
                  prev.map(m =>
                    m.id === assistantId
                      ? { ...m, content: (m.content || "") + remaining, id: data.message_id }
                      : m
                  )
                );
                break;
              }
              case "error":
                setError(data.error);
                break;
            }
            eventType = "";
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setError((err as Error).message);
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }, [conversationId]);

  return { messages, isStreaming, error, sendMessage, setMessages };
}
