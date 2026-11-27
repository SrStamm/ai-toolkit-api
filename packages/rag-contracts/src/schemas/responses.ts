import { z } from "zod";
import type {
  DeleteDocumentResponse,
  DocumentMetadataResponse,
  IngestJobResponse,
  JobStatusResponse,
  ListDocumentsResponse,
  SearchResponse,
} from "../index.js";

type SourceMetadata = ListDocumentsResponse["metadata"]["documents"][number];

const sourceMetadataSchema = z.object({
  source: z.string(),
  display_name: z.string().nullable().optional(),
  domain: z.string(),
  topic: z.string(),
  chunk_count: z.number().int(),
  last_ingested: z.number().int(),
}) satisfies z.ZodType<SourceMetadata>;

export const searchResponseSchema = z.object({
  context: z.string(),
  citations: z.array(z.string()),
}) satisfies z.ZodType<SearchResponse>;

export const listDocumentsResponseSchema = z.object({
  status: z.literal("success"),
  metadata: z.object({
    documents: z.array(sourceMetadataSchema),
    count: z.number().int(),
  }),
  output: z.string(),
}) satisfies z.ZodType<ListDocumentsResponse>;

export const documentMetadataResponseSchema = z.object({
  status: z.literal("success"),
  metadata: sourceMetadataSchema,
  output: z.string(),
}) satisfies z.ZodType<DocumentMetadataResponse>;

export const deleteDocumentResponseSchema = z.object({
  status: z.literal("deleted"),
  source: z.string(),
}) satisfies z.ZodType<DeleteDocumentResponse>;

export const ingestJobResponseSchema = z.object({
  status: z.literal("queued"),
  job_id: z.string(),
}) satisfies z.ZodType<IngestJobResponse>;

export const jobStatusResponseSchema = z.object({
  job_id: z.string(),
  status: z.enum(["queued", "running", "completed", "failed"]),
  progress: z.number().int().nullable().optional(),
  step: z.string(),
  error: z.string().nullable().optional(),
}) satisfies z.ZodType<JobStatusResponse>;
