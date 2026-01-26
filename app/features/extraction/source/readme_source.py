from app.features.extraction.exceptions import (
    SourceFetchError,
    SourceInvalidURLError,
    SourceTimeoutError,
)
from app.features.extraction.interface import SourceInterface
import httpx


class READMESource(SourceInterface):
    async def extract(self, url: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                response.raise_for_status()

            return response.text
        except httpx.InvalidURL:
            raise SourceInvalidURLError(url)

        except httpx.ReadTimeout:
            raise SourceTimeoutError(url)

        except httpx.HTTPStatusError as e:
            raise SourceFetchError(url, e.response.status_code)
