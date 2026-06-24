from abc import ABC, abstractmethod
from typing import Generic, TypeVar

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class Agent(ABC, Generic[InputT, OutputT]):
    """Base interface for replaceable opportunity-intelligence agents."""

    @abstractmethod
    async def run(self, payload: InputT) -> OutputT:
        """Process an input payload into a structured output."""
