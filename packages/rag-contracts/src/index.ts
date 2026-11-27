import type { operations, paths } from "./generated/api.js";

export type SearchRequest = operations["searchDocuments"]["requestBody"]["content"]["application/json"];
export type IngestRequest = operations["ingestDocumentJob"]["requestBody"]["content"]["application/json"];

export type SearchResponse = operations["searchDocuments"]["responses"][200]["content"]["application/json"];
export type ListDocumentsResponse = operations["listDocuments"]["responses"][200]["content"]["application/json"];
export type DeleteDocumentResponse = operations["deleteDocument"]["responses"][200]["content"]["application/json"];
export type DocumentMetadataResponse = operations["getDocumentMetadata"]["responses"][200]["content"]["application/json"];
export type IngestJobResponse = operations["ingestDocumentJob"]["responses"][200]["content"]["application/json"];
export type JobStatusResponse = operations["getJobStatus"]["responses"][200]["content"]["application/json"];

export type RagJobStatus = JobStatusResponse["status"];
export type RagPath = keyof paths;
export type RagOperationId = keyof operations;
