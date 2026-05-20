from enum import Enum


class LLMProviders(Enum):
    BEDROCK = "bedrock"
    OPENROUTER = "openrouter"
    AISUITE = "aisuite"


class LLMModels(Enum):
    DUMMY = "dummy"
