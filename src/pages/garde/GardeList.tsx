import { useMemo, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Search, MapPin, Phone, Share2 } from "lucide-react";
import {
  getGardeAbidjan,
  getGardeInterieur,
  getSectionsAbidjan,
  getVillesInterieur,
} from "@/services/gardeApi";
import type { PharmacieDeGarde } from "@/types/garde";
import { startOfWeek, endOfWeek, format } from "date-fns";
import { fr } from "date-fns/locale";
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

const weekStart = startOfWeek(new Date(), { weekStartsOn: 1 });
const weekEnd = endOfWeek(new Date(), { weekStartsOn: 1 });
const startDateStr = format(weekStart, "yyyy-MM-dd");
const endDateStr = format(weekEnd, "yyyy-MM-dd");

function formatDateRange(start: string, end: string) {
  return `${format(new Date(start), "d MMM", { locale: fr })} – ${format(new Date(end), "d MMM yyyy", { locale: fr })}`;
}

const PHCIE_PREFIX = "PHCIE ";

function displayPharmacyName(name: string) {
  return name ? `${PHCIE_PREFIX}${name}` : PHCIE_PREFIX.trim();
}

function GardeListContent() {
  const location = useLocation();
  const navigate = useNavigate();
  const isAbidjan = location.pathname.includes("/garde/abidjan");

  const [search, setSearch] = useState("");
  const [section, setSection] = useState<string | null>(null);
  const [city, setCity] = useState<string | null>(null);

  const { data: list = [], isLoading, error } = useQuery({
    queryKey: ["garde", isAbidjan ? "abidjan" : "interieur", startDateStr, endDateStr, section ?? city],
    queryFn: () =>
      isAbidjan
        ? getGardeAbidjan({ startDate: startDateStr, endDate: endDateStr, section })
        : getGardeInterieur({ startDate: startDateStr, endDate: endDateStr, city }),
  });

  const { data: sections = [] } = useQuery({
    queryKey: ["garde", "sections"],
    queryFn: getSectionsAbidjan,
    enabled: isAbidjan,
  });

  const { data: cities = [] } = useQuery({
    queryKey: ["garde", "villes"],
    queryFn: getVillesInterieur,
    enabled: !isAbidjan,
  });

  const filtered = useMemo(() => {
    if (!search.trim()) return list;
    const q = search.trim().toLowerCase();
    return list.filter((p) => p.name.toLowerCase().includes(q));
  }, [list, search]);

  const handleAppeler = (p: PharmacieDeGarde) => {
    const tel = p.phones?.[0]?.replace(/\s/g, "") ?? "";
    if (tel) window.open(`tel:${tel}`, "_self");
  };

  const handleYAller = (p: PharmacieDeGarde) => {
    const query = [p.name, p.address, p.area ?? p.city].filter(Boolean).join(", ");
    window.open(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`, "_blank");
  };

  const handlePartager = async (p: PharmacieDeGarde) => {
    const text = `${p.name} — De garde jusqu'au ${format(new Date(p.end_date), "dd/MM/yyyy", { locale: fr })}. ${p.address ?? ""} ${p.phones?.[0] ?? ""}`;
    if (navigator.share) {
      try {
        await navigator.share({ title: "Pharmacie de garde", text });
      } catch {
        await navigator.clipboard.writeText(text);
      }
    } else {
      await navigator.clipboard.writeText(text);
    }
  };

  const zoneLabel = isAbidjan ? "Abidjan" : "Intérieur";
  const filterLabel = isAbidjan ? "Toutes les sections" : "Toutes les villes";
  const filterOptions = isAbidjan ? sections : cities;
  const filterValue = isAbidjan ? section : city;
  const setFilter = isAbidjan ? setSection : setCity;

  return (
    <div className="min-h-screen flex flex-col bg-[hsl(120,25%,96%)]">
      <Header />
      <header className="sticky top-14 z-40 bg-[hsl(120,25%,96%)] border-b border-border/50">
        <div className="flex items-center gap-2 px-4 h-14">
          <button
            type="button"
            onClick={() => navigate("/garde")}
            className="p-1 text-foreground"
            aria-label="Retour"
          >
            <ArrowLeft size={24} />
          </button>
          <h1 className="flex-1 text-foreground font-bold text-lg text-center pr-8">
            Pharmacies de garde
          </h1>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => {}}
          >
            <MapPin size={18} />
            Carte
          </Button>
        </div>
        <div className="px-4 pb-3 space-y-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              placeholder="Rechercher une pharmacie..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 rounded-xl bg-card border-primary/20"
            />
          </div>
          <Select value={filterValue ?? "all"} onValueChange={(v) => setFilter(v === "all" ? null : v)}>
            <SelectTrigger className="w-full rounded-xl bg-card border-primary/20">
              <SelectValue placeholder={filterLabel} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{filterLabel}</SelectItem>
              {filterOptions.map((opt) => (
                <SelectItem key={opt} value={opt}>
                  {opt}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </header>

      <main className="flex-1 px-4 py-4 pb-8">
        <div className="rounded-xl bg-primary px-4 py-3 mb-4 shadow-sm">
          <p className="text-primary-foreground font-semibold text-sm leading-tight">
            Semaine du {formatDateRange(startDateStr, endDateStr)}
          </p>
          <p className="text-primary-foreground/90 text-xs mt-0.5">
            Zone : {zoneLabel}
          </p>
        </div>

        {error && (
          <p className="text-destructive text-sm py-4">
            Erreur lors du chargement. Réessayez.
          </p>
        )}
        {isLoading && (
          <p className="text-muted-foreground text-sm py-8 text-center">
            Chargement...
          </p>
        )}
        {!isLoading && !error && filtered.length === 0 && (
          <p className="text-muted-foreground text-sm py-8 text-center">
            Aucune pharmacie de garde pour cette période.
          </p>
        )}
        {!isLoading && !error && filtered.length > 0 && (
          <ul className="space-y-3">
            {filtered.map((p) => (
              <li
                key={p.id}
                className="rounded-xl bg-card border border-primary/20 shadow-sm overflow-hidden"
              >
                <div
                  className="p-4 cursor-pointer"
                  onClick={() => p.pharmacy_id && navigate(`/garde/pharmacie/${p.pharmacy_id}`)}
                  role={p.pharmacy_id ? "button" : undefined}
                >
                  <div className="flex items-start justify-between gap-2">
                    <h2 className="font-semibold text-foreground leading-tight">
                      {displayPharmacyName(p.name)}
                    </h2>
                    <span className="shrink-0 inline-flex items-center gap-1 rounded-lg bg-primary px-2 py-1 text-xs font-medium text-primary-foreground">
                      <span className="size-3 rounded-full bg-primary-foreground/80" />
                      De garde
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    {[p.section ?? p.city, p.area].filter(Boolean).join(", ")}
                  </p>
                  {p.address && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {p.address}
                    </p>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-2 px-4 pb-4">
                  <Button
                    size="sm"
                    className="min-w-0 gap-1 bg-orange-500 hover:bg-orange-600 text-white text-xs sm:text-sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAppeler(p);
                    }}
                  >
                    <Phone size={16} className="shrink-0" />
                    <span className="truncate">Appeler</span>
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="min-w-0 gap-1 border-primary/40 text-primary text-xs sm:text-sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleYAller(p);
                    }}
                  >
                    <MapPin size={16} className="shrink-0" />
                    <span className="truncate">Y aller</span>
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="min-w-0 gap-1 border-primary/40 text-primary text-xs sm:text-sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handlePartager(p);
                    }}
                  >
                    <Share2 size={16} className="shrink-0" />
                    <span className="truncate">Partager</span>
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}

export default GardeListContent;
