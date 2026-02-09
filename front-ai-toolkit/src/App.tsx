import { Toaster } from "sonner";
import "./App.css";
import Home from "./pages/Home";

function App() {
  return (
    <div className="h-screen">
      <Toaster />
      <Home />
    </div>
  );
}

export default App;
