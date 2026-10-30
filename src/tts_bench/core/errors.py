from __future__ import annotations


class TTSBenchError(Exception):
    pass


class EngineNotInstalledError(TTSBenchError):
    def __init__(self, engine: str, hint: str = ""):
        super().__init__(f"Engine '{engine}' is not installed. {hint}".strip())


class WeightsMissingError(TTSBenchError):
    def __init__(self, engine: str, hint: str = ""):
        super().__init__(f"Weights for engine '{engine}' are missing. {hint}".strip())


class EngineAlreadyLoadedError(TTSBenchError):
    pass


class InputLimitError(TTSBenchError):
    pass


class SynthesisError(TTSBenchError):
    def __init__(self, message: str, partial_chunks: list | None = None):
        super().__init__(message)
        # Diagnosis only: never counted in latency statistics.
        self.partial_chunks = partial_chunks or []


class VoiceNotFoundError(TTSBenchError):
    pass


class StreamingNotSupportedError(TTSBenchError):
    pass
