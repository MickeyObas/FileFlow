from enum import StrEnum


class ProcessingStage(StrEnum):
    QUEUED = "queued"
    READING = "reading"
    ANALYZING = "analyzing"
    WRITING_RESULT = "writing_result"
    DONE = "done"
