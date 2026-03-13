"use client";

import { useEffect, useState } from "react";
import { formatDateTime, formatRelativeTime } from "@/lib/formatters";

interface RelativeTimeProps {
  date: string;
  className?: string;
}

export function RelativeTime({ date, className }: RelativeTimeProps) {
  const absoluteText = formatDateTime(date);
  const [text, setText] = useState(absoluteText);

  useEffect(() => {
    const update = () => {
      setText(formatRelativeTime(date));
    };

    update();
    const intervalId = window.setInterval(update, 60_000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [date]);

  return (
    <time dateTime={new Date(date).toISOString()} title={absoluteText} className={className}>
      {text}
    </time>
  );
}
