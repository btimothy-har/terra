class NewsGraphError(Exception):
    pass


class NewsGraphExtractionError(NewsGraphError):
    pass


class NewsGraphLLMError(NewsGraphError):
    pass
