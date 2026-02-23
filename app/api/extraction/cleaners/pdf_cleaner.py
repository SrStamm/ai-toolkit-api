import re
from ..schema import ChunkWithMetadata
from ..interface import CleanerInterface


class PDFCleaner(CleanerInterface):
    MIN_CHUNK_LEN = 80

    def clean(self, raw_content: str) -> str:
        if not raw_content:
            return ""

        content = re.sub(r"[\u2010-\u2015]", "-", raw_content)
        # putting together cut words
        content = re.sub(r"(\w+)-\n(\w+)", r"\1\2", content)

        # protect headers before hanging new lines
        content = re.sub(r"\n([A-Z][a-zA-Z ]{2,40})\n", r"\n\n\1\n\n", content)

        content = re.sub(r"\n(?=[a-z])", " ", content)
        content = re.sub(r"\|\s*\d+\s*$", "", content)
        content = re.sub(r"<s>\[INST\].*?\[/INST\]", "", content, flags=re.DOTALL)

        content = re.sub(r"\.{5,}\s*\d+$", "", content, flags=re.MULTILINE)

        # Remove index-like lines
        content = re.sub(r"^Index\s+\|\s+\d+.*$", "", content, flags=re.MULTILINE)

        # Remove lines with many numbers separated by commas
        content = re.sub(r"^[A-Za-z ,\-]+\s\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*$", "", content, flags=re.MULTILINE)

        content = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", content)
        content = re.sub(r"[ \t]+", " ", content)
        content = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", content)
        content = re.sub(r"\n{3,}", "\n\n", content)

        content = re.sub(r"^[A-Z][^\n]{0,80}\|\s*\d+\s*$", "", content, flags=re.MULTILINE)
        content = re.sub(r"^\s*\d+\s*$", "", content, flags=re.MULTILINE)
        content = re.sub(r"<s>\[INST\].*?\[/INST\]", "", content, flags=re.DOTALL)


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
        if not line or len(line) > 80:
            return False

        # Excluir líneas de índice/TOC (tienen puntos suspensivos o número de página al final)
        if re.search(r"\.{3,}", line):
            return False
        if re.search(r"\|\s*(v{1,3}i{0,3}|ix|x{1,3}|\d+)\s*$", line):
            return False

        # Heading numerado tipo "1.2 Algo"
        if re.match(r"^[0-9]+\.(?:[0-9]+\.?)?\s+[A-Z]", line):
            return True

        # Todo mayúsculas
        words = line.split()
        if len(words) >= 2 and line.isupper():
            return True

        # Title case estricto: todas las palabras principales capitalizadas, sin punto final
        if (len(line) < 60 
            and not line.endswith(".")
            and not re.search(r"\d", line)  # sin números
            and len(words) >= 2
            and all(w[0].isupper() for w in words if len(w) > 3)):
            return True

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

    def chunk(
        self,
        clean_text: str,
        max_chars: int = 1500,
        overlap: int = 250
    ) -> list[ChunkWithMetadata]:
        if overlap >= max_chars:
            raise ValueError("overlap must be smaller than max_chars")
        if not clean_text.strip():
            return []

        text = re.sub(r"\n{2,}", "\n\n", clean_text)
        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)


        in_toc = False
        blocks = text.split("\n\n")

        for b in blocks[:30]:
            print(repr(b))
            print("IS HEADING:", self._is_heading(b))
            print("---")

        result: list[ChunkWithMetadata] = []
        current_text = ""
        current_section = None

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            if "Table of Contents" in block or re.match(r"^(Table of Contents|Contents)$", block):
                in_toc = True
                continue

            if in_toc:
                if len(block) > 300:
                    in_toc = False
                else:
                    continue

            if self._is_heading(block):
                current_section = block
                continue

            if len(block) > max_chars:
                if current_text:
                    result.append(ChunkWithMetadata(text=current_text.strip(), section=current_section))
                sub_chunks = self._split_by_length(block, max_chars, overlap)
                for sc in sub_chunks:
                    result.append(ChunkWithMetadata(text=sc, section=current_section))
                current_text = sub_chunks[-1][-overlap:] if sub_chunks else ""
                continue

            if len(current_text) + len(block) + 2 <= max_chars:
                current_text = current_text + "\n\n" + block if current_text else block
            else:
                if current_text:
                    result.append(ChunkWithMetadata(text=current_text.strip(), section=current_section))
                overlap_seed = result[-1].text[-overlap:] if result else ""
                current_text = overlap_seed + "\n\n" + block if overlap_seed else block

        if current_text:
            result.append(ChunkWithMetadata(text=current_text.strip(), section=current_section))

        return result
