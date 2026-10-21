import { Toaster } from "@/components/ui/sonner";
import { Home } from "./pages/Home";
import { JobProvider } from "@/contexts/JobProvider";

export function App() {
  return (
    <JobProvider>
      <div className="h-screen">
        <Toaster />
        <Home />
      </div>
    </JobProvider>
  );
}

export default App;
