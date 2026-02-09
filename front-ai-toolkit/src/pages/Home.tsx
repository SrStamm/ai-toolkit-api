import ChatInterface from "@/components/chatInterface";
import IngestionInterface from "@/components/ingestionInterface";
import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetClose,
  SheetFooter,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";

function Home() {
  return (
    <main className="relative flex md:static md:flex-row min-h-screen bg-background">
      <section className="hidden md:block md:relative md:w-1/3 md:border-r">
        <IngestionInterface />
      </section>

      <section className="absolute top-0 left-0 md:hidden">
        <Sheet>
          <SheetTrigger>
            <Button>Open</Button>
          </SheetTrigger>
          <SheetContent showCloseButton={false}>
            <IngestionInterface />

            <SheetFooter>
              <SheetClose asChild>
                <Button>Close</Button>
              </SheetClose>
            </SheetFooter>
          </SheetContent>
        </Sheet>
      </section>

      <section className="md:w-2/3">
        <ChatInterface />
      </section>
    </main>
  );
}

export default Home;
