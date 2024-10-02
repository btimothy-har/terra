from jobs.pipelines.exceptions import PipelineError


class NewsGraphError(PipelineError):
    pass


class NewsGraphExtractionError(NewsGraphError):
    pass


class NewsGraphLLMError(NewsGraphError):
    pass
