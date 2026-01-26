import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Textarea } from "./ui/textarea";

function IngestionInterface() {
  return (
    <div className="p-4 w-full max-w-sm">
      <Card>
        <CardHeader>
          <CardTitle>Ingesta de Datos</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea placeholder="Pega la URL aquí..." />
          <Button className="w-full">Ingerir Documento</Button>
        </CardContent>
      </Card>
    </div>
  );
}

export default IngestionInterface;
