from app.features.extraction.interface import CleanerInterface


class MarkdownCleaner(CleanerInterface):
    def clean(self, raw_content: str) -> str:
        return raw_content
