"use client";

import { useEffect, useState } from "react";
import { formatDateTime, formatRelativeTime } from "@/lib/formatters";

interface RelativeTimeProps {
  date: string;
  className?: string;
}

function formatStableDateTime(date: string): string {
  const value = new Date(date);
  const day = String(value.getUTCDate()).padStart(2, "0");
  const month = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"][value.getUTCMonth()];
  const minutes = String(value.getUTCMinutes()).padStart(2, "0");
  const hours24 = value.getUTCHours();
  const meridiem = hours24 >= 12 ? "p. m." : "a. m.";
  const hours12 = hours24 % 12 || 12;

  return `${day}-${month}, ${hours12}:${minutes} ${meridiem}`;
}

export function RelativeTime({ date, className }: RelativeTimeProps) {
  const stableAbsoluteText = formatStableDateTime(date);
  const [text, setText] = useState(stableAbsoluteText);
  const [title, setTitle] = useState(stableAbsoluteText);

  useEffect(() => {
    const update = () => {
      setText(formatRelativeTime(date));
      setTitle(formatDateTime(date));
    };

    update();
    const intervalId = window.setInterval(update, 60_000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [date]);

  return (
    <time dateTime={new Date(date).toISOString()} title={title} className={className}>
      {text}
    </time>
  );
}
