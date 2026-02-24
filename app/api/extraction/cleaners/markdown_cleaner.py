import re
from ..interface import CleanerInterface
from ..schema import ChunkWithMetadata


class MarkdownCleaner(CleanerInterface):
    MAX_CHARS = 1500
    OVERLAP = 250

    def clean(self, raw_content: str) -> str:
        return raw_content

    def chunk(self, clean_text: str) -> list[ChunkWithMetadata]:
        # Separar por ## o ###
        sections = re.split(r"(?=^#{1,3} )", clean_text, flags=re.MULTILINE)
        sections = [s.strip() for s in sections if s.strip()]

        result: list[ChunkWithMetadata] = []

        for section in sections:
            # Extraer el heading de la primera línea
            lines = section.split("\n", 1)
            heading_line = lines[0].strip()
            section_name = re.sub(r"^#+\s*", "", heading_line)
            body = lines[1].strip() if len(lines) > 1 else ""

            full = f"{heading_line}\n{body}" if body else heading_line

            if len(full) <= self.MAX_CHARS:
                result.append(ChunkWithMetadata(text=full, section=section_name))
            else:
                # Partir por párrafos manteniendo el section
                paragraphs = body.split("\n\n")
                current = heading_line
                for para in paragraphs:
                    para = para.strip()
                    if not para:
                        continue
                    if len(current) + len(para) + 2 <= self.MAX_CHARS:
                        current = current + "\n\n" + para
                    else:
                        result.append(ChunkWithMetadata(text=current.strip(), section=section_name))
                        overlap_seed = current[-self.OVERLAP:]
                        current = overlap_seed + "\n\n" + para
                if current:
                    result.append(ChunkWithMetadata(text=current.strip(), section=section_name))

        return result
