from io import BytesIO
from fastapi import UploadFile
import pdfplumber


class PDFSource:
    async def extract_data_from_pdf(self, file: UploadFile) -> str:
        # Read file
        file_content = await file.read()

        # Open file
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            full_text = "\n".join(
                page.extract_text() for page in pdf.pages if page.extract_text()
            )
            return full_text
