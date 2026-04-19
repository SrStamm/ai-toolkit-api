"""
Servicio para la ingestión de documentos en el vector store.
"""

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, UTC
import hashlib
from typing import Callable
from uuid import uuid5, NAMESPACE_DNS

from fastapi import UploadFile
import structlog

from app.api.extraction.schema import ChunkWithMetadata
from app.api.extraction.factory import SourceFactory
from app.api.extraction.exceptions import EmptySourceContentError
from app.api.retrieval_engine.exceptions import ChunkingError
from app.api.retrieval_engine.schemas import Citation
from app.infrastructure.storage.interfaces import FilterContext, VectorStoreInterface
from app.infrastructure.storage.hybrid_ai import HybridEmbeddingService
from app.infrastructure.metrics import (
    documents_ingested_total,
    documents_chunks_total,
)


ProgressCallback = Callable[[int, str], None]


class IngestionService:
    """
    Responsable de la ingestión de documentos (PDF y URL).
    """

    def __init__(
        self,
        vector_store: VectorStoreInterface,
        embed_service: HybridEmbeddingService,
    ) -> None:
        self.vector_store = vector_store
        self.embed_service = embed_service
        self.logger = structlog.get_logger()

    def _generate_deterministic_ids(
        self, chunks: list[ChunkWithMetadata], source: str
    ) -> list[str]:
        """Generate deterministic UUIDs for chunks."""
        hash_ids = [
            hashlib.sha256((chunk.text + source).encode()).hexdigest()
            for chunk in chunks
        ]
        return [str(uuid5(NAMESPACE_DNS, h_id)) for h_id in hash_ids]

    async def _process_ingestion(
        self,
        chunks: list[ChunkWithMetadata],
        source: str,
        domain: str,
        topic: str,
        progress_callback: ProgressCallback | None = None,
    ) -> dict:
        """Process ingestion with optional progress reporting."""

        async def report(percent: int, msg: str) -> None:
            if progress_callback:
                await progress_callback(percent, msg)

        await report(50, "Analyzing chunks...")

        # Generate IDs
        hash_ids = self._generate_deterministic_ids(chunks, source)

        # Check existing
        chunks_in_db = self.vector_store.retrieve(hash_ids)
        ids_in_db = {chunk.id for chunk in chunks_in_db}

        # Separate new vs existing
        news = [
            (hash_ids[i], c, i)
            for i, c in enumerate(chunks)
            if hash_ids[i] not in ids_in_db
        ]

        await report(55, f"Found {len(news)} new, {len(chunks_in_db)} existing chunks")

        timestamp = int(datetime.now(UTC).timestamp())
        old_points_to_upsert: list = []

        # Clean old data
        if chunks_in_db:
            self.vector_store.delete_old_data(source=source, timestamp=timestamp)

        # Process new chunks
        if news:
            await report(60, "Generating embeddings...")

            # Timeout calculation
            estimated_time = len(news) * 0.5
            timeout = max(60, estimated_time * 2)

            BATCH_SIZE = 20

            for i in range(0, len(news), BATCH_SIZE):
                batch = news[i : i + BATCH_SIZE]
                texts_to_process = [item[1].text for item in batch]

                try:
                    vectors = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.embed_service.batch_embed, texts_to_process
                        ),
                        timeout=timeout,
                    )
                except asyncio.TimeoutError:
                    timeout_minutes = timeout / 60
                    raise RuntimeError(
                        f"Embedding timed out after {timeout_minutes:.1f} minutes"
                    )

                if len(vectors) != len(texts_to_process):
                    raise RuntimeError(
                        f"Vector mismatch: expected {len(texts_to_process)}, got {len(vectors)}"
                    )

                new_points = []

                for (h_id, chunk_metadata, original_idx), vector in zip(batch, vectors):
                    point = self.vector_store.create_point(
                        hash_id=h_id,
                        vector={"dense": vector.dense, "sparse": vector.sparse},
                        payload={
                            "text": chunk_metadata.text,
                            "section": chunk_metadata.section,
                            "source": source,
                            "domain": domain.lower(),
                            "topic": topic.lower(),
                            "chunk_index": original_idx,
                            "ingested_at": timestamp,
                        },
                    )
                    new_points.append(point)

                self.vector_store.insert_vector(new_points)

                await report(60, f"Ingested {i + BATCH_SIZE} of {len(news)} chunks")

        # Update existing chunks
        if chunks_in_db:
            await report(85, "Updating existing chunks...")

            for chunk_db in chunks_in_db:
                point = self.vector_store.create_point(
                    hash_id=chunk_db.id,
                    vector=chunk_db.vector,
                    payload={
                        **chunk_db.payload,
                        "ingested_at": timestamp,
                    },
                )
                old_points_to_upsert.append(point)

        # Insert into vector store
        if old_points_to_upsert:
            await report(95, "Storing in vector database...")
            self.vector_store.insert_vector(old_points_to_upsert)

        return {
            "chunks_processed": len(chunks),
            "new": len(news),
            "updated": len(chunks_in_db),
        }

    # ===========================================================================
    # PDF Ingestion
    # ===========================================================================

    async def ingest_pdf_file(
        self,
        file: UploadFile,
        source: str,
        domain: str,
        topic: str,
        progress_callback: ProgressCallback | None = None,
    ) -> dict:
        """Synchronous PDF ingestion."""
        extractor, cleaner = SourceFactory.get_pdf_cleaner()

        raw_data = await extractor.extract(file)

        content = cleaner.clean(raw_data)
        if not content.strip():
            raise EmptySourceContentError(file.filename)

        chunks = cleaner.chunk(content)
        if not chunks:
            raise ChunkingError("No chunks generated")

        result = await self._process_ingestion(
            chunks=chunks,
            source=source,
            domain=domain,
            topic=topic,
            progress_callback=progress_callback,
        )

        self._log_ingestion_metrics("pdf", result)

        return result

    async def ingest_pdf_file_stream(
        self, file: UploadFile, source: str, domain: str, topic: str
    ) -> AsyncIterator[dict]:
        """Streaming PDF ingestion with progress reporting."""

        yield {"progress": 10, "step": "Extracting text from PDF"}

        extractor, cleaner = SourceFactory.get_pdf_cleaner()

        try:
            raw_data = await extractor.extract(file)
        except Exception as e:
            self.logger.error(
                "PDF extraction failed", error=str(e), filename=file.filename
            )
            raise

        yield {"progress": 30, "step": "Cleaning and processing PDF content"}

        content = cleaner.clean(raw_data)
        if not content.strip():
            raise EmptySourceContentError(file.filename)

        chunks = cleaner.chunk(content)
        if not chunks:
            raise ChunkingError("No chunks generated")

        yield {"progress": 50, "step": "Processing chunks..."}

        result = await self._process_ingestion(
            chunks=chunks,
            source=source,
            domain=domain,
            topic=topic,
            progress_callback=None,
        )

        yield {"progress": 95, "step": "Finalizing..."}

        self._log_ingestion_metrics("pdf", result)
        yield {"progress": 100, "step": "Done!", **result}

    # ===========================================================================
    # URL Ingestion
    # ===========================================================================

    async def ingest_document(
        self,
        url: str,
        source: str,
        domain: str,
        topic: str,
        progress_callback: ProgressCallback | None = None,
    ) -> dict:
        """Synchronous URL ingestion."""
        from app.api.extraction.exceptions import SourceException

        extractor, cleaner = SourceFactory.get_extractor_and_cleaner(url)

        try:
            raw_data = await extractor.extract(url)
        except SourceException as e:
            self.logger.warning(
                "Source extraction failed", error=str(e), url=url, source=source
            )
            raise

        content = cleaner.clean(raw_data)
        if not content.strip():
            raise EmptySourceContentError(url)

        chunks = cleaner.chunk(content)
        if not chunks:
            raise ChunkingError("No chunks generated")

        result = await self._process_ingestion(
            chunks=chunks,
            source=source,
            domain=domain,
            topic=topic,
            progress_callback=progress_callback,
        )

        self.logger.info(
            "ingest_completed",
            url=url,
            source=source,
            domain=domain,
            topic=topic,
            **result,
        )

        self._log_ingestion_metrics("url", result)

        return result

    async def ingest_document_stream(
        self, url: str, source: str, domain: str, topic: str
    ) -> AsyncIterator[dict]:
        """Streaming URL ingestion with progress reporting."""
        from app.api.extraction.exceptions import SourceException

        yield {"progress": 10, "step": "Extracting content from URL"}

        extractor, cleaner = SourceFactory.get_extractor_and_cleaner(url)

        try:
            raw_data = await extractor.extract(url)
        except SourceException as e:
            self.logger.warning("Source extraction failed", error=str(e), url=url)
            raise

        yield {"progress": 30, "step": "Cleaning and processing content"}

        content = cleaner.clean(raw_data)
        if not content.strip():
            raise EmptySourceContentError(url)

        chunks = cleaner.chunk(content)
        if not chunks:
            raise ChunkingError("No chunks generated")

        yield {"progress": 50, "step": "Analyzing chunks..."}

        result = await self._process_ingestion(
            chunks=chunks,
            source=source,
            domain=domain,
            topic=topic,
            progress_callback=None,
        )

        yield {"progress": 95, "step": "Finalizing..."}

        self.logger.info(
            "ingest_completed",
            url=url,
            source=source,
            domain=domain,
            topic=topic,
            **result,
        )

        self._log_ingestion_metrics("url", result)
        yield {"progress": 100, "step": "Done!", **result}

    def _log_ingestion_metrics(self, source_type: str, result: dict) -> None:
        """Log ingestion metrics."""
        documents_ingested_total.labels(source_type=source_type, status="success").inc()
        documents_chunks_total.labels(source_type=source_type).inc(
            result["chunks_processed"]
        )
