import { getHighlightSegments } from "@/lib/fuzzy";
import type { FuseResultMatch } from "@/lib/fuzzy";
import { cn } from "@/lib/utils";

interface SearchHighlightProps {
  text: string;
  fieldKey: string;
  matches?: ReadonlyArray<FuseResultMatch>;
  highlightClassName?: string;
  className?: string;
}

export function SearchHighlight({
  text,
  fieldKey,
  matches,
  highlightClassName,
  className,
}: SearchHighlightProps) {
  const segments = getHighlightSegments(text, matches, fieldKey);
  const hasHighlight = segments.some((s) => s.highlighted);
  if (!hasHighlight) {
    return <span className={className}>{text}</span>;
  }
  return (
    <span className={className}>
      {segments.map((segment, i) =>
        segment.highlighted ? (
          <mark
            key={i}
            className={cn(
              "bg-primary/20 text-primary-foreground rounded-sm px-0.5 font-semibold",
              highlightClassName
            )}
          >
            {segment.text}
          </mark>
        ) : (
          <span key={i}>{segment.text}</span>
        )
      )}
    </span>
  );
}
