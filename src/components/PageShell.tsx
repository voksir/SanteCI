import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface PageShellProps {
  title: string;
  children?: React.ReactNode;
}

const PageShell = ({ title, children }: PageShellProps) => {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <header className="sticky top-0 z-50 bg-primary shadow-md">
        <div className="flex items-center gap-3 px-4 h-14">
          <button onClick={() => navigate(-1)} className="text-primary-foreground">
            <ArrowLeft size={24} />
          </button>
          <h1 className="text-primary-foreground font-bold text-lg">{title}</h1>
        </div>
      </header>
      <main className="flex-1 flex items-center justify-center p-6">
        {children || (
          <p className="text-muted-foreground text-center text-sm">
            Cette page sera bientôt disponible.
          </p>
        )}
      </main>
    </div>
  );
};

export default PageShell;
