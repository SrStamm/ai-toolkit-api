import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";

interface MetadataFieldsProps {
  domain: string;
  setDomain: (value: string) => void;
  topic: string;
  setTopic: (value: string) => void;
  loading: boolean;
}

export function MetadataFields({
  domain,
  setDomain,
  topic,
  setTopic,
  loading,
}: MetadataFieldsProps) {
  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground font-medium">Metadatos (opcional)</p>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="domain" className="text-xs">Dominio</Label>
          <Input
            id="domain"
            placeholder="ej: tecnología"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            disabled={loading}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="topic" className="text-xs">Tema</Label>
          <Input
            id="topic"
            placeholder="ej: documentación"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            disabled={loading}
          />
        </div>
      </div>
    </div>
  );
}
