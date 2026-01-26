import ChatInterface from "@/components/chatInterface";
import IngestionInterface from "@/components/ingestionInterface";

function Home() {
  return (
    <main className="flex flex-row md:flex-row min-h-screen bg-background">
      <section className="md:w-1/3 border-r">
        <IngestionInterface />
      </section>

      <section className="md:w-2/3">
        <ChatInterface />
      </section>
    </main>
  );
}

export default Home;
