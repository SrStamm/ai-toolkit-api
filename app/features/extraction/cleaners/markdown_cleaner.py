from ..interface import CleanerInterface


class MarkdownCleaner(CleanerInterface):
    def clean(self, raw_content: str) -> str:
        return raw_content

    def chunk(self, clean_text: str) -> list[str]:
        separated = clean_text.split("##")

        if not separated[0].strip():
            separated.pop(0)

        return ["## " + s.strip().lstrip("#") for s in separated]
