"""Failure that still writes result.json for the manager to poll."""


class PipelineError(Exception):
    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
