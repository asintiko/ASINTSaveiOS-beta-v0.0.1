import logging
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot, Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.localization import DEFAULT_LANGUAGE, get_text
from bot.markups.admin import (
    admin_panel_kb,
    back_to_panel_kb,
    subscription_confirm_kb,
    subscription_period_kb,
    subscription_plan_kb,
)
from bot.states import AdminPanel
from bot.subscription import apply_subscription
from bot.utils.admin_reports import generate_statistics_report, generate_users_report
from bot.utils.analytics import record_command_usage, record_manual_subscription_grant
from config import ADMIN_IDS
from db import Spyusers
from logging_config import register_log_translations


logger = logging.getLogger(__name__)

register_log_translations(
    {
        "Failed to deliver admin report %s": {
            "ru": "Не удалось отправить админский отчёт %s",
        },
        "Unauthorized admin access attempt by user_id=%s": {
            "ru": "Несанкционированная попытка доступа в админ-панель от user_id=%s",
        },
        "Unauthorized admin callback from user_id=%s": {
            "ru": "Несанкционированный административный callback от user_id=%s",
        },
        "Failed to notify user %s about manual subscription: %s": {
            "ru": "Не удалось уведомить пользователя %s о вручную выданной подписке: %s",
        },
        "Failed to remove admin panel keyboard": {
            "ru": "Не удалось убрать клавиатуру админ-панели",
        },
        "Failed to notify user %s about ban status change: %s": {
            "ru": "Не удалось уведомить пользователя %s об изменении статуса блокировки: %s",
        },
    }
)


