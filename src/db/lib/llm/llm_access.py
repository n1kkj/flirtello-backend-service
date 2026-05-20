import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import List, Literal, Optional, Tuple, TypedDict

import aisuite as ai
import boto3
import sentry_sdk
from openai import OpenAI
from openai.types.chat.chat_completion import ChatCompletion

from ..config import config
from ..content_models import LLMStats
from .llm_enums import LLMProviders

logger = logging.getLogger(__name__)


class LatencyExtendedOpenaiResponse(ChatCompletion):
    latency: int


class TChatMessage(TypedDict):
    role: Literal["USER", "CHATBOT"]
    message: str


class BedrockLLMModel(Enum):
    COMMAND_R_PLUS = "cohere.command-r-plus-v1:0"
    COMMAND_R = "cohere.command-r-v1:0"


class OpenrouterLLMModel(Enum):
    COMMAND_R = "cohere/command-r-08-2024"


class AisuiteLLMModel(Enum):
    COMMAND_R = "cohere:command-r"


@dataclass(frozen=True)
class LLMDTO:
    llm_provider: Optional[LLMProviders]
    llm_model: Optional[str]


def calculate_llm_response_latency(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        response = func(*args, **kwargs)
        end_time = time.time()

        # Calculate latency in milliseconds
        latency = int((end_time - start_time) * 1000)

        # Add latency to the response
        if isinstance(response, dict):
            response["latency"] = latency
        elif hasattr(response, "__dict__"):  # If response is an object
            response.latency = latency
        else:
            raise TypeError("Response must be a dict or an object with __dict__.")

        return response

    return wrapper


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate_cohere(
        self,
        message: str,
        preamble: str,
        chat_history: List[str],
        model_name: str,
    ):
        pass

    @abstractmethod
    def generate_text(
        self,
        model_name: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        chat_history: Optional[List[TChatMessage]] = None,
    ) -> Tuple[str, LLMStats]:
        pass


class BedrockLLMProvider(BaseLLMProvider):
    def generate_cohere(
        self,
        message: str,
        preamble: str,
        chat_history: List[TChatMessage],
        model_name: str,
    ):
        bedrock = boto3.client(service_name="bedrock-runtime", region_name="us-east-1")
        request = {"message": message}
        if preamble:
            request["preamble"] = preamble
        if chat_history:
            request["chat_history"] = chat_history

        response = bedrock.invoke_model(
            body=json.dumps(request),
            modelId=model_name,
        )

        return response

    def generate_text(
        self,
        model_name: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        chat_history: Optional[List[TChatMessage]] = None,
    ) -> Tuple[str, LLMStats]:
        if model_name.startswith("cohere.command"):
            response = self.generate_cohere(prompt, system_prompt, chat_history, model_name)
            response_body = json.loads(response.get("body").read())
            print(response_body)

            response_text = response_body["text"]
            output_tokens = response["ResponseMetadata"]["HTTPHeaders"].get(
                "x-amzn-bedrock-output-token-count"
            )
            if not output_tokens:
                sentry_sdk.capture_exception(
                    ValueError(
                        f"No 'x-amzn-bedrock-output-token-count' response param, response: {response}"
                    )
                )
                output_tokens = 0
            stats = LLMStats(
                model_id=model_name,
                model_latency=response["ResponseMetadata"]["HTTPHeaders"][
                    "x-amzn-bedrock-invocation-latency"
                ],
                input_tokens=response["ResponseMetadata"]["HTTPHeaders"][
                    "x-amzn-bedrock-input-token-count"
                ],
                output_tokens=output_tokens,
                system_prompt=system_prompt,
                chat_history={"chat_history": chat_history},
                prompt=prompt,
                response=response_text,
                llm_provider=LLMProviders.BEDROCK,
            )
            return response_text, stats

        else:
            raise ValueError(f"Invalid model name: {model_name}")


class OpenRouterLLMProvider(BaseLLMProvider):
    @calculate_llm_response_latency
    def generate_cohere(
        self,
        message: str,
        preamble: Optional[str],
        chat_history: Optional[List[TChatMessage]],
        model_name: str,
    ):
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=config.openrouter_api_key.get_secret_value(),
        )

        if preamble:
            messages = [{"role": "system", "content": preamble}]
        if chat_history:
            messages.extend(
                {
                    "role": OpenRouterLLMProvider.adapt_message_type(msg["role"]),
                    "content": msg["message"],
                }
                for msg in chat_history
            )
        messages.append({"role": "user", "content": message})

        logger.debug(f"{model_name}\n{messages}")

        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
        )
        return completion

    def generate_text(
        self,
        model_name: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        chat_history: Optional[List[TChatMessage]] = None,
    ) -> Tuple[str, LLMStats]:
        response: LatencyExtendedOpenaiResponse = self.generate_cohere(
            prompt, system_prompt, chat_history, model_name
        )

        # Extract response text from the first choice
        response_text = response.choices[0].message.content

        # Extract token usage details from the response
        usage = response.usage
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens

        latency = response.latency

        stats = LLMStats(
            model_id=model_name,
            model_latency=latency,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            system_prompt=system_prompt,
            chat_history={"chat_history": chat_history},
            prompt=prompt,
            response=response_text,
            llm_provider=LLMProviders.OPENROUTER,
        )

        return response_text, stats

    # TODO Refactor and put into adapter
    @staticmethod
    def adapt_message_type(role: Literal["USER", "CHATBOT"]) -> Literal["user", "assistant"]:
        if role == "USER":
            return "user"
        elif role == "CHATBOT":
            return "assistant"
        raise ValueError(f"Unexpected role: {role}")


