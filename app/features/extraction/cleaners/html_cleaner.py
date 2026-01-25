from bs4 import BeautifulSoup
from app.features.extraction.interface import CleanerInterface


class HTMLCleaner(CleanerInterface):
    def clean(self, raw_content: str) -> str:
        soup = BeautifulSoup(raw_content, "html.parser")

        for tag in soup(["nav", "footer", "header", "script", "style"]):
            tag.decompose()

        main = soup.find("main") or soup.find("article") or soup

        lines = [line.strip() for line in main.get_text(separator="\n").splitlines()]
        return "\n".join(line for line in lines if line)

    def chunk(self, clean_text: str):
        max_chars = 300
        overlap = 100
        chunks = []
        start = 0

        while start < len(clean_text):
            end = start + max_chars
            chunk = clean_text[start:end]
            chunks.append(chunk)
            start = end - overlap

        return chunks
