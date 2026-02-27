import Header from "@/components/Header";
import HeroCarousel from "@/components/HeroCarousel";
import FeatureGrid from "@/components/FeatureGrid";
import Footer from "@/components/Footer";

const Index = () => (
  <div className="min-h-screen flex flex-col bg-background">
    <Header />
    <HeroCarousel />
    <FeatureGrid />
    <div className="flex-1" />
    <Footer />
  </div>
);

export default Index;
