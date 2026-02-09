import ChatInterface from "@/components/chatInterface";
import IngestionInterface from "@/components/ingestionInterface";

function Home() {
  return (
    <main className="relative flex md:static md:flex-row min-h-screen bg-background">
      <section className="hidden md:block md:relative md:w-1/3 md:border-r">
        <IngestionInterface />
      </section>

      <section className="absolute md:hidden">
        <Sheet>
          <IngestionInterface />
        </Sheet>
      </section>

      <section className="md:w-2/3">
        <ChatInterface />
      </section>
    </main>
  );
}

export default Home;
