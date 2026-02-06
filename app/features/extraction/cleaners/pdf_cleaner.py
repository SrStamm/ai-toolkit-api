import re
from ..interface import CleanerInterface


class PDFCleaner(CleanerInterface):
    def clean(self, raw_content: str) -> str:
        """
        Limpia el contenido extraído de un PDF.
        - Elimina múltiples saltos de línea consecutivos
        - Elimina espacios en blanco excesivos
        - Elimina caracteres de control y caracteres raros
        - Normaliza guiones de palabras cortadas
        """
        if not raw_content:
            return ""

        # Eliminar caracteres de control excepto \n y \t
        content = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", raw_content)

        # Normalizar espacios en blanco dentro de líneas
        content = re.sub(r"[ \t]+", " ", content)

        # Intentar unir palabras cortadas al final de línea (guiones de separación)
        # Ejemplo: "proce-\nso" -> "proceso"
        content = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", content)

        # Reemplazar múltiples saltos de línea por máximo 2
        content = re.sub(r"\n{3,}", "\n\n", content)

        # Eliminar espacios al inicio y final de cada línea
        lines = [line.strip() for line in content.split("\n")]

        # Filtrar líneas vacías repetidas
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
        """
        Detecta si una línea parece ser un encabezado.
        Criterios:
        - Línea corta (< 100 caracteres)
        - Empieza con número/letra seguido de punto (1., A., etc.)
        - Todo en mayúsculas
        - Termina sin punto
        """
        if not line or len(line) > 100:
            return False

        # Patrón de numeración: "1. ", "1.1 ", "A. ", etc.
        if re.match(r"^[0-9]+\.(?:[0-9]+\.?)?\s+[A-Z]", line):
            return True

        # Todo en mayúsculas (con al menos 3 palabras)
        words = line.split()
        if len(words) >= 2 and line.isupper():
            return True

        # Línea corta sin punto final que parece título
        if len(line) < 60 and not line.endswith(".") and len(words) >= 2:
            if line[0].isupper():
                return True

        return False

    def _split_by_length(
        self, text: str, max_chars: int = 1000, overlap: int = 100
    ) -> list[str]:
        """
        Divide texto largo en chunks con overlap para mantener contexto.
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + max_chars
            chunk = text[start:end]

            # Si no es el último chunk, intentar cortar en el último punto o salto de línea
            if end < len(text):
                # Buscar último punto seguido de espacio o salto de línea
                last_period = chunk.rfind(". ")
                last_newline = chunk.rfind("\n")

                cut_point = max(last_period, last_newline)
                if cut_point > max_chars * 0.7:  # Solo si está en el último 30%
                    chunk = chunk[: cut_point + 1].strip()
                    end = start + len(chunk)

            chunks.append(chunk.strip())
            start = end - overlap

        return chunks

    def chunk(self, clean_text: str) -> list[str]:
        """
        Divide el PDF en chunks semánticos.
        Estrategia:
        1. Detectar encabezados como puntos de división
        2. Agrupar contenido bajo cada encabezado
        3. Si un chunk es muy largo (>1500 chars), dividirlo con overlap
        4. Si no hay encabezados, división por longitud con overlap
        """
        if not clean_text.strip():
            return []

        lines = clean_text.split("\n")
        chunks = []
        current_chunk = []
        current_heading = None

        for line in lines:
            line = line.strip()

            if not line:
                if current_chunk:
                    current_chunk.append("")
                continue

            # Detectar si es un encabezado
            if self._is_heading(line):
                # Guardar chunk anterior si existe
                if current_chunk:
                    chunk_text = "\n".join(current_chunk).strip()
                    if chunk_text:
                        # Si el chunk es muy largo, dividirlo
                        if len(chunk_text) > 1500:
                            chunks.extend(self._split_by_length(chunk_text, 1000, 100))
                        else:
                            chunks.append(chunk_text)

                # Iniciar nuevo chunk con el encabezado
                current_chunk = [line]
                current_heading = line
            else:
                current_chunk.append(line)

        # Procesar último chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk).strip()
            if chunk_text:
                if len(chunk_text) > 1500:
                    chunks.extend(self._split_by_length(chunk_text, 1000, 100))
                else:
                    chunks.append(chunk_text)

        # Si no se generaron chunks (no había encabezados claros),
        # hacer división por longitud del texto completo
        if not chunks:
            chunks = self._split_by_length(clean_text, 1000, 100)

        return chunks
