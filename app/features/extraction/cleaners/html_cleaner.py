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

    def _split_by_length(self, clean_text: str, max_chars: int = 300):
        overlap = 100
        chunks = []
        start = 0

        while start < len(clean_text):
            end = start + max_chars
            chunk = clean_text[start:end]
            chunks.append(chunk)
            start = end - overlap

        return chunks

    def chunk(self, clean_text: str) -> list[str]:
        soup = BeautifulSoup(clean_text, "html.parser")
        chunks = []

        # 1. Identificar encabezados como puntos de anclaje
        headers = soup.find_all(["h2", "h3"])

        if not headers:
            return self._split_by_length(soup.get_text(), 1000)

        # 2. Procesar cada sección
        for i, header in enumerate(headers):
            header_text = header.get_text(strip=True).replace("¶", "")
            content = []

            # Buscamos el contenido que hay ENTRE este header y el siguiente
            curr = header.next_sibling
            next_header = headers[i + 1] if i + 1 < len(headers) else None

            while curr and curr != next_header:
                # Si el elemento tiene texto, lo extraemos limpiamente
                if hasattr(curr, "get_text"):
                    text = curr.get_text(strip=True).replace("¶", "")
                    if text:
                        content.append(text)
                curr = curr.next_sibling

            full_section = f"{header_text}\n" + "\n".join(content)

            # 3. Control de tamaño (Tu lógica de Colab)
            if len(full_section) > 1500:
                chunks.extend(self._split_by_length(full_section, 1000))
            else:
                chunks.append(full_section)

        return chunks
