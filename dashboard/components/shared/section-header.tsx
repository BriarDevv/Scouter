import { cn } from "@/lib/utils";

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  level?: "section" | "card";
  className?: string;
}

export function SectionHeader({ title, subtitle, action, level = "section", className }: SectionHeaderProps) {
  const Tag = level === "section" ? "h2" : "h3";

  return (
    <div className={cn("flex items-center justify-between gap-3", className)}>
      <div>
        <Tag
          className={cn(
            "font-semibold font-heading text-foreground",
            level === "section" ? "text-base" : "text-sm"
          )}
        >
          {title}
        </Tag>
        {subtitle && (
          <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
