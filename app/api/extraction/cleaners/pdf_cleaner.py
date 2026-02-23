import re
from ..interface import CleanerInterface



class PDFCleaner(CleanerInterface):
    MIN_CHUNK_LEN = 80

    def clean(self, raw_content: str) -> str:
        if not raw_content:
            return ""

        content = re.sub(r"[\u2010-\u2015]", "-", raw_content)
        content = re.sub(r"(\w+)-\n(\w+)", r"\1\2", content)
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

    def _apply_overlap(self, chunks: list[str], overlap: int) -> list[str]:
        if overlap <= 0:
            return chunks

        overlapped = []

        for i, chunk in enumerate(chunks):
            if i == 0:
                overlapped.append(chunk)
                continue

            prev_chunk = overlapped[-1]

            overlap_text = prev_chunk[-overlap:]
            new_chunk = overlap_text + "\n\n" + chunk

            overlapped.append(new_chunk)

        return overlapped

    def chunk(
        self,
        clean_text: str,
        max_chars: int = 1500,
        overlap: int = 250,
    ) -> list[str]:

        if overlap >= max_chars:
            raise ValueError("overlap must be smaller than max_chars")

        if not clean_text.strip():
            return []

        # 1. Normalize excessive newlines
        text = re.sub(r"\n{2,}", "\n\n", clean_text)

        # 2. Convert newlines inside paragraphs to spaces
        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

        blocks = text.split("\n\n")

        chunks = []
        current_chunk = ""

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            # case individual block is bigger than limit
            if len(block) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                sub_chunks = self._split_by_length(block, max_chars, overlap)
                chunks.extend(sub_chunks)

                continue

            # if add block does not exceed the limit
            if len(current_chunk) + len(block) + 2 <= max_chars:
                if current_chunk:
                    current_chunk += "\n\n" + block
                else:
                    current_chunk = block 
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())

                # new chunk start with current block
                current_chunk = block

        if current_chunk:
            chunks.append(current_chunk.strip())

        return self._apply_overlap(chunks, overlap)
