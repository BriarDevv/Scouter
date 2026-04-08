"use client";

import { useRef, useState, KeyboardEvent } from "react";
import { ArrowUp } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (content: string) => Promise<void>;
  disabled?: boolean;
  error?: string | null;
}

export function ChatInput({ onSend, disabled, error }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = async () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    await onSend(trimmed);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 150) + "px";
  };

  return (
    <div className="border-t border-border p-4">
      {error && <p className="mb-2 text-xs text-destructive">{error}</p>}
      <div className="mx-auto max-w-4xl flex items-center gap-2 rounded-2xl border border-border bg-background px-3 py-2 focus-within:ring-2 focus-within:ring-ring/30 focus-within:border-ring transition-all">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder="Escribi un mensaje..."
          rows={1}
          disabled={disabled}
          className="flex-1 resize-none bg-transparent text-sm leading-normal outline-none placeholder:text-muted-foreground disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-xl transition-colors",
            value.trim() && !disabled
              ? "bg-foreground text-background hover:bg-foreground/80"
              : "bg-muted text-muted-foreground"
          )}
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
