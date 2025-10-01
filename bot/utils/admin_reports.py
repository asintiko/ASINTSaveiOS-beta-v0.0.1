from __future__ import annotations

import json
import tempfile
import textwrap
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Dict, List, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db import CommandStat, PaymentTransaction, Spyusers

_DARK_BG = "#111b21"
_PANEL_BG = "#17212b"
_CARD_BG = "#1f2a33"
_ACCENT = "#2a9fd6"
_TEXT_PRIMARY = "#eef1f4"
_TEXT_SECONDARY = "#9aa9b5"
_TABLE_BORDER = "#22303c"
_FONT_FAMILY = "'SF Pro Text', 'Segoe UI', sans-serif"


@dataclass
class ReportFile:
    path: Path
    filename: str
    caption: str

    def cleanup(self) -> None:
        try:
            self.path.unlink(missing_ok=True)
        except Exception:
            pass


def _format_dt(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.strftime("%Y-%m-%d %H:%M")


def _render_base_html(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8" />
<title>{escape(title)}</title>
<style>
    :root {{
        color-scheme: dark;
    }}
    body {{
        background: {_DARK_BG};
        color: {_TEXT_PRIMARY};
        font-family: {_FONT_FAMILY};
        margin: 0;
        padding: 32px;
    }}
    h1 {{
        margin: 0 0 24px;
        font-size: 28px;
    }}
    h2 {{
        margin: 32px 0 16px;
        font-size: 22px;
        color: {_TEXT_PRIMARY};
    }}
    p {{
        color: {_TEXT_SECONDARY};
        line-height: 1.6;
    }}
    .panel {{
        background: {_PANEL_BG};
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35);
    }}
    .cards {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
    }}
    .card {{
        background: {_CARD_BG};
        border-radius: 14px;
        padding: 18px;
        border: 1px solid {_TABLE_BORDER};
    }}
    .card h3 {{
        margin: 0 0 12px;
        font-size: 16px;
        color: {_TEXT_SECONDARY};
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }}
    .card strong {{
        font-size: 24px;
        color: {_TEXT_PRIMARY};
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        background: {_CARD_BG};
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid {_TABLE_BORDER};
    }}
    th, td {{
        padding: 12px 16px;
        text-align: left;
        border-bottom: 1px solid {_TABLE_BORDER};
        font-size: 14px;
    }}
    th {{
        background: {_PANEL_BG};
        text-transform: uppercase;
        font-size: 12px;
        letter-spacing: 0.05em;
        color: {_TEXT_SECONDARY};
    }}
    tr:hover td {{
        background: rgba(42, 159, 214, 0.08);
    }}
    .badge {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        background: {_ACCENT};
        color: #fff;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    .muted {{
        color: {_TEXT_SECONDARY};
        font-size: 13px;
    }}
    #user-chart {{
        display: flex;
        align-items: flex-end;
        gap: 8px;
        height: 280px;
        padding: 20px;
        background: {_CARD_BG};
        border: 1px solid {_TABLE_BORDER};
        border-radius: 16px;
        overflow-x: auto;
    }}
    .bar {{
        flex: 0 0 40px;
        background: {_ACCENT};
        border-radius: 6px 6px 0 0;
        position: relative;
    }}
    .bar span {{
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translate(-50%, -6px);
        font-size: 12px;
        color: {_TEXT_SECONDARY};
    }}
    .bar small {{
        position: absolute;
        bottom: -32px;
        left: 50%;
        transform: translateX(-50%) rotate(-45deg);
        transform-origin: bottom;
        white-space: nowrap;
        font-size: 11px;
        color: {_TEXT_SECONDARY};
    }}
    select {{
        background: {_CARD_BG};
        color: {_TEXT_PRIMARY};
        border: 1px solid {_TABLE_BORDER};
        border-radius: 12px;
        padding: 8px 12px;
        font-size: 14px;
    }}
    footer {{
        margin-top: 32px;
        text-align: center;
        font-size: 12px;
        color: {_TEXT_SECONDARY};
    }}
