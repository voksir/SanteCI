import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import GardeZoneSelect from "./pages/garde/GardeZoneSelect";
import GardeList from "./pages/garde/GardeList";
import GardeDetail from "./pages/garde/GardeDetail";
import Proximite from "./pages/Proximite";
import PrixList from "./pages/prix/PrixList";
import PrixDetail from "./pages/prix/PrixDetail";
import Assurances from "./pages/Assurances";
import Actualites from "./pages/Actualites";
import Don from "./pages/Don";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/garde" element={<GardeZoneSelect />} />
          <Route path="/garde/abidjan" element={<GardeList />} />
          <Route path="/garde/interieur" element={<GardeList />} />
          <Route path="/garde/pharmacie/:id" element={<GardeDetail />} />
          <Route path="/proximite" element={<Proximite />} />
          <Route path="/prix" element={<PrixList />} />
          <Route path="/prix/medicament/:code" element={<PrixDetail />} />
          <Route path="/assurances" element={<Assurances />} />
          <Route path="/actualites" element={<Actualites />} />
          <Route path="/don" element={<Don />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
