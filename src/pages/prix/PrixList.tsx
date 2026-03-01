import { useState, useMemo, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { ArrowLeft, Search, ChevronRight, Pill } from "lucide-react";
import {
  getMedicaments,
  searchMedicaments,
  getGroupesTherapeutiques,
} from "@/services/prixApi";
import type { Medicament, MedicamentsListOptions } from "@/types/medicaments";
import Header from "@/components/Header";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const PAGE_SIZE = 30;
const SEARCH_DEBOUNCE_MS = 400;

type SortOption = "nom" | "groupe" | "prix";

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(id);
  }, [value, delayMs]);
  return debounced;
}

export default function PrixList() {
  const navigate = useNavigate();
  const [searchInput, setSearchInput] = useState("");
  const [groupe, setGroupe] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<SortOption>("nom");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  const searchQuery = useDebouncedValue(searchInput.trim(), SEARCH_DEBOUNCE_MS);

  const listOptions: MedicamentsListOptions = useMemo(
    () => ({
      groupe_therapeutique: groupe,
      sortBy,
      sortOrder,
      limit: PAGE_SIZE,
    }),
    [groupe, sortBy, sortOrder]
  );

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
    isError,
  } = useInfiniteQuery({
    queryKey: ["prix", "list", searchQuery, listOptions],
    queryFn: ({ pageParam }) =>
      searchQuery
        ? searchMedicaments(searchQuery, {
            ...listOptions,
            offset: pageParam as number,
          })
        : getMedicaments({ ...listOptions, offset: pageParam as number }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) =>
      lastPage.length === PAGE_SIZE ? allPages.length * PAGE_SIZE : undefined,
  });

  const { data: groupes = [] } = useQuery({
    queryKey: ["prix", "groupes"],
    queryFn: getGroupesTherapeutiques,
  });

  const medicaments = useMemo(
    () => (data?.pages ?? []).flat(),
    [data?.pages]
  );

  return (
    <div className="min-h-screen flex flex-col bg-[hsl(120,25%,96%)]">
      <Header />
      <header className="sticky top-14 z-40 bg-[hsl(120,25%,96%)] border-b border-border/50">
        <div className="flex items-center gap-2 px-4 h-14">
          <button
            type="button"
            onClick={() => navigate("/")}
            className="p-1 text-foreground"
            aria-label="Retour à l'accueil"
          >
            <ArrowLeft size={24} />
          </button>
          <h1 className="flex-1 text-foreground font-bold text-lg text-center pr-8">
            Prix de médicaments
          </h1>
        </div>
        <div className="px-4 pb-3 space-y-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              placeholder="Nom ou groupe thérapeutique..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="pl-9 rounded-xl bg-card border-primary/20"
            />
          </div>
          <Select
            value={groupe ?? "all"}
            onValueChange={(v) => setGroupe(v === "all" ? null : v)}
          >
            <SelectTrigger className="w-full rounded-xl bg-card border-primary/20">
              <SelectValue placeholder="Tous les groupes" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les groupes</SelectItem>
              {groupes.map((g) => (
                <SelectItem key={g} value={g}>
                  {g}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </header>

      <main className="flex-1 px-4 py-4 pb-8">
        <div className="flex items-center justify-between gap-2 mb-3">
          <span className="text-muted-foreground text-xs">
            {medicaments.length} médicament{medicaments.length !== 1 ? "s" : ""}
          </span>
          <div className="flex items-center gap-2">
            <Select
              value={`${sortBy}-${sortOrder}`}
              onValueChange={(v) => {
                const [s, o] = v.split("-") as [SortOption, "asc" | "desc"];
                setSortBy(s);
                setSortOrder(o);
              }}
            >
              <SelectTrigger className="w-auto min-w-[160px] h-8 rounded-lg bg-card border-primary/20 text-xs">
                <SelectValue placeholder="Trier par" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="nom-asc">Nom (A–Z)</SelectItem>
                <SelectItem value="nom-desc">Nom (Z–A)</SelectItem>
                <SelectItem value="groupe-asc">Groupe (A–Z)</SelectItem>
                <SelectItem value="groupe-desc">Groupe (Z–A)</SelectItem>
                <SelectItem value="prix-asc">Prix (croissant)</SelectItem>
                <SelectItem value="prix-desc">Prix (décroissant)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {isError && (
          <p className="text-destructive text-sm py-4">
            Erreur lors du chargement. Réessayez.
          </p>
        )}
        {isLoading && (
          <p className="text-muted-foreground text-sm py-8 text-center">
            Chargement...
          </p>
        )}
        {!isLoading && !isError && medicaments.length === 0 && (
          <p className="text-muted-foreground text-sm py-8 text-center">
            Aucun médicament trouvé.
          </p>
        )}
        {!isLoading && !isError && medicaments.length > 0 && (
          <>
            <ul className="space-y-3">
              {medicaments.map((m) => (
                <MedicamentCard
                  key={m.id}
                  medicament={m}
                  onSelect={() => navigate(`/prix/medicament/${encodeURIComponent(m.code)}`)}
                />
              ))}
            </ul>
            {hasNextPage && (
              <div className="mt-4 flex justify-center">
                <Button
                  variant="outline"
                  className="border-primary/40 text-primary"
                  onClick={() => fetchNextPage()}
                  disabled={isFetchingNextPage}
                >
                  {isFetchingNextPage ? "Chargement..." : "Charger plus"}
                </Button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

function MedicamentCard({
  medicament,
  onSelect,
}: {
  medicament: Medicament;
  onSelect: () => void;
}) {
  return (
    <li className="rounded-xl bg-card border border-primary/20 shadow-sm overflow-hidden">
      <div
        className="p-4 cursor-pointer"
        onClick={onSelect}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && onSelect()}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <h2 className="font-semibold text-foreground leading-tight line-clamp-2">
              {medicament.nom_commercial}
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Code : {medicament.code}
            </p>
          </div>
          <div className="shrink-0 flex items-center gap-1 rounded-lg bg-primary px-2 py-1 text-primary-foreground text-xs font-medium">
            <Pill size={14} />
            <span>{medicament.prix_fcfa.toLocaleString("fr-FR")} FCFA</span>
          </div>
        </div>
        {medicament.groupe_therapeutique && (
          <p className="text-sm text-muted-foreground mt-2 line-clamp-1">
            {medicament.groupe_therapeutique}
          </p>
        )}
      </div>
      <div className="px-4 pb-4">
        <Button
          size="sm"
          className="w-full gap-1 bg-orange-500 hover:bg-orange-600 text-white text-xs sm:text-sm"
          onClick={(e) => {
            e.stopPropagation();
            onSelect();
          }}
        >
          <ChevronRight size={16} className="shrink-0" />
          Détails
        </Button>
      </div>
    </li>
  );
}
