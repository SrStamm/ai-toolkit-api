import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";

function ChatInterface() {
  return (
    <div className="flex flex-col h-[90vh] p-4 w-full">
      {/* Area de mensajes */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 p-4 border rounded-lg">
        <Card className="p-3 bg-muted">
          <p className="text-sm">Aquí aparecerá la respuesta de la IA...</p>
          <div className="mt-2 pt-2 border-t text-xs text-blue-500">
            Citations: source-url.com
          </div>
        </Card>
      </div>

      {/* Input de Pregunta */}
      <div className="flex gap-2">
        <Input placeholder="Haz una pregunta sobre los documentos..." />
        <Button>Enviar</Button>
      </div>
    </div>
  );
}

export default ChatInterface;
