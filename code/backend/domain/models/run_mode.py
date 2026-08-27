from enum import StrEnum


class RunMode(StrEnum):
    CREATE_PROJECT = "CREATE_PROJECT"
    CONTINUE_PROJECT = "CONTINUE_PROJECT"
    LEGACY = "LEGACY"
