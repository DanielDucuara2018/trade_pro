from typing import Any


class Error(Exception):
    code: int
    reason: str
    description: str

    def __init__(self, **data: Any):
        self.data = data

    def __str__(self):
        fields = [
            ("code", self.code),
            ("reason", self.reason),
            ("data", repr(self.data)),
        ]
        fields_repr = ", ".join(f"{field}={value}" for field, value in fields)
        return fields_repr


class NotDataFound(Error):

    code = 1001
    reason = "not-data-found"
    description = "Not data found in DB"


class NotUserFound(Error):
    code = 1002
    reason = "not-user-found"
    description = "Not user found in DB"
