from io import StringIO
import chardet
from fastapi import HTTPException, UploadFile
import pandas as pd


class CSVSource:
    async def extract_data_from_csv(self, file: UploadFile) -> str:
        # Read file
        file_content = await file.read()

        # Detect encoding automatically
        detector = chardet.universaldetector.UniversalDetector()
        detector.reset()
        detector.feed(file_content)
        detector.close()
        detected = detector.result
        encoding = detected["encoding"] or "iso-8859-1"

        # Decode file
        try:
            text = file_content.decode(encoding)
        except UnicodeDecodeError:
            text = file_content.decode("utf-8", errors="replace")

        # Convert file to dataframe
        try:
            df = pd.read_csv(StringIO(text), sep=";", on_bad_lines="skip")
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Error procesando CSV: {str(e)}"
            )

        if df.empty:
            raise ValueError("El CSV está vacío o no se pudo parsear")

        return df.head(5).to_string(index=False)