class AisuiteLLMProvider(BaseLLMProvider):
    @calculate_llm_response_latency
    def generate_cohere(
        self,
        message: str,
        preamble: Optional[str],
        chat_history: Optional[List[TChatMessage]],
        model_name: str,
    ) -> Tuple[str, LLMStats]:

        client = ai.Client()
        if preamble:
            messages = [{"role": "system", "content": preamble}]
        if chat_history:
            messages.extend(
                {
                    "role": OpenRouterLLMProvider.adapt_message_type(msg["role"]),
                    "content": msg["message"],
                }
                for msg in chat_history
            )
        messages.append({"role": "user", "content": message})

        logger.debug(f"{model_name}\n{messages}")

        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
        )
        return completion

    def generate_text(
        self,
        model_name: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        chat_history: Optional[List[TChatMessage]] = None,
    ) -> Tuple[str, LLMStats]:
        response: LatencyExtendedOpenaiResponse = self.generate_cohere(
            prompt, system_prompt, chat_history, model_name
        )

        # Extract response text from the first choice
        response_text = response.choices[0].message.content

        # Extract token usage details from the response
        usage = response.usage
        input_tokens = usage["prompt_tokens"]
        output_tokens = usage["completion_tokens"]

        latency = response.latency

        stats = LLMStats(
            model_id=model_name,
            model_latency=latency,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            system_prompt=system_prompt,
            chat_history={"chat_history": chat_history},
            prompt=prompt,
            response=response_text,
            llm_provider=LLMProviders.AISUITE,
        )

        return response_text, stats

    @staticmethod
    def adapt_message_type(role: Literal["USER", "CHATBOT"]) -> Literal["user", "assistant"]:
        if role == "USER":
            return "user"
        elif role == "CHATBOT":
            return "assistant"
        raise ValueError(f"Unexpected role: {role}")


class LLMGeneratorAdapter:
    def __init__(
        self,
        default_provider: Optional[LLMProviders] = None,
        default_model_name: Optional[str] = None,
    ):
        self.default_provider = default_provider or config.default_llm_provider
        self.default_model_name = default_model_name or config.default_llm_model

        self.provider_mapping: dict[LLMProviders, BaseLLMProvider] = {
            LLMProviders.BEDROCK: BedrockLLMProvider(),
            LLMProviders.OPENROUTER: OpenRouterLLMProvider(),
            LLMProviders.AISUITE: AisuiteLLMProvider(),
        }

    def generate_text(
        self,
        prompt: str,
        preamble: Optional[str] = None,
        chat_history: Optional[List[str]] = None,
        character_llm_dto: Optional[LLMDTO] = None,
    ) -> Tuple[str, LLMStats]:
        if character_llm_dto is None:
            llm_dto = LLMDTO(
                llm_provider=self.default_provider,
                llm_model=self.default_model_name,
            )
        else:
            llm_dto = character_llm_dto

        provider_processor = self.provider_mapping[llm_dto.llm_provider]
        return provider_processor.generate_text(
            model_name=llm_dto.llm_model,
            prompt=prompt,
            system_prompt=preamble,
            chat_history=chat_history,
        )
