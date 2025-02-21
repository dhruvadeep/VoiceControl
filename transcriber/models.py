"""Contains pydantic base classes for requests and responses."""
from pydantic import BaseModel, Field


class CommandResponse(BaseModel):
    """Gives command along with additional information.

    Parameters
    ----------
    command: str
    additional: str

    command is the base reduced command
    additional is the additional information associated with the command in the user query

    """

    command: str = Field(..., strict=True)
    additional: str = Field(..., strict=True)

class CommandListResponse(BaseModel):
    """Gives a list of CommandResponse.

    Parameters
    ----------
    commands: list[CommandResponse]

    commands is the list of CommandResponse objects

    """

    commands: list[CommandResponse] = Field(..., strict=True)

class FinalResponse(BaseModel):
    """Gives a list of CommandListResponse as response and transcription as message.

    Parameters
    ----------
    response: CommandListResponse
    message: str

    response is CommandListResponse object
    message is a string

    """

    response: CommandListResponse = Field(..., strict=True)
    message: str = Field(..., strict=True)
