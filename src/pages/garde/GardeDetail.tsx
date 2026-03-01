import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, MapPin, Phone, Share2, ChevronDown, ChevronUp } from "lucide-react";
import { getPharmacieById, getDutyPeriodsByPharmacieId } from "@/services/gardeApi";
import { format, isWithinInterval } from "date-fns";
import { fr } from "date-fns/locale";
import Header from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

function formatPeriodLabel(startDate: string, endDate: string): string {
  const start = format(new Date(startDate), "d MMM", { locale: fr });
  const end = format(new Date(endDate), "d MMM yyyy", { locale: fr });
  return `De garde du ${start} au ${end}`;
}

function formatPeriodAriaLabel(startDate: string, endDate: string): string {
  const start = format(new Date(startDate), "d MMMM yyyy", { locale: fr });
  const end = format(new Date(endDate), "d MMMM yyyy", { locale: fr });
  return `De garde du ${start} au ${end}`;
}

export default function GardeDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [autresPeriodesOpen, setAutresPeriodesOpen] = useState(false);

  const { data: pharmacie, isLoading, error } = useQuery({
    queryKey: ["pharmacie", id],
    queryFn: () => getPharmacieById(id!),
    enabled: !!id,
  });

  const { data: periods = [] } = useQuery({
    queryKey: ["garde", "pharmacie", id],
    queryFn: () => getDutyPeriodsByPharmacieId(id!),
    enabled: !!id,
  });

  const currentPeriod = periods[0];
  const otherPeriods = periods.length > 1 ? periods.slice(1) : [];

  const isCurrentPeriod =
    currentPeriod &&
    (() => {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const start = new Date(currentPeriod.start_date);
      start.setHours(0, 0, 0, 0);
      const end = new Date(currentPeriod.end_date);
      end.setHours(23, 59, 59, 999);
      return isWithinInterval(today, { start, end });
    })();

  const zoneLabel =
    pharmacie?.zone_type === "abidjan"
      ? "Abidjan"
      : pharmacie?.zone_type === "interieur"
        ? "Intérieur"
        : null;

  const openTel = (raw: string) => {
    const tel = raw.replace(/\s/g, "");
    if (tel) window.open(`tel:${tel}`, "_self");
  };

  const handleYAller = () => {
    const query = [pharmacie?.name, pharmacie?.address, pharmacie?.area ?? pharmacie?.city]
      .filter(Boolean)
      .join(", ");
    window.open(
      `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`,
      "_blank"
    );
  };

  const handlePartager = async () => {
    const periodStr = currentPeriod
      ? formatPeriodLabel(currentPeriod.start_date, currentPeriod.end_date)
      : "";
    const zoneStr = zoneLabel ? ` (${zoneLabel})` : "";
    const text = `${pharmacie?.name ?? ""} — ${periodStr}${zoneStr}. ${pharmacie?.address ?? ""} ${pharmacie?.phones?.[0] ?? ""}`;
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

  return (
    <div className="min-h-screen flex flex-col bg-[hsl(120,25%,96%)]">
      <Header />
      <header className="sticky top-14 z-40 bg-[hsl(120,25%,96%)] border-b border-border/50">
        <div className="flex items-center gap-2 px-4 h-14">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="p-1 text-foreground"
            aria-label="Retour"
          >
            <ArrowLeft size={24} />
          </button>
          <h1 className="flex-1 text-foreground font-bold text-lg truncate pr-8">
            {pharmacie ? `PHCIE ${pharmacie.name}` : "Pharmacie"}
          </h1>
        </div>
      </header>

      <main className="flex-1 px-4 py-6 pb-10">
        {isLoading && (
          <p className="text-muted-foreground text-sm py-8 text-center">
            Chargement...
          </p>
        )}
        {error && (
          <p className="text-destructive text-sm py-4">
            Erreur lors du chargement.
          </p>
        )}
        {!isLoading && !error && pharmacie && (
          <>
            {currentPeriod && (
              <div
                className="rounded-xl bg-primary px-4 py-3 text-primary-foreground text-sm font-medium flex flex-wrap items-center gap-2 mb-4"
                role="status"
                aria-label={formatPeriodAriaLabel(currentPeriod.start_date, currentPeriod.end_date)}
              >
                <span className="size-4 rounded-full bg-primary-foreground/80 shrink-0" aria-hidden />
                <span>
                  {formatPeriodLabel(currentPeriod.start_date, currentPeriod.end_date)}
                </span>
                {isCurrentPeriod && (
                  <span className="inline-flex items-center rounded-md bg-primary-foreground/20 px-2 py-0.5 text-xs font-semibold">
                    En ce moment
                  </span>
                )}
              </div>
            )}

            {otherPeriods.length > 0 && (
              <Collapsible open={autresPeriodesOpen} onOpenChange={setAutresPeriodesOpen} className="mb-4">
                <CollapsibleTrigger asChild>
                  <button
                    type="button"
                    className="flex w-full items-center justify-between rounded-xl border border-primary/20 bg-card px-4 py-3 text-left text-sm font-medium text-foreground hover:bg-muted/50 transition-colors"
                  >
                    <span>Autres périodes de garde ({otherPeriods.length})</span>
                    {autresPeriodesOpen ? (
                      <ChevronUp size={18} className="shrink-0" />
                    ) : (
                      <ChevronDown size={18} className="shrink-0" />
                    )}
                  </button>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <ul className="mt-2 space-y-2 rounded-xl border border-primary/20 bg-muted/30 p-4">
                    {otherPeriods.map((p) => (
                      <li
                        key={p.id}
                        className="text-sm text-muted-foreground"
                      >
                        {formatPeriodLabel(p.start_date, p.end_date)}
                      </li>
                    ))}
                  </ul>
                </CollapsibleContent>
              </Collapsible>
            )}

            <div className="rounded-2xl bg-card border border-primary/20 shadow-sm p-5 mb-4">
              <h2 className={`font-bold text-lg text-foreground ${zoneLabel ? "mb-1" : "mb-4"}`}>
                PHCIE {pharmacie.name}
              </h2>
              {zoneLabel && (
                <p className="text-muted-foreground text-sm mb-4">
                  Zone : {zoneLabel}
                </p>
              )}
              {pharmacie.address && (
                <div className="flex gap-2 text-muted-foreground text-sm mb-2">
                  <MapPin size={18} className="shrink-0 text-primary/80" />
                  <span>{pharmacie.address}</span>
                </div>
              )}
              {(pharmacie.area || pharmacie.city) && (
                <p className="text-muted-foreground text-sm ml-6 mb-2">
                  {pharmacie.section ?? ""} {pharmacie.area ?? pharmacie.city}
                </p>
              )}
              {pharmacie.phones && pharmacie.phones.length > 0 && pharmacie.phones.length <= 2 && (
                <div className="mt-3 space-y-2">
                  <p className="text-muted-foreground text-xs font-medium">Téléphone(s)</p>
                  {pharmacie.phones.map((num) => (
                    <div key={num} className="flex items-center justify-between gap-2 flex-wrap">
                      <span className="text-primary font-medium text-sm">+225 {num}</span>
                      <Button
                        size="sm"
                        variant="outline"
                        className="gap-1 border-primary/40 text-primary shrink-0"
                        onClick={() => openTel(num)}
                      >
                        <Phone size={14} />
                        Appeler
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {pharmacie.phones && pharmacie.phones.length > 2 && (
              <div className="rounded-2xl bg-muted/40 border border-border/60 shadow-sm p-5 mb-6">
                <p className="text-muted-foreground text-xs font-semibold uppercase tracking-wide mb-3">
                  Téléphone(s)
                </p>
                <div className="space-y-2">
                  {pharmacie.phones.map((num) => (
                    <div key={num} className="flex items-center justify-between gap-2 flex-wrap">
                      <span className="text-primary font-medium text-sm">+225 {num}</span>
                      <Button
                        size="sm"
                        variant="outline"
                        className="gap-1 border-primary/40 text-primary shrink-0"
                        onClick={() => openTel(num)}
                      >
                        <Phone size={14} />
                        Appeler
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-3 gap-2 mb-8">
              <Button
                size="lg"
                className="min-w-0 gap-1.5 bg-orange-500 hover:bg-orange-600 text-white text-sm sm:text-base"
                onClick={() => pharmacie.phones?.[0] && openTel(pharmacie.phones[0])}
              >
                <Phone size={20} className="shrink-0" />
                <span className="truncate">Appeler</span>
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="min-w-0 gap-1.5 border-primary/40 text-primary text-sm sm:text-base"
                onClick={handleYAller}
              >
                <MapPin size={20} className="shrink-0" />
                <span className="truncate">Y aller</span>
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="min-w-0 gap-1.5 border-primary/40 text-primary text-sm sm:text-base"
                onClick={handlePartager}
              >
                <Share2 size={20} className="shrink-0" />
                <span className="truncate">Partager</span>
              </Button>
            </div>

            <div className="rounded-xl bg-muted/60 border border-border/50 p-4 flex gap-3">
              <span className="text-muted-foreground shrink-0 size-5 rounded-full border border-muted-foreground/50 flex items-center justify-center text-xs font-medium">
                i
              </span>
              <p className="text-muted-foreground text-xs leading-relaxed">
                Les données sont fournies à titre informatif uniquement. Veuillez
                vérifier directement auprès de la pharmacie. Source : UNPPCI —
                Tour de garde.
              </p>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
