import { Toaster } from "@/components/ui/sonner";
import { Home } from "./pages/Home";

export function App() {
  return (
    <div className="h-screen">
      <Toaster />
      <Home />
    </div>
  );
}

export default App;
