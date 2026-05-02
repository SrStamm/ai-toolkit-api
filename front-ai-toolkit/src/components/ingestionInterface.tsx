import { useState } from "react";
import { IngestionHeader } from "./ingestion/IngestionHeader";
import { SourceTabs } from "./ingestion/SourceTabs";
import { MetadataFields } from "./ingestion/MetadataFields";
import { ActiveJobsPanel } from "./ingestion/ActiveJobsPanel";

export function IngestionInterface() {
  const [loading, setLoading] = useState(false);
  const [domain, setDomain] = useState("");
  const [topic, setTopic] = useState("");

  return (
    <div className="flex flex-col h-full">
      <IngestionHeader />
      <SourceTabs loading={loading} setLoading={setLoading} domain={domain} topic={topic} />
      <div className="px-4">
        <MetadataFields
          domain={domain}
          setDomain={setDomain}
          topic={topic}
          setTopic={setTopic}
          loading={loading}
        />
      </div>
      <ActiveJobsPanel />
    </div>
  );
}

export default IngestionInterface;
