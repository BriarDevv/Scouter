"use client";

import { memo, useEffect, useRef } from "react";
import { Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";
import { ChatToolCallCard } from "@/components/chat/chat-tool-call";
import type { ChatMessage } from "@/types";

interface ChatMessagesProps {
  messages: ChatMessage[];
  isStreaming: boolean;
}

export const ChatMessages = memo(function ChatMessages({ messages, isStreaming }: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="text-center space-y-2">
          <Bot className="h-10 w-10 mx-auto text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">
            Escribi algo para comenzar
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map(msg => {
        if (msg.role === "tool") return null;
        const isUser = msg.role === "user";

        return (
          <div key={msg.id} className={cn("flex gap-3", isUser && "justify-end")}>
            {!isUser && (
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted dark:bg-muted">
                <Bot className="h-4 w-4 text-foreground dark:text-foreground" />
              </div>
            )}
            <div
              className={cn(
                "max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
                isUser
                  ? "bg-foreground text-background rounded-br-md"
                  : "bg-muted rounded-bl-md"
              )}
            >
              <div className="whitespace-pre-wrap break-words">{msg.content}</div>
              {msg.tool_calls.length > 0 && (
                <div className="mt-3 space-y-2">
                  {msg.tool_calls.map(tc => (
                    <ChatToolCallCard key={tc.id} toolCall={tc} />
                  ))}
                </div>
              )}
            </div>
            {isUser && (
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-foreground/10">
                <User className="h-4 w-4" />
              </div>
            )}
          </div>
        );
      })}
      {isStreaming && (
        <div className="flex gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted dark:bg-muted">
            <Bot className="h-4 w-4 text-foreground dark:text-foreground animate-pulse" />
          </div>
          <div className="flex items-center gap-1 text-muted-foreground">
            <span
              className="h-1.5 w-1.5 rounded-full bg-foreground/60 animate-bounce"
              style={{ animationDelay: "0ms" }}
            />
            <span
              className="h-1.5 w-1.5 rounded-full bg-foreground/60 animate-bounce"
              style={{ animationDelay: "150ms" }}
            />
            <span
              className="h-1.5 w-1.5 rounded-full bg-foreground/60 animate-bounce"
              style={{ animationDelay: "300ms" }}
            />
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
});
