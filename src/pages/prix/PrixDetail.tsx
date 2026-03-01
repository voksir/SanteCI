import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Pill } from "lucide-react";
import { getMedicamentByCode } from "@/services/prixApi";
import { format } from "date-fns";
import { fr } from "date-fns/locale";
import Header from "@/components/Header";

export default function PrixDetail() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();

  const { data: medicament, isLoading, error } = useQuery({
    queryKey: ["prix", "medicament", code],
    queryFn: () => getMedicamentByCode(decodeURIComponent(code ?? "")),
    enabled: !!code,
  });

  return (
    <div className="min-h-screen flex flex-col bg-[hsl(120,25%,96%)]">
      <Header />
      <header className="sticky top-14 z-40 bg-[hsl(120,25%,96%)] border-b border-border/50">
        <div className="flex items-center gap-2 px-4 h-14">
          <button
            type="button"
            onClick={() => navigate("/prix")}
            className="p-1 text-foreground"
            aria-label="Retour à la liste"
          >
            <ArrowLeft size={24} />
          </button>
          <h1 className="flex-1 text-foreground font-bold text-lg truncate pr-8">
            {medicament ? medicament.nom_commercial : "Médicament"}
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
        {!isLoading && !error && medicament && (
          <div className="rounded-2xl bg-card border border-primary/20 shadow-sm p-5">
            <div className="flex items-start gap-3 mb-4">
              <div className="rounded-full bg-primary/10 p-2">
                <Pill size={24} className="text-primary" />
              </div>
              <div className="min-w-0 flex-1">
                <h2 className="font-bold text-lg text-foreground leading-tight">
                  {medicament.nom_commercial}
                </h2>
                <p className="text-sm text-muted-foreground mt-0.5">
                  Code : {medicament.code}
                </p>
              </div>
            </div>

            <div className="rounded-xl bg-primary px-4 py-3 text-primary-foreground mb-4">
              <p className="text-xs font-medium text-primary-foreground/90">
                Prix public
              </p>
              <p className="text-xl font-bold">
                {medicament.prix_fcfa.toLocaleString("fr-FR")} FCFA
              </p>
            </div>

            {medicament.groupe_therapeutique && (
              <div className="mb-4">
                <p className="text-xs font-medium text-muted-foreground mb-1">
                  Groupe thérapeutique
                </p>
                <p className="text-sm text-foreground">
                  {medicament.groupe_therapeutique}
                </p>
              </div>
            )}

            {(medicament.source || medicament.updated_at) && (
              <div className="pt-4 border-t border-border/50 text-xs text-muted-foreground">
                {medicament.source && (
                  <p>Source : {medicament.source}</p>
                )}
                {medicament.updated_at && (
                  <p>
                    Dernière mise à jour :{" "}
                    {format(new Date(medicament.updated_at), "d MMMM yyyy", {
                      locale: fr,
                    })}
                  </p>
                )}
              </div>
            )}
          </div>
        )}
        {!isLoading && !error && !medicament && code && (
          <p className="text-muted-foreground text-sm py-8 text-center">
            Médicament introuvable.
          </p>
        )}
      </main>
    </div>
  );
}
