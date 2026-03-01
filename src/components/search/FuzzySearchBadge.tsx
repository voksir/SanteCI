import { Search } from "lucide-react";
import { cn } from "@/lib/utils";

interface FuzzySearchBadgeProps {
  visible: boolean;
  className?: string;
}

export function FuzzySearchBadge({ visible, className }: FuzzySearchBadgeProps) {
  if (!visible) return null;
  return (
    <div
      className={cn(
        "flex items-center gap-1.5 text-xs text-amber-700 bg-amber-50",
        "border border-amber-200 rounded-md px-2.5 py-1 w-fit",
        className
      )}
    >
      <Search className="w-3.5 h-3.5 shrink-0" />
      Résultats approchants de votre recherche
    </div>
  );
}
