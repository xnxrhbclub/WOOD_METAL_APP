from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Order:
    id: Optional[int]
    client_name: str          # кто заказал (например "Иван")
    item: str                 # что делаем (например "сварить стол")
    deadline: date             # к какому сроку нужно
    price: float               # цена
    order_date: date = field(default_factory=date.today)
    status: str = "active"     # active | done
    notes: str = ""

    @property
    def days_left(self) -> int:
        """Сколько дней осталось до срока. Отрицательное число — просрочка."""
        return (self.deadline - date.today()).days


@dataclass
class Material:
    """Позиция на складе металла (например 'Труба 40х40')."""
    id: Optional[int]
    name: str
    unit: str = "м"          # м, кг, шт — единица измерения остатка
    quantity: float = 0.0     # сколько осталось
    price_per_unit: float = 0.0  # цена за единицу (для расчёта себестоимости)


@dataclass
class OrderMaterial:
    """Расход материала на конкретный заказ (снимок цены на момент списания)."""
    id: Optional[int]
    order_id: int
    material_id: Optional[int]
    material_name: str
    unit: str
    quantity_used: float
    cost: float


@dataclass
class OrderExpense:
    """Прочий расход по заказу (расходники, доставка и т.п.)."""
    id: Optional[int]
    order_id: int
    description: str
    amount: float

