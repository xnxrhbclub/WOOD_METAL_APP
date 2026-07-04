from typing import List

from models import Order

try:
    from plyer import notification as plyer_notification
    HAS_PLYER = True
except Exception:
    HAS_PLYER = False


def check_and_notify(orders: List[Order], warn_days: int = 4):
    """Проверяет список заказов и шлёт уведомление, если срок близко или просрочен."""
    for order in orders:
        if order.status == "done":
            continue
        days = order.days_left
        if days < 0:
            _send(
                f"Просрочен заказ: {order.client_name}",
                f"«{order.item}» — просрочка {abs(days)} дн.",
            )
        elif days <= warn_days:
            _send(
                f"Скоро срок: {order.client_name}",
                f"«{order.item}» — осталось {days} дн. (до {order.deadline.strftime('%d.%m.%Y')})",
            )


def _send(title: str, message: str):
    if HAS_PLYER:
        try:
            plyer_notification.notify(title=title, message=message, timeout=10)
            return
        except Exception:
            pass
    # Фолбэк, если plyer недоступен (например при отладке на десктопе без бэкенда уведомлений)
    print(f"[УВЕДОМЛЕНИЕ] {title}: {message}")
