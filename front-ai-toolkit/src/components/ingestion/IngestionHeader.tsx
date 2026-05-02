import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

export function IngestionHeader() {
  return (
    <div className="px-6 pt-6 pb-4 border-b bg-gradient-to-r from-primary/5 to-transparent">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-xl bg-primary/10">
          <Sparkles className="size-5 text-primary" />
        </div>
        <div>
          <h2 className="text-lg font-semibold">Ingesta de Datos</h2>
          <p className="text-xs text-muted-foreground">
            Cargá documentos para que el agente pueda responder
          </p>
        </div>
      </div>
    </div>
  );
}
