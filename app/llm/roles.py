from enum import StrEnum


class LLMRole(StrEnum):
    LEADER = "leader"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"
