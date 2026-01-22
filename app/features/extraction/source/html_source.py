import httpx
from bs4 import BeautifulSoup


class HTMLSource:
    def __init__(
        self,
        remove_nav: bool = True,
        remove_footer: bool = True,
        remove_header: bool = True,
        only_main: bool = True,
        allowed_tags: list[str] | None = None,
    ):
        self.remove_nav = remove_nav
        self.remove_footer = remove_footer
        self.remove_header = remove_header
        self.only_main = only_main
        self.allowed_tags = allowed_tags

    async def extract(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        if self.remove_nav:
            for tag in soup.find_all("nav"):
                tag.decompose()

        if self.remove_footer:
            for tag in soup.find_all("footer"):
                tag.decompose()

        if self.remove_header:
            for tag in soup.find_all("header"):
                tag.decompose()

        if self.only_main:
            main = soup.find("main") or soup.find("article")
            if main:
                soup = main

        if self.allowed_tags:
            texts = [el.get_text(strip=True) for el in soup.find_all(self.allowed_tags)]
            return "\n".join(texts)

        return soup.get_text(separator="\n", strip=True)
