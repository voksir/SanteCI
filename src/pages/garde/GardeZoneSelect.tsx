import { useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import Header from "@/components/Header";

/**
 * Étape 2 : Choisissez une zone — Abidjan ou Intérieur.
 * Design 113 : fond clair, deux cartes blanches à bord vert, coins arrondis.
 */
const GardeZoneSelect = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col bg-[hsl(120,20%,97%)]">
      <Header />
      <header className="sticky top-14 z-40 bg-[hsl(120,20%,97%)] border-b border-border/50">
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
            Pharmacies de garde
          </h1>
        </div>
      </header>
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-8">
        <p className="text-muted-foreground text-center text-base mb-8">
          Choisissez une zone.
        </p>
        <div className="grid grid-cols-2 gap-4 w-full max-w-md">
          <button
            type="button"
            onClick={() => navigate("/garde/abidjan")}
            className="flex items-center justify-center min-h-[120px] rounded-2xl bg-card border-2 border-primary/30 shadow-sm hover:shadow-md hover:border-primary/50 active:scale-[0.98] transition-all text-foreground font-medium text-lg"
          >
            Abidjan
          </button>
          <button
            type="button"
            onClick={() => navigate("/garde/interieur")}
            className="flex items-center justify-center min-h-[120px] rounded-2xl bg-card border-2 border-primary/30 shadow-sm hover:shadow-md hover:border-primary/50 active:scale-[0.98] transition-all text-foreground font-medium text-lg"
          >
            Intérieur
          </button>
        </div>
      </main>
    </div>
  );
};

export default GardeZoneSelect;
