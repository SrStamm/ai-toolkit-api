class SourceException(Exception):
    """ """


class SourceInvalidURLError(SourceException):
    def __init__(self, url: str):
        super().__init__(f"Invalid URL: {url}")
        self.url = url


class SourceTimeoutError(SourceException):
    def __init__(self, url: str):
        super().__init__(f"Timeout while fetching URL: {url}")
        self.url = url


class SourceFetchError(SourceException):
    def __init__(self, url: str, status_code: str) -> None:
        super().__init__(f"Failed to fetch URL {url} (status {status_code})")
        self.url = url
        self.status_code = status_code


class EmptySourceContentError(SourceException):
    def __init__(self, url: str) -> None:
        super().__init__(f"Empty content for URL: {url}")
