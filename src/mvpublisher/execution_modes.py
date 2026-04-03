from enum import Enum


class ExecutionMode(str, Enum):
    AUTOPUBLISH = "autopublish"
    AUTOFILL_ONLY = "autofill_only"

