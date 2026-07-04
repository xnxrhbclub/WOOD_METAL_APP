import sqlite3
from datetime import date
from pathlib import Path
from typing import List, Optional

from models import Order, Material, OrderMaterial, OrderExpense

DB_PATH = Path(__file__).parent / "orders.db"


class OrderDB:
    def __init__(self, db_path: str = str(DB_PATH)):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                item TEXT NOT NULL,
                deadline TEXT NOT NULL,
                price REAL NOT NULL,
                order_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                notes TEXT DEFAULT ''
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                unit TEXT NOT NULL DEFAULT 'м',
                quantity REAL NOT NULL DEFAULT 0,
                price_per_unit REAL NOT NULL DEFAULT 0
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS order_materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                material_id INTEGER,
                material_name TEXT NOT NULL,
                unit TEXT NOT NULL DEFAULT 'м',
                quantity_used REAL NOT NULL,
                cost REAL NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS order_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL
            )
            """
        )
        self.conn.commit()

    def add_order(self, order: Order) -> int:
        cur = self.conn.execute(
            "INSERT INTO orders (client_name, item, deadline, price, order_date, status, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                order.client_name,
                order.item,
                order.deadline.isoformat(),
                order.price,
                order.order_date.isoformat(),
                order.status,
                order.notes,
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_order(self, order: Order):
        self.conn.execute(
            "UPDATE orders SET client_name=?, item=?, deadline=?, price=?, status=?, notes=? WHERE id=?",
            (
                order.client_name,
                order.item,
                order.deadline.isoformat(),
                order.price,
                order.status,
                order.notes,
                order.id,
            ),
        )
        self.conn.commit()

    def delete_order(self, order_id: int):
        self.conn.execute("DELETE FROM orders WHERE id=?", (order_id,))
        self.conn.commit()

    def get_all(self, include_done: bool = False) -> List[Order]:
        query = "SELECT * FROM orders"
        if not include_done:
            query += " WHERE status != 'done'"
        query += " ORDER BY deadline ASC"
        rows = self.conn.execute(query).fetchall()
        return [self._row_to_order(r) for r in rows]

    def get_by_id(self, order_id: int) -> Optional[Order]:
        row = self.conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        return self._row_to_order(row) if row else None

    @staticmethod
    def _row_to_order(row) -> Order:
        return Order(
            id=row["id"],
            client_name=row["client_name"],
            item=row["item"],
            deadline=date.fromisoformat(row["deadline"]),
            price=row["price"],
            order_date=date.fromisoformat(row["order_date"]),
            status=row["status"],
            notes=row["notes"],
        )

    # ------------------------------------------------------------ склад --

    def add_material(self, material: Material) -> int:
        cur = self.conn.execute(
            "INSERT INTO materials (name, unit, quantity, price_per_unit) VALUES (?, ?, ?, ?)",
            (material.name, material.unit, material.quantity, material.price_per_unit),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_material(self, material: Material):
        self.conn.execute(
            "UPDATE materials SET name=?, unit=?, quantity=?, price_per_unit=? WHERE id=?",
            (material.name, material.unit, material.quantity, material.price_per_unit, material.id),
        )
        self.conn.commit()

    def delete_material(self, material_id: int):
        self.conn.execute("DELETE FROM materials WHERE id=?", (material_id,))
        self.conn.commit()

    def get_materials(self) -> List[Material]:
        rows = self.conn.execute("SELECT * FROM materials ORDER BY name ASC").fetchall()
        return [self._row_to_material(r) for r in rows]

    def get_material(self, material_id: int) -> Optional[Material]:
        row = self.conn.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
        return self._row_to_material(row) if row else None

    def adjust_material_quantity(self, material_id: int, delta: float):
        """Изменяет остаток материала на складе (delta может быть отрицательной)."""
        material = self.get_material(material_id)
        if material:
            material.quantity += delta
            self.update_material(material)

    @staticmethod
    def _row_to_material(row) -> Material:
        return Material(
            id=row["id"],
            name=row["name"],
            unit=row["unit"],
            quantity=row["quantity"],
            price_per_unit=row["price_per_unit"],
        )

    # ------------------------------------------------- материалы заказа --

    def add_order_material(self, order_material: OrderMaterial) -> int:
        cur = self.conn.execute(
            "INSERT INTO order_materials (order_id, material_id, material_name, unit, quantity_used, cost) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                order_material.order_id,
                order_material.material_id,
                order_material.material_name,
                order_material.unit,
                order_material.quantity_used,
                order_material.cost,
            ),
        )
        self.conn.commit()
        if order_material.material_id is not None:
            self.adjust_material_quantity(order_material.material_id, -order_material.quantity_used)
        return cur.lastrowid

    def delete_order_material(self, order_material_id: int):
        row = self.conn.execute(
            "SELECT * FROM order_materials WHERE id=?", (order_material_id,)
        ).fetchone()
        if row:
            self.conn.execute("DELETE FROM order_materials WHERE id=?", (order_material_id,))
            self.conn.commit()
            if row["material_id"] is not None:
                self.adjust_material_quantity(row["material_id"], row["quantity_used"])

    def get_order_materials(self, order_id: int) -> List[OrderMaterial]:
        rows = self.conn.execute(
            "SELECT * FROM order_materials WHERE order_id=? ORDER BY id ASC", (order_id,)
        ).fetchall()
        return [
            OrderMaterial(
                id=r["id"], order_id=r["order_id"], material_id=r["material_id"],
                material_name=r["material_name"], unit=r["unit"],
                quantity_used=r["quantity_used"], cost=r["cost"],
            )
            for r in rows
        ]

    # --------------------------------------------------- расходы заказа --

    def add_order_expense(self, expense: OrderExpense) -> int:
        cur = self.conn.execute(
            "INSERT INTO order_expenses (order_id, description, amount) VALUES (?, ?, ?)",
            (expense.order_id, expense.description, expense.amount),
        )
        self.conn.commit()
        return cur.lastrowid

    def delete_order_expense(self, expense_id: int):
        self.conn.execute("DELETE FROM order_expenses WHERE id=?", (expense_id,))
        self.conn.commit()

    def get_order_expenses(self, order_id: int) -> List[OrderExpense]:
        rows = self.conn.execute(
            "SELECT * FROM order_expenses WHERE order_id=? ORDER BY id ASC", (order_id,)
        ).fetchall()
        return [
            OrderExpense(id=r["id"], order_id=r["order_id"], description=r["description"], amount=r["amount"])
            for r in rows
        ]

    # ------------------------------------------------------- финансы --

    def get_order_financials(self, order_id: int, price: float) -> dict:
        """Считает себестоимость и чистую прибыль по заказу."""
        materials = self.get_order_materials(order_id)
        expenses = self.get_order_expenses(order_id)
        material_cost = sum(m.cost for m in materials)
        expenses_total = sum(e.amount for e in expenses)
        total_cost = material_cost + expenses_total
        return {
            "material_cost": material_cost,
            "expenses_total": expenses_total,
            "total_cost": total_cost,
            "profit": price - total_cost,
            "has_data": bool(materials or expenses),
        }
