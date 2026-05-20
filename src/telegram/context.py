"""
Определяет объект контекста вызова, который передается через приложение.
"""
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator, List, Optional
from uuid import UUID, uuid4

from src.db.lib.auth import SupabaseAuth
from src.translator import Translator


@dataclass(frozen=True)
class TimingEntry:
    """Запись о времени выполнения для одной операции."""

    label: str
    duration_ms: float


@dataclass
class RequestContext:
    """
    Содержит информацию о текущем запросе, которая передается
    между функциями и слоями приложения.

    Атрибуты:
        request_id: Уникальный идентификатор для трассировки запроса.
        translator: Экземпляр сервиса-переводчика.
        user_language: Языковой код пользователя (например, 'en', 'ru').
        is_voice_message: Флаг, указывающий что сообщение было получено голосом (для STT/TTS flow).
        can_afford_tts: Флаг, указывающий что у пользователя достаточно средств для TTS ответа.
        timings: Список замеров времени выполнения.
        _start_timer: Временная метка для внутреннего использования (не инициализируется).
    """

    request_id: UUID
    translator: Optional[Translator] = None
    user_language: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    bot_token: Optional[str] = None
    auth_client: Optional[SupabaseAuth] = None
    internal_source: Optional[str] = None
    user_id: Optional[UUID] = None
    active_char_id: Optional[int] = None
    is_new_user: bool = False
    is_voice_message: bool = False
    can_afford_tts: bool = False
    timings: List[TimingEntry] = field(default_factory=list, init=False)
    _start_timer: Optional[float] = field(default=None, init=False)

    @classmethod
    def build(
        cls,
        translator: Optional[Translator] = None,
        user_language: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        bot_token: Optional[str] = None,
        auth_client: Optional[SupabaseAuth] = None,
    ) -> "RequestContext":
        """Фабричный метод для удобного создания экземпляра."""
        return cls(
            request_id=uuid4(),
            translator=translator,
            user_language=user_language,
            telegram_chat_id=telegram_chat_id,
            bot_token=bot_token,
            auth_client=auth_client,
        )

    @contextmanager
    def record_timing(self, label: str) -> Generator[None, None, None]:
        """
        Контекстный менеджер для замера времени выполнения блока кода.
        Пример использования:
            with context.record_timing("external_api_call"):
                # какой-то долгий код
                time.sleep(1)
        """
        start_time = time.perf_counter()
        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            self.timings.append(TimingEntry(label, duration_ms))
