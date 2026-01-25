from .cleaners.markdown_cleaner import MarkdownCleaner
from .cleaners.html_cleaner import HTMLCleaner
from .source.html_source import HTMLSource
from .source.readme_source import READMESource


class SourceFactory:
    @staticmethod
    def get_extractor_and_cleaner(url: str):
        if "raw.githubusercontent.com" in url or url.endswith(".md"):
            return READMESource(), MarkdownCleaner()

        return HTMLSource(), HTMLCleaner()
