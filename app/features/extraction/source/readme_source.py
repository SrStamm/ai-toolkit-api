import httpx


class READMESource:
    async def extract(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()

        return response.text
