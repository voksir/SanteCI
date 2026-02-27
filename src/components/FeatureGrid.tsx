import { Link } from "react-router-dom";
import { Clock, MapPin, Pill, CreditCard, Heart, Gift } from "lucide-react";

const features = [
  { label: "Pharmacies de Garde", icon: Clock, path: "/garde" },
  { label: "Pharmacies à proximité", icon: MapPin, path: "/proximite" },
  { label: "Prix de Médicaments", icon: Pill, path: "/prix" },
  { label: "Bons & Assurances", icon: CreditCard, path: "/assurances" },
  { label: "Actu Santé", icon: Heart, path: "/actualites" },
  { label: "Faire un don", icon: Gift, path: "/don" },
];

const FeatureGrid = () => {
  return (
    <section className="honeycomb-bg py-8 px-4">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 max-w-lg mx-auto">
        {features.map((item, i) => (
          <Link
            key={item.path}
            to={item.path}
            className="group flex flex-col items-center gap-3 p-5 bg-primary rounded-xl shadow-md hover:shadow-lg active:scale-95 transition-all duration-200 animate-fade-in"
            style={{ animationDelay: `${i * 80}ms`, animationFillMode: "both" }}
          >
            <div className="bg-primary-foreground/20 rounded-full p-3 group-hover:bg-primary-foreground/30 transition-colors">
              <item.icon size={32} className="text-primary-foreground" />
            </div>
            <span className="text-primary-foreground text-xs font-semibold text-center leading-tight">
              {item.label}
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
};

export default FeatureGrid;
