import logging
from decimal import Decimal, InvalidOperation

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.db.lib.billing.balance_transactions import (
    async_get_transactions_by_balance_id,
    async_get_user_balance,
    set_user_balance_via_correction,
)
from src.db.lib.chat_models import ChatUser
from src.telegram.api import send_tg_message
from src.telegram.lib.i18n import get_gettext_for_language

logger = logging.getLogger(__name__)


async def process_flashbalance_command(
    sender_chat_id: int,
    session: AsyncSession,
    user: ChatUser,
    token: str,
    lang_code: str,
    command_text: str,
):
    """
    Debug-команда для просмотра и установки тестового баланса пользователя.
    
    Формат:
        /flashbalance333        → показать текущий баланс
        /flashbalance333 <amount> → установить баланс
        /flashbalance333 list    → показать последние 10 транзакций
    
    Примеры:
        /flashbalance333        → показать текущий баланс
        /flashbalance333 100    → установить баланс 100 токенов
        /flashbalance333 0      → обнулить баланс
        /flashbalance333 1.5    → установить баланс 1.5 токена
        /flashbalance333 list   → показать последние транзакции
    
    Использует корректирующую транзакцию для изменения баланса.
    Все изменения отражаются в таблице транзакций для audit trail.
    
    ВАЖНО: Только для тестирования/отладки!
    """
    _ = get_gettext_for_language(lang_code)
    
    # Парсинг команды
    parts = command_text.split()
    
    # Если параметр не указан - показать текущий баланс
    if len(parts) == 1:
        try:
            current_balance = await async_get_user_balance(
                session, user.id, "TOKEN"
            )
            await send_tg_message(
                sender_chat_id,
                _("💰 Your current token balance: {balance} tokens").format(
                    balance=current_balance
                ),
                token
            )
            logger.info(
                f"[DEBUG] Flashbalance check: user_id={user.id}, "
                f"current_balance={current_balance}"
            )
        except Exception as e:
            await send_tg_message(
                sender_chat_id,
                _("❌ Error getting balance: {error}").format(error=str(e)),
                token
            )
            logger.error(
                f"Error getting balance for user {user.id}: {e}", exc_info=True
            )
        return
    
    # Обработка параметра "list"
    if len(parts) == 2 and parts[1].lower() == "list":
        try:
            # Получаем ID баланса пользователя для токенов
            from src.db.lib.billing.common.content_billing_models import (
                CurrencyType,
                UserBalance,
            )
            
            balance_result = await session.execute(
                select(UserBalance)
                .where(
                    (UserBalance.user_id == user.id)
                    & (UserBalance.balance_type.has(CurrencyType.name == "TOKEN"))
                )
            )
            user_balance_obj = balance_result.scalars().first()
            user_balance_id = user_balance_obj.id if user_balance_obj else None
            
            if not user_balance_id:
                await send_tg_message(
                    sender_chat_id,
                    _("📋 No transactions found (no balance)"),
                    token
                )
                return
            
            # Получаем отфильтрованные транзакции через новую функцию
            # Запрашиваем 20 транзакций из БД, так как после фильтрации пар останется примерно половина
            user_transactions = await async_get_transactions_by_balance_id(
                session=session,
                balance_id=user_balance_id,
                user_id=user.id,
                limit=20,
            )
            
            logger.info(
                f"[DEBUG] Flashbalance list: user_id={user.id}, "
                f"user_balance_id={user_balance_id}, "
                f"filtered_transactions_count={len(user_transactions)}"
            )
            
            if not user_transactions:
                await send_tg_message(
                    sender_chat_id,
                    _("📋 No transactions found"),
                    token
                )
                return
            
            # Ограничиваем до 10 транзакций для отображения
            user_transactions = user_transactions[:10]
            
            # Форматируем транзакции для вывода
            lines = [_("📋 Last {count} transactions:\n").format(count=len(user_transactions))]
            
            # Импорты для определения типа операции
            from src.db.lib.billing.common.content_billing_models import (
                PaidAction,
                TokenPack,
            )
            
            for i, tx in enumerate(user_transactions, 1):
                # Определяем направление с точки зрения пользователя
                is_topup = tx.balance_id_to == user_balance_id
                is_withdraw = tx.balance_id_from == user_balance_id
                
                if is_topup:
                    direction = "➕"
                    amount_str = f"+{abs(tx.amount)}"
                elif is_withdraw:
                    direction = "➖"
                    amount_str = f"-{abs(tx.amount)}"
                else:
                    direction = "↔️"
                    amount_str = f"{tx.amount}"
                
                # Определяем тип операции согласно семантической модели
                # Приоритет: 1) additional_data.reason, 2) service_id (PaidAction/TokenPack), 3) transaction_type
                operation_description = None
                
                # 1. Проверяем additional_data для определения причины (корректировка баланса)
                if tx.additional_data and isinstance(tx.additional_data, dict):
                    reason = tx.additional_data.get("reason")
                    if reason == "test_balance_correction":
                        operation_description = "Balance Correction"
                
                # 2. Если не определили, проверяем service_id (PaidAction, TokenPack, GiftCode)
                if not operation_description and tx.service_id:
                    try:
                        # Сначала проверяем GiftCode (активация промокода)
                        from src.db.lib.gift_codes.common.models import GiftCode
                        gift_code_result = await session.execute(
                            select(GiftCode).where(GiftCode.id == tx.service_id)
                        )
                        gift_code = gift_code_result.scalars().first()
                        if gift_code:
                            operation_description = f"Gift Code ({gift_code.code})"
                    except Exception:
                        pass
                    
                    # Если не GiftCode, проверяем PaidAction (платные действия: Message, Photo и т.д.)
                    if not operation_description:
                        try:
                            paid_action_result = await session.execute(
                                select(PaidAction).where(PaidAction.id == tx.service_id)
                            )
                            paid_action = paid_action_result.scalars().first()
                            if paid_action:
                                # Показываем название из базы данных как есть
                                operation_description = paid_action.name
                        except Exception:
                            pass
                    
                    # Если не PaidAction и не GiftCode, проверяем TokenPack (покупка токенов)
                    if not operation_description:
                        try:
                            token_pack_result = await session.execute(
                                select(TokenPack).where(TokenPack.id == tx.service_id)
                            )
                            token_pack = token_pack_result.scalars().first()
                            if token_pack:
                                operation_description = "Token Purchase"
                        except Exception:
                            pass
                
                # 3. Если все еще не определили, используем общее описание по направлению
                if not operation_description:
                    if is_topup:
                        # Пополнение может быть: покупка токенов, промокод, корректировка
                        operation_description = "Top-up"
                    elif is_withdraw:
                        # Списание: платное действие (Message, Photo и т.д.)
                        operation_description = "Payment"
                    else:
                        operation_description = tx.transaction_type or "Unknown"
                
                # Форматируем дату
                from datetime import datetime
                if isinstance(tx.created_at, datetime):
                    date_str = tx.created_at.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    date_str = str(tx.created_at)
                
                # Источник транзакции
                if tx.source_name:
                    source = tx.source_name.value if hasattr(tx.source_name, 'value') else str(tx.source_name)
                else:
                    source = "N/A"
                
                lines.append(
                    f"{i}. {direction} {amount_str} tokens\n"
                    f"   📅 {date_str}\n"
                    f"   🔖 {operation_description} | 📍 {source}\n"
                )
            
            message = "\n".join(lines)
            
            # Telegram имеет лимит на длину сообщения (4096 символов)
            if len(message) > 4000:
                message = message[:3900] + "\n\n... (truncated)"
            
            await send_tg_message(
                sender_chat_id,
                message,
                token
            )
            
            logger.info(
                f"[DEBUG] Flashbalance list: user_id={user.id}, "
                f"transactions_count={len(user_transactions)}"
            )
        except Exception as e:
            await send_tg_message(
                sender_chat_id,
                _("❌ Error getting transactions: {error}").format(error=str(e)),
                token
            )
            logger.error(
                f"Error getting transactions for user {user.id}: {e}", exc_info=True
            )
        return
    
    # Если параметров больше одного - ошибка формата
    if len(parts) > 2:
        await send_tg_message(
            sender_chat_id,
            _("❌ Invalid format. Use: /flashbalance333 [amount|list]\n"
              "Examples:\n"
              "  /flashbalance333        → show current balance\n"
              "  /flashbalance333 100    → set balance to 100 tokens\n"
              "  /flashbalance333 list   → show last 10 transactions"),
            token
        )
        return
    
    try:
        target_amount = Decimal(parts[1])
        
        if target_amount < 0:
            await send_tg_message(
                sender_chat_id,
                _("❌ Amount cannot be negative"),
                token
            )
            return
        
        # Выполнить корректировку баланса через транзакцию
        correction = await set_user_balance_via_correction(
            session, user.id, target_amount
        )
        
        if correction == 0:
            await send_tg_message(
                sender_chat_id,
                _("✅ Balance already at {amount} tokens").format(amount=target_amount),
                token
            )
        elif correction > 0:
            await send_tg_message(
                sender_chat_id,
                _("✅ Balance adjusted: +{correction} tokens\n💰 New balance: {amount} tokens").format(
                    correction=correction,
                    amount=target_amount
                ),
                token
            )
        else:
            await send_tg_message(
                sender_chat_id,
                _("✅ Balance adjusted: {correction} tokens\n💰 New balance: {amount} tokens").format(
                    correction=correction,
                    amount=target_amount
                ),
                token
            )
        
        logger.info(
            f"[DEBUG] Flashbalance command executed: user_id={user.id}, "
            f"target_amount={target_amount}, correction={correction}"
        )
        
    except (ValueError, InvalidOperation):
        await send_tg_message(
            sender_chat_id,
            _("❌ Invalid amount. Please use a number.\n"
              "Examples:\n"
              "  /flashbalance333        → show current balance\n"
              "  /flashbalance333 100    → set balance to 100 tokens\n"
              "  /flashbalance333 list   → show last 10 transactions"),
            token
        )
        logger.warning(f"Invalid flashbalance command from user {user.id}: {command_text}")
    except Exception as e:
        await send_tg_message(
            sender_chat_id,
            _("❌ Error adjusting balance: {error}").format(error=str(e)),
            token
        )
        logger.error(f"Error in flashbalance command for user {user.id}: {e}", exc_info=True)