</style>
</head>
<body>
<div class="panel">
{body}
</div>
<footer>Отчёт сформирован {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</footer>
</body>
</html>"""


def _write_report(title: str, body: str, filename: str, caption: str) -> ReportFile:
    html = _render_base_html(title, body)
    temp_file = tempfile.NamedTemporaryFile("w", delete=False, suffix=".html", encoding="utf-8")
    with temp_file as fh:
        fh.write(html)
    return ReportFile(path=Path(temp_file.name), filename=filename, caption=caption)


async def generate_users_report(session: AsyncSession) -> ReportFile:
    users: Sequence[Spyusers] = (
        await session.scalars(
            select(Spyusers).order_by(Spyusers.created_at.nullslast(), Spyusers.id)
        )
    ).all()

    total_users = len(users)
    now = datetime.utcnow()
    banned = sum(1 for u in users if u.is_banned)
    active_subs = sum(
        1
        for u in users
        if (u.subscription_tier or "free") != "free"
        and (u.subscription_expires_at is None or u.subscription_expires_at > now)
    )

    rows: List[str] = []
    for user in users:
        plan_key = (user.subscription_tier or "free").lower()
        plan_label = escape(plan_key.title())
        if plan_key == "free":
            plan_display = f"<span class='muted'>{plan_label}</span>"
        elif user.subscription_expires_at:
            expires = _format_dt(user.subscription_expires_at)
            plan_display = (
                f"<span class='badge'>{plan_label}</span> "
                f"<span class='muted'>до {expires}</span>"
            )
        else:
            plan_display = f"<span class='badge'>{plan_label}</span> <span class='muted'>бессрочно</span>"

        username = f"@{escape(user.username)}" if user.username else "—"
        rows.append(
            "".join(
                [
                    "<tr>",
                    f"<td>{'🚫' if user.is_banned else '✅'}</td>",
                    f"<td><strong>{escape(user.user_full_name or '—')}</strong>",
                    f"<div class='muted'>{username}</div></td>",
                    f"<td>{user.user_id}</td>",
                    f"<td>{plan_display}</td>",
                    f"<td>{escape((user.language or '—').upper())}</td>",
                    f"<td>{_format_dt(user.created_at)}</td>",
                    f"<td>{_format_dt(user.last_seen_at)}</td>",
                    "</tr>",
                ]
            )
        )

    if rows:
        table_html = (
            "<table>"
            "<thead><tr><th></th><th>Пользователь</th><th>ID</th><th>Подписка</th><th>Язык</th><th>Дата регистрации</th><th>Активность</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody>"
            "</table>"
        )
    else:
        table_html = "<p>Пользователи отсутствуют.</p>"

    body = textwrap.dedent(
        f"""
        <h1>Отчёт по пользователям</h1>
        <div class='cards'>
            <div class='card'><h3>Всего</h3><strong>{total_users}</strong></div>
            <div class='card'><h3>Активные подписки</h3><strong>{active_subs}</strong></div>
            <div class='card'><h3>Заблокированы</h3><strong>{banned}</strong></div>
        </div>
        <h2>Список пользователей</h2>
        {table_html}
        """
    ).strip()

    caption = f"👥 Отчёт по пользователям • всего {total_users}"
    return _write_report(
        title="AsintSave — пользователи",
        body=body,
        filename="users-report.html",
        caption=caption,
    )


async def generate_statistics_report(session: AsyncSession) -> ReportFile:
    now = datetime.utcnow()
    total_users = await session.scalar(select(func.count(Spyusers.id))) or 0
    banned_users = await session.scalar(select(func.count()).where(Spyusers.is_banned.is_(True))) or 0

    active_users: Sequence[Spyusers] = (
        await session.scalars(
            select(Spyusers).where(
                (Spyusers.subscription_tier.is_not(None))
                & (Spyusers.subscription_tier != "free")
            )
        )
    ).all()
    lifetime = sum(1 for user in active_users if user.subscription_expires_at is None)
    active_subscriptions = sum(
        1
        for user in active_users
        if user.subscription_expires_at and user.subscription_expires_at > now
    )
    total_active = active_subscriptions + lifetime

    command_stats: Sequence[CommandStat] = (
        await session.scalars(select(CommandStat).order_by(CommandStat.count.desc()))
    ).all()

    transactions: Sequence[PaymentTransaction] = (
        await session.scalars(select(PaymentTransaction).order_by(PaymentTransaction.created_at))
    ).all()

    if command_stats:
        command_rows = "".join(
            f"<tr><td>/{escape(stat.command)}</td><td>{stat.count}</td><td>{_format_dt(stat.updated_at)}</td></tr>"
            for stat in command_stats
        )
        commands_html = (
            "<h2>Использование команд</h2>"
            "<table><thead><tr><th>Команда</th><th>Количество</th><th>Последнее использование</th></tr></thead>"
            f"<tbody>{command_rows}</tbody></table>"
        )
    else:
        commands_html = "<h2>Использование команд</h2><p>Данных пока нет.</p>"

    if transactions:
        by_method: Dict[str, int] = {}
        manual = 0
        for tx in transactions:
            method = tx.method.lower()
            by_method[method] = by_method.get(method, 0) + 1
            if tx.is_manual:
                manual += 1
        payment_rows = "".join(
            f"<tr><td>{escape(method.upper())}</td><td>{count}</td></tr>"
            for method, count in sorted(by_method.items())
        )
        payments_html = (
            "<h2>Платежи</h2>"
            "<table><thead><tr><th>Метод</th><th>Успешных оплат</th></tr></thead>"
            f"<tbody>{payment_rows}</tbody></table>"
            f"<p class='muted'>Ручных выдач: {manual}</p>"
        )
    else:
        payments_html = "<h2>Платежи</h2><p>Информации об оплатах пока нет.</p>"

    daily_new: Dict[str, int] = {}
    creation_dates: Sequence[datetime] = (
        await session.scalars(select(Spyusers.created_at).where(Spyusers.created_at.is_not(None)))
    ).all()
    for created in creation_dates:
        day = created.strftime("%Y-%m-%d")
        daily_new[day] = daily_new.get(day, 0) + 1
    sorted_days = sorted(daily_new.keys())
    chart_data = [{"date": day, "count": daily_new[day]} for day in sorted_days]
    chart_json = json.dumps(chart_data, ensure_ascii=False)

    chart_html = textwrap.dedent(
        f"""
        <h2>Рост пользователей</h2>
        <label for='period'>Выберите период:</label>
        <select id='period'>
            <option value='7'>7 дней</option>
            <option value='30' selected>30 дней</option>
            <option value='90'>90 дней</option>
            <option value='180'>180 дней</option>
            <option value='365'>365 дней</option>
        </select>
        <div id='user-chart'></div>
        <script>
        const dailyData = {chart_json};
        const chart = document.getElementById('user-chart');
        const selectEl = document.getElementById('period');

        function renderChart(period) {{
          chart.innerHTML = '';
          if (!dailyData.length) {{
            chart.innerHTML = '<p class="muted">Недостаточно данных для графика.</p>';
            return;
          }}
          const slice = dailyData.slice(-period);
          const max = Math.max(1, ...slice.map(item => item.count));
          chart.innerHTML = '';
          slice.forEach(item => {{
            const bar = document.createElement('div');
            bar.className = 'bar';
            bar.style.height = ((item.count / max) * 100).toFixed(2) + '%';
            const value = document.createElement('span');
            value.textContent = item.count;
            bar.appendChild(value);
            const label = document.createElement('small');
            label.textContent = item.date;
            bar.appendChild(label);
            chart.appendChild(bar);
          }});
        }}

        selectEl.addEventListener('change', (event) => {{
          renderChart(parseInt(event.target.value, 10));
        }});

        renderChart(parseInt(selectEl.value, 10));
        </script>
        """
    ).strip()

    body = textwrap.dedent(
        f"""
        <h1>Аналитика AsintSave</h1>
        <div class='cards'>
            <div class='card'><h3>Всего пользователей</h3><strong>{total_users}</strong></div>
            <div class='card'><h3>Активные подписки</h3><strong>{total_active}</strong></div>
            <div class='card'><h3>Бессрочные</h3><strong>{lifetime}</strong></div>
            <div class='card'><h3>Заблокированы</h3><strong>{banned_users}</strong></div>
        </div>
        {chart_html}
        {commands_html}
        {payments_html}
        """
    ).strip()

    caption = "📊 Статистика бота AsintSave"
    return _write_report(
        title="AsintSave — статистика",
        body=body,
        filename="statistics-report.html",
        caption=caption,
    )