def admin_router() -> Router:
    router = Router(name="admin_router")

    def _is_admin(user_id: Optional[int]) -> bool:
        return user_id in ADMIN_IDS if user_id is not None else False

    async def _ensure_profile(session: AsyncSession, message: Message) -> Optional[Spyusers]:
        from_user = message.from_user
        if from_user is None:
            return None

        stmt = select(Spyusers).where(Spyusers.user_id == from_user.id)
        user = await session.scalar(stmt)
        now = datetime.utcnow()
        if user:
            user.username = from_user.username
            user.user_full_name = from_user.full_name
            user.updated_at = now
            user.last_seen_at = now
        else:
            user = Spyusers(
                user_id=from_user.id,
                username=from_user.username,
                user_full_name=from_user.full_name,
                is_banned=False,
                created_at=now,
                updated_at=now,
                last_seen_at=now,
            )
            session.add(user)
        return user

    async def _get_or_create_user_by_id(
        session: AsyncSession,
        user_id: int,
        *,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> Spyusers:
        stmt = select(Spyusers).where(Spyusers.user_id == user_id)
        user = await session.scalar(stmt)
        now = datetime.utcnow()
        if user is None:
            user = Spyusers(
                user_id=user_id,
                username=username,
                user_full_name=full_name,
                is_banned=False,
                created_at=now,
                updated_at=now,
                last_seen_at=now,
            )
            session.add(user)
        else:
            if username is not None:
                user.username = username
            if full_name is not None:
                user.user_full_name = full_name
            user.updated_at = now
            user.last_seen_at = now
        return user

    async def _resolve_target_user(
        message: Message,
        session: AsyncSession,
    ) -> Optional[Spyusers]:
        if message.forward_from:
            target = message.forward_from
            return await _get_or_create_user_by_id(
                session,
                target.id,
                username=target.username,
                full_name=target.full_name,
            )

        text = (message.text or "").strip()
        if not text:
            await message.answer(
                "Отправьте числовой ID пользователя или перешлите его сообщение.",
            )
            return None

        if text.startswith("@"):
            username = text[1:]
            stmt = select(Spyusers).where(Spyusers.username == username)
            user = await session.scalar(stmt)
            if user is None:
                await message.answer(
                    "Пользователь с указанным username не найден в базе. Отправьте ID или пересланное сообщение.",
                )
                return None
            return user

        if text.isdigit():
            user_id = int(text)
            return await _get_or_create_user_by_id(session, user_id)

        await message.answer(
            "Не удалось распознать пользователя. Пришлите ID или пересланное сообщение.",
        )
        return None

    def _format_subscription_snapshot(user: Spyusers) -> str:
        plan_key = (user.subscription_tier or "free").lower()
        plan_name = get_text(f"subscription_plan_{plan_key}", DEFAULT_LANGUAGE)
        if plan_key == "free":
            return plan_name
        if user.subscription_expires_at:
            expires = user.subscription_expires_at.strftime("%Y-%m-%d %H:%M UTC")
            return f"{plan_name} (до {expires})"
        return f"{plan_name} (бессрочно)"

    async def _send_report(
        callback: CallbackQuery,
        session: AsyncSession,
        generator,
    ) -> None:
        report = await generator(session)
        try:
            document = FSInputFile(report.path, filename=report.filename)
            await callback.message.answer_document(
                document=document,
                caption=report.caption,
                reply_markup=admin_panel_kb(),
            )
        except Exception:
            logger.exception("Failed to deliver admin report %s", report.path)
            await callback.message.answer(
                "Не удалось отправить отчёт. Попробуйте снова позже.",
                reply_markup=admin_panel_kb(),
            )
        finally:
            report.cleanup()

    @router.message(Command("admin"))
    async def admin_entry(message: Message, session: AsyncSession, state: FSMContext) -> None:
        user_id = message.from_user.id if message.from_user else None
        if not _is_admin(user_id):
            await message.answer("У вас нет доступа к административной панели.")
            logger.warning("Unauthorized admin access attempt by user_id=%s", user_id)
            return

        await record_command_usage(session, "admin")
        await state.clear()
        await _ensure_profile(session, message)
        await message.answer(
            "<b>Админ-панель</b>\nВыберите действие из списка ниже:",
            parse_mode="HTML",
            reply_markup=admin_panel_kb(),
        )

    @router.callback_query(F.data == "admin_users")
    async def admin_users(
        callback: CallbackQuery,
        session: AsyncSession,
    ) -> None:
        user_id = callback.from_user.id if callback.from_user else None
        if not _is_admin(user_id):
            await callback.answer("Нет доступа", show_alert=True)
            logger.warning("Unauthorized admin callback from user_id=%s", user_id)
            return
        await callback.answer()
        await _send_report(callback, session, generate_users_report)

    @router.callback_query(F.data == "admin_stats")
    async def admin_stats(
        callback: CallbackQuery,
        session: AsyncSession,
    ) -> None:
        user_id = callback.from_user.id if callback.from_user else None
        if not _is_admin(user_id):
            await callback.answer("Нет доступа", show_alert=True)
            logger.warning("Unauthorized admin callback from user_id=%s", user_id)
            return
        await callback.answer()
        await _send_report(callback, session, generate_statistics_report)

    @router.callback_query(F.data == "admin_subscribe")
    async def admin_subscribe_entry(
        callback: CallbackQuery,
        state: FSMContext,
    ) -> None:
        user_id = callback.from_user.id if callback.from_user else None
        if not _is_admin(user_id):
            await callback.answer("Нет доступа", show_alert=True)
            logger.warning("Unauthorized admin callback from user_id=%s", user_id)
            return
        await callback.answer()
        await state.clear()
        await state.set_state(AdminPanel.subscription_user)
        await callback.message.answer(
            "Отправьте ID пользователя или перешлите любое его сообщение.",
            reply_markup=back_to_panel_kb(),
        )

    @router.callback_query(F.data == "admin_subscribe_cancel")
    async def admin_subscribe_cancel(
        callback: CallbackQuery,
        state: FSMContext,
    ) -> None:
        user_id = callback.from_user.id if callback.from_user else None
        if not _is_admin(user_id):
            await callback.answer("Нет доступа", show_alert=True)
            return
        await callback.answer("Отменено")
        await state.clear()
        await callback.message.answer(
            "Операция выдачи подписки отменена.",
            reply_markup=admin_panel_kb(),
        )

    @router.callback_query(F.data == "admin_subscribe_back_plan")
    async def admin_subscribe_back_plan(
        callback: CallbackQuery,
        state: FSMContext,
    ) -> None:
        if not _is_admin(callback.from_user.id if callback.from_user else None):
            await callback.answer("Нет доступа", show_alert=True)
            return
        data = await state.get_data()
        if not data.get("target_user_id"):
            await callback.answer("Сначала выберите пользователя", show_alert=True)
            return
        await callback.answer()
        await state.set_state(AdminPanel.subscription_plan)
        await callback.message.answer(
            "Выберите тариф для выдачи:",
            reply_markup=subscription_plan_kb(),
        )

    @router.callback_query(F.data == "admin_subscribe_back_period")
    async def admin_subscribe_back_period(
        callback: CallbackQuery,
        state: FSMContext,
    ) -> None:
        if not _is_admin(callback.from_user.id if callback.from_user else None):
            await callback.answer("Нет доступа", show_alert=True)
            return
        data = await state.get_data()
        if not data.get("plan"):
            await callback.answer("Сначала выберите тариф", show_alert=True)
            return
        await callback.answer()
        await state.set_state(AdminPanel.subscription_period)
        await callback.message.answer(
            "Выберите период действия подписки:",
            reply_markup=subscription_period_kb(),
        )

    @router.callback_query(F.data.startswith("admin_subscribe_plan:"))
    async def admin_subscribe_plan(
        callback: CallbackQuery,
        state: FSMContext,
    ) -> None:
        if not _is_admin(callback.from_user.id if callback.from_user else None):
            await callback.answer("Нет доступа", show_alert=True)
            return
        data = await state.get_data()
        if not data.get("target_user_id"):
            await callback.answer("Сначала выберите пользователя", show_alert=True)
            return
        plan = callback.data.split(":", 1)[1]
        if plan not in {"lite", "pro"}:
            await callback.answer("Неизвестный тариф", show_alert=True)
            return
        await callback.answer()
        await state.update_data(plan=plan)
        await state.set_state(AdminPanel.subscription_period)
        plan_name = get_text(f"subscription_plan_{plan}", DEFAULT_LANGUAGE)
        await callback.message.answer(
            f"Выбран тариф: <b>{plan_name}</b>\nТеперь выберите период действия.",
            parse_mode="HTML",
            reply_markup=subscription_period_kb(),
        )

    @router.callback_query(F.data.startswith("admin_subscribe_period:"))
    async def admin_subscribe_period(
        callback: CallbackQuery,
        state: FSMContext,
        session: AsyncSession,
    ) -> None:
        if not _is_admin(callback.from_user.id if callback.from_user else None):
            await callback.answer("Нет доступа", show_alert=True)
            return
        period = callback.data.split(":", 1)[1]
        if period not in {"week", "month", "forever"}:
            await callback.answer("Неизвестный период", show_alert=True)
            return
        data = await state.get_data()
        target_user_id = data.get("target_user_id")
        plan = data.get("plan")
        if not target_user_id or not plan:
            await callback.answer("Не хватает данных. Начните заново.", show_alert=True)
            return

        stmt = select(Spyusers).where(Spyusers.user_id == target_user_id)
        target_user = await session.scalar(stmt)
        if target_user is None:
            target_user = await _get_or_create_user_by_id(session, target_user_id)

        await callback.answer()
        await state.update_data(period=period)
        await state.set_state(AdminPanel.subscription_confirmation)

        plan_name = get_text(f"subscription_plan_{plan}", DEFAULT_LANGUAGE)
        if period == "forever":
            period_label = "Бессрочно"
        else:
            period_label = get_text(f"subscription_period_{period}", DEFAULT_LANGUAGE)
        snapshot = _format_subscription_snapshot(target_user)

        confirmation_text = (
            "<b>Подтверждение выдачи подписки</b>\n\n"
            f"<b>ID:</b> <code>{target_user.user_id}</code>\n"
            f"<b>Имя:</b> {target_user.user_full_name or '—'}\n"
            f"<b>Username:</b> @{target_user.username if target_user.username else '—'}\n"
            f"<b>Текущая подписка:</b> {snapshot}\n\n"
            f"📦 Новый тариф: <b>{plan_name}</b>\n"
            f"⏳ Период: <b>{period_label}</b>"
        )

        await callback.message.answer(
            confirmation_text,
            parse_mode="HTML",
            reply_markup=subscription_confirm_kb(),
        )

    @router.callback_query(F.data == "admin_subscribe_confirm")
    async def admin_subscribe_confirm(
        callback: CallbackQuery,
        state: FSMContext,
        session: AsyncSession,
        bot: Bot,
    ) -> None:
        admin_id = callback.from_user.id if callback.from_user else None
        if not _is_admin(admin_id):
            await callback.answer("Нет доступа", show_alert=True)
            return

        data = await state.get_data()
        target_user_id = data.get("target_user_id")
        plan = data.get("plan")
        period = data.get("period")
        if not target_user_id or not plan or not period:
            await callback.answer("Не хватает данных. Начните заново.", show_alert=True)
            return

        stmt = select(Spyusers).where(Spyusers.user_id == target_user_id)
        user = await session.scalar(stmt)
        if user is None:
            user = await _get_or_create_user_by_id(session, target_user_id)

        now = datetime.utcnow()
        if period == "forever":
            user.subscription_tier = plan
            user.subscription_expires_at = None
            user.subscription_period = "forever"
            user.subscription_weekly_media_count = 0
            user.subscription_weekly_reset_at = now + timedelta(days=7)
            user.subscription_monthly_media_count = 0
            user.subscription_monthly_reset_at = now + timedelta(days=30)
            user.subscription_weekly_notification_count = 0
            user.subscription_weekly_notification_reset_at = now + timedelta(days=7)
            user.subscription_monthly_notification_count = 0
            user.subscription_monthly_notification_reset_at = now + timedelta(days=30)
        else:
            apply_subscription(user, plan, period, now)
        user.updated_at = now

        await session.flush()
        await record_manual_subscription_grant(
            session=session,
            user=user,
            admin_id=admin_id,
            plan=plan,
            period=period,
        )

        await state.clear()
        await callback.answer("Подписка выдана")

        language = (user.language or DEFAULT_LANGUAGE).lower()
        plan_name_user = get_text(f"subscription_plan_{plan}", language)
        if user.subscription_expires_at:
            date_str = user.subscription_expires_at.strftime("%Y-%m-%d %H:%M UTC")
            user_message = get_text(
                "subscription_payment_success",
                language,
                plan=plan_name_user,
                date=date_str,
            )
        else:
            user_message = get_text(
                "subscription_payment_success_no_expiry",
                language,
                plan=plan_name_user,
            )
        try:
            await bot.send_message(user.user_id, user_message, parse_mode="HTML")
        except Exception as exc:
            logger.debug("Failed to notify user %s about manual subscription: %s", user.user_id, exc)

        if period == "forever":
            period_label = "Бессрочно"
        else:
            period_label = get_text(f"subscription_period_{period}", DEFAULT_LANGUAGE)
        await callback.message.answer(
            "✅ Подписка выдана.\n"
            f"Пользователь <code>{user.user_id}</code> получает <b>{plan_name_user}</b> ({period_label}).",
            parse_mode="HTML",
            reply_markup=admin_panel_kb(),
        )

    @router.callback_query(F.data == "admin_manage")
    async def admin_manage(
        callback: CallbackQuery,
        state: FSMContext,
    ) -> None:
        user_id = callback.from_user.id if callback.from_user else None
        if not _is_admin(user_id):
            await callback.answer("Нет доступа", show_alert=True)
            logger.warning("Unauthorized admin callback from user_id=%s", user_id)
            return
        await callback.answer()
        await state.set_state(AdminPanel.waiting_for_user_action)
        await callback.message.answer(
            "Введите действие в формате <code>ban USER_ID</code> или <code>unban USER_ID</code>.\n"
            "Для отмены воспользуйтесь /cancel или кнопкой ниже.",
            parse_mode="HTML",
            reply_markup=back_to_panel_kb(),
        )

    @router.callback_query(F.data == "admin_back")
    async def admin_back(
        callback: CallbackQuery,
        state: FSMContext,
    ) -> None:
        user_id = callback.from_user.id if callback.from_user else None
        if not _is_admin(user_id):
            await callback.answer("Нет доступа", show_alert=True)
            return
        await callback.answer()
        await state.clear()
        await callback.message.answer(
            "Вы вернулись в админ-панель.",
            reply_markup=admin_panel_kb(),
        )

    @router.callback_query(F.data == "admin_close")
    async def admin_close(
        callback: CallbackQuery,
        state: FSMContext,
    ) -> None:
        user_id = callback.from_user.id if callback.from_user else None
        if not _is_admin(user_id):
            await callback.answer("Нет доступа", show_alert=True)
            return
        await callback.answer()
        await state.clear()
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            logger.debug("Failed to remove admin panel keyboard", exc_info=True)

    @router.message(AdminPanel.waiting_for_user_action)
    async def admin_manage_users(
        message: Message,
        session: AsyncSession,
        state: FSMContext,
        bot: Bot,
    ) -> None:
        user_id = message.from_user.id if message.from_user else None
        if not _is_admin(user_id):
            await message.answer("Нет доступа к управлению пользователями.")
            await state.clear()
            return

        text = (message.text or "").strip()
        parts = text.split()
        if len(parts) != 2 or parts[0].lower() not in {"ban", "unban"} or not parts[1].isdigit():
            await message.answer(
                "Неверный формат. Используйте <code>ban USER_ID</code> или <code>unban USER_ID</code>.",
                parse_mode="HTML",
            )
            return

        action = parts[0].lower()
        target_user_id = int(parts[1])

        stmt = select(Spyusers).where(Spyusers.user_id == target_user_id)
        target_user = await session.scalar(stmt)

        if not target_user:
            await message.answer("Пользователь с таким ID не найден.")
            return

        new_status = action == "ban"
        if target_user.is_banned == new_status:
            status_text = "уже заблокирован" if new_status else "уже активен"
            await message.answer(f"Пользователь {status_text}.")
            return

        target_user.is_banned = new_status
        await session.flush()

        status_message = "заблокирован" if new_status else "разблокирован"
        await message.answer(f"Пользователь <code>{target_user_id}</code> {status_message}.", parse_mode="HTML")

        notify_text = (
            "Ваш доступ к боту временно ограничен администратором."
            if new_status
            else "Ваш доступ к боту восстановлен."
        )
        try:
            await bot.send_message(target_user_id, notify_text)
        except Exception as exc:
            logger.debug("Failed to notify user %s about ban status change: %s", target_user_id, exc)

    @router.message(
        Command("cancel"),
        StateFilter(
            AdminPanel.waiting_for_user_action,
            AdminPanel.subscription_user,
            AdminPanel.subscription_plan,
            AdminPanel.subscription_period,
            AdminPanel.subscription_confirmation,
        ),
    )
    async def admin_cancel(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer(
            "Действие отменено.",
            reply_markup=admin_panel_kb(),
        )

    @router.message(AdminPanel.subscription_user)
    async def admin_subscription_user_input(
        message: Message,
        session: AsyncSession,
        state: FSMContext,
    ) -> None:
        user_id = message.from_user.id if message.from_user else None
        if not _is_admin(user_id):
            await message.answer("Нет доступа к управлению подписками.")
            await state.clear()
            return

        target_user = await _resolve_target_user(message, session)
        if target_user is None:
            return

        await session.flush()
        await state.update_data(target_user_id=target_user.user_id)
        await state.set_state(AdminPanel.subscription_plan)

        snapshot = _format_subscription_snapshot(target_user)
        await message.answer(
            "Пользователь выбран.\n"
            f"Текущий статус: {snapshot}.\n\n"
            "Выберите тариф для выдачи:",
            reply_markup=subscription_plan_kb(),
        )

    return router
