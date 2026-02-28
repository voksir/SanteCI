import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, MapPin, Phone, Share2 } from "lucide-react";
import { getPharmacieById, getDutyPeriodsByPharmacieId } from "@/services/gardeApi";
import { format } from "date-fns";
import { fr } from "date-fns/locale";
import Header from "@/components/Header";
import { Button } from "@/components/ui/button";

export default function GardeDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

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
    const endStr = currentPeriod
      ? format(new Date(currentPeriod.end_date), "dd/MM/yyyy", { locale: fr })
      : "";
    const text = `${pharmacie?.name ?? ""} — De garde jusqu'au ${endStr}. ${pharmacie?.address ?? ""} ${pharmacie?.phones?.[0] ?? ""}`;
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
              <div className="rounded-xl bg-primary px-4 py-3 text-primary-foreground text-sm font-medium flex items-center gap-2 mb-4">
                <span className="size-4 rounded-full bg-primary-foreground/80 shrink-0" />
                De garde jusqu'au{" "}
                {format(new Date(currentPeriod.end_date), "dd/MM/yyyy", {
                  locale: fr,
                })}
              </div>
            )}

            <div className="rounded-2xl bg-card border border-primary/20 shadow-sm p-5 mb-6">
              <h2 className="font-bold text-lg text-foreground mb-4">
                PHCIE {pharmacie.name}
              </h2>
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
              {pharmacie.phones && pharmacie.phones.length > 0 && (
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
