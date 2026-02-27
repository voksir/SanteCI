import { Menu, X, Home, Clock, MapPin, Pill, CreditCard, Heart, Gift } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

const navItems = [
  { label: "Accueil", icon: Home, path: "/" },
  { label: "Pharmacies de Garde", icon: Clock, path: "/garde" },
  { label: "Pharmacies à proximité", icon: MapPin, path: "/proximite" },
  { label: "Prix de Médicaments", icon: Pill, path: "/prix" },
  { label: "Bons & Assurances", icon: CreditCard, path: "/assurances" },
  { label: "Actu Santé", icon: Heart, path: "/actualites" },
  { label: "Faire un don", icon: Gift, path: "/don" },
];

const Header = () => {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <>
      <header className="sticky top-0 z-50 bg-primary shadow-md">
        <div className="flex items-center justify-between px-4 h-14">
          <button
            onClick={() => setDrawerOpen(true)}
            className="text-primary-foreground p-1"
            aria-label="Menu"
          >
            <Menu size={26} />
          </button>
          <h1 className="text-primary-foreground font-bold text-lg tracking-wide">
            PHARMACIES CI
          </h1>
          <div className="w-8" />
        </div>
      </header>

      {/* Overlay */}
      {drawerOpen && (
        <div
          className="fixed inset-0 bg-foreground/40 z-50"
          onClick={() => setDrawerOpen(false)}
        />
      )}

      {/* Drawer */}
      <aside
        className={`fixed top-0 left-0 h-full w-72 bg-card z-50 shadow-2xl transform transition-transform duration-300 ${
          drawerOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between p-4 bg-primary">
          <span className="text-primary-foreground font-bold text-lg">
            PHARMACIES CI
          </span>
          <button
            onClick={() => setDrawerOpen(false)}
            className="text-primary-foreground"
          >
            <X size={24} />
          </button>
        </div>
        <nav className="py-2">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              onClick={() => setDrawerOpen(false)}
              className="flex items-center gap-3 px-5 py-3.5 text-foreground hover:bg-accent transition-colors"
            >
              <item.icon size={20} className="text-primary" />
              <span className="font-medium text-sm">{item.label}</span>
            </Link>
          ))}
        </nav>
      </aside>
    </>
  );
};

export default Header;
