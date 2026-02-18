from .cleaners.markdown_cleaner import MarkdownCleaner
from .cleaners.html_cleaner import HTMLCleaner
from .cleaners.pdf_cleaner import PDFCleaner
from .source.html_source import HTMLSource
from .source.readme_source import READMESource
from .source.pdf_source import PDFSource


class SourceFactory:
    @staticmethod
    def get_extractor_and_cleaner(url: str):
        if "raw.githubusercontent.com" in url or url.endswith(".md"):
            return READMESource(), MarkdownCleaner()

        return HTMLSource(), HTMLCleaner()

    @staticmethod
    def get_pdf_cleaner():  # ← NUEVO
        """Para archivos PDF subidos"""
        return PDFSource(), PDFCleaner()
