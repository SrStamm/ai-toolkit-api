import re
from ..interface import CleanerInterface



class PDFCleaner(CleanerInterface):
    MIN_CHUNK_LEN = 80

    def clean(self, raw_content: str) -> str:
        if not raw_content:
            return ""

        content = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", raw_content)
        content = re.sub(r"[ \t]+", " ", content)
        content = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", content)
        content = re.sub(r"\n{3,}", "\n\n", content)

        lines = [line.strip() for line in content.split("\n")]

        clean_lines = []
        prev_empty = False
        for line in lines:
            if line:
                clean_lines.append(line)
                prev_empty = False
            elif not prev_empty:
                clean_lines.append(line)
                prev_empty = True

        return "\n".join(clean_lines).strip()

    def _is_heading(self, line: str) -> bool:
        if not line or len(line) > 100:
            return False

        if re.match(r"^[0-9]+\.(?:[0-9]+\.?)?\s+[A-Z]", line):
            return True

        words = line.split()
        if len(words) >= 2 and line.isupper():
            return True

        if len(line) < 60 and not line.endswith(".") and len(words) >= 2:
            return line[0].isupper()

        return False

    def _split_by_length(
        self, text: str, max_chars: int = 1000, overlap: int = 100
    ) -> list[str]:
        chunks = []
        start = 0

        while start < len(text):
            end = start + max_chars
            chunk = text[start:end]

            if end < len(text):
                last_period = chunk.rfind(". ")
                last_newline = chunk.rfind("\n")
                cut = max(last_period, last_newline)

                if cut > max_chars * 0.7:
                    chunk = chunk[: cut + 1]
                    end = start + len(chunk)

            chunks.append(chunk.strip())
            start = end - overlap

        return chunks

    def chunk(self, clean_text: str) -> list[str]:
        if not clean_text.strip():
            return []

        lines = clean_text.split("\n")
        chunks = []

        current_heading = None
        buffer = []

        def flush():
            if not buffer:
                return

            text = "\n".join(buffer).strip()

            if len(text) < self.MIN_CHUNK_LEN:
                buffer.clear()
                return

            if current_heading:
                text = f"{current_heading}\n{text}"

            if len(text) > 1500:
                chunks.extend(self._split_by_length(text))
            else:
                chunks.append(text)

            buffer.clear()

        for line in lines:
            if not line:
                buffer.append("")
                continue

            if self._is_heading(line):
                flush()
                current_heading = line
            else:
                buffer.append(line)

        flush()
        return chunks
