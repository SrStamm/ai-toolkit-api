import { ChatInterface } from "@/components/chatInterface";
import { IngestionInterface } from "@/components/ingestionInterface";
import { Sheet, SheetTrigger, SheetContent } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";

export function Home() {
  return (
    <main className="flex h-screen w-full bg-background overflow-hidden">
      <aside className="hidden md:block md:w-80 border-r bg-muted/30 animate-slide-in-left">
        <IngestionInterface />
      </aside>

      <div className="flex flex-col flex-1 h-full">
        <header className="flex items-center p-4 border-b md:hidden bg-card animate-fade-in">
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2">
                <span>⚙️</span>
                Configurar Ingesta
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-75 sm:w-[100] p-0">
              <div className="pt-10">
                <IngestionInterface />
              </div>
            </SheetContent>
          </Sheet>
          <h1 className="ml-4 font-semibold text-sm tracking-tight">Mi RAG App</h1>
        </header>

        <section className="flex-1 overflow-hidden min-h-0 animate-fade-in">
          <ChatInterface />
        </section>
      </div>
    </main>
  );
}

export default Home;
