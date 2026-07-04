from datetime import date

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.uix.spinner import Spinner
from kivy.uix.behaviors import ButtonBehavior

from database import OrderDB
from models import Order, Material, OrderMaterial, OrderExpense
from utils import parse_deadline
from notifications import check_and_notify
from settings import load_settings, save_settings
from theme import (
    BG, BRONZE, BRONZE_LIGHT,
    CREAM, CREAM_DIM, STATUS_OK, STATUS_WARN, STATUS_OVERDUE,
    FONT_TITLE, FONT_SUBTITLE, FONT_BODY, FONT_SMALL,
    GLASS_PANEL, GLASS_PANEL_LIGHT, GLASS_BAR,
)
from widgets import Card, BronzeButton, GhostButton, DangerButton, NavButton, StyledInput

Window.clearcolor = BG


# ---------------------------------------------------------------- helpers --

def status_color(days: int) -> tuple:
    if days < 0:
        return STATUS_OVERDUE
    warn_days = App.get_running_app().settings["warn_days"]
    if days <= warn_days:
        return STATUS_WARN
    return STATUS_OK


def wrap_label(**kwargs):
    lbl = Label(**kwargs)
    lbl.bind(size=lambda inst, val: setattr(inst, "text_size", val))
    return lbl


class TopBar(Card):
    """Стеклянная шапка с логотипом и названием компании (скруглена снизу)."""

    def __init__(self, subtitle="", **kwargs):
        super().__init__(bg_color=GLASS_BAR, radius=[0, 0, dp(22), dp(22)],
                          orientation="horizontal",
                          size_hint_y=None, height=dp(78), padding=(dp(16), dp(10)),
                          spacing=dp(12), **kwargs)

        try:
            logo = Image(source="icon.png", size_hint=(None, None), size=(dp(52), dp(52)))
            self.add_widget(logo)
        except Exception:
            pass

        text_box = BoxLayout(orientation="vertical")
        app = App.get_running_app()
        name = app.settings.get("company_name", "WOOD METAL") if app else "WOOD METAL"
        title = wrap_label(text=name, font_size=FONT_TITLE, bold=True, color=BRONZE_LIGHT,
                            halign="left", valign="middle", size_hint_y=0.6)
        self.subtitle_label = wrap_label(text=subtitle, font_size=FONT_SUBTITLE, color=CREAM_DIM,
                                          halign="left", valign="middle", size_hint_y=0.4)
        text_box.add_widget(title)
        text_box.add_widget(self.subtitle_label)
        self.add_widget(text_box)

    def set_subtitle(self, text):
        self.subtitle_label.text = text


class NavBar(Card):
    """Стеклянная нижняя навигация (скруглена сверху): Заказы / Новый заказ / Склад / Настройки."""

    def __init__(self, active="orders", **kwargs):
        super().__init__(bg_color=GLASS_BAR, radius=[dp(22), dp(22), 0, 0],
                          orientation="horizontal", size_hint_y=None, height=dp(66),
                          padding=(dp(8), dp(8)), spacing=dp(6), **kwargs)

        self.btn_orders = NavButton(text="Заказы", font_size=FONT_SMALL)
        self.btn_add = NavButton(text="+ Заказ", font_size=FONT_SMALL)
        self.btn_materials = NavButton(text="Склад", font_size=FONT_SMALL)
        self.btn_settings = NavButton(text="Настройки", font_size=FONT_SMALL)

        self.btn_orders.bind(on_release=lambda *_: self._go("orders"))
        self.btn_add.bind(on_release=lambda *_: self._go("add"))
        self.btn_materials.bind(on_release=lambda *_: self._go("materials"))
        self.btn_settings.bind(on_release=lambda *_: self._go("settings"))

        buttons = (
            (self.btn_orders, "orders"),
            (self.btn_add, "add"),
            (self.btn_materials, "materials"),
            (self.btn_settings, "settings"),
        )
        for b, name in buttons:
            b.set_active(name == active)
            self.add_widget(b)

    def _go(self, name):
        app = App.get_running_app()
        app.sm.current = name


# ------------------------------------------------------------- order card --

class ClickableBox(ButtonBehavior, BoxLayout):
    """BoxLayout, реагирующий на нажатие как кнопка (для открытия деталей заказа)."""
    pass


class OrderRow(Card):
    """Карточка одного заказа со статусной полосой слева. Клик по карточке — детали заказа."""

    def __init__(self, order: Order, on_done, on_delete, on_open, **kwargs):
        super().__init__(bg_color=GLASS_PANEL, radius=dp(18), orientation="horizontal",
                          size_hint_y=None, height=dp(104), padding=dp(2), spacing=0, **kwargs)
        self.order = order
        days = order.days_left
        color = status_color(days)

        # цветная полоса-индикатор слева
        stripe = Widget(size_hint_x=None, width=dp(8))
        with stripe.canvas.before:
            Color(*color)
            self._stripe_rect = RoundedRectangle(pos=stripe.pos, size=stripe.size,
                                                   radius=[dp(6), 0, 0, dp(6)])
        stripe.bind(pos=self._update_stripe, size=self._update_stripe)
        self._stripe = stripe
        self.add_widget(stripe)

        content = BoxLayout(orientation="horizontal", padding=(dp(14), dp(10)), spacing=dp(10))

        info = ClickableBox(orientation="vertical", spacing=dp(2))
        info.bind(on_release=lambda *_: on_open(order))
        info.add_widget(wrap_label(
            text=f"[b]{order.client_name}[/b]", markup=True, font_size=FONT_SUBTITLE,
            color=CREAM, halign="left", valign="middle", size_hint_y=0.3,
        ))
        info.add_widget(wrap_label(
            text=order.item, font_size=FONT_BODY, color=CREAM_DIM,
            halign="left", valign="middle", size_hint_y=0.25,
        ))
        app = App.get_running_app()
        currency = app.settings.get("currency", "")
        sub = f"Срок: {order.deadline.strftime('%d.%m.%Y')}   \u2022   {order.price:.0f} {currency}   \u2022   "
        sub += f"просрочен на {abs(days)} дн." if days < 0 else f"осталось {days} дн."
        info.add_widget(wrap_label(
            text=sub, font_size=FONT_SMALL, color=BRONZE_LIGHT if days >= 0 else STATUS_OVERDUE,
            halign="left", valign="middle", size_hint_y=0.25,
        ))

        fin = app.db.get_order_financials(order.id, order.price)
        if fin["has_data"]:
            profit_color = STATUS_OK if fin["profit"] >= 0 else STATUS_OVERDUE
            info.add_widget(wrap_label(
                text=f"Прибыль: {fin['profit']:.0f} {currency}",
                font_size=FONT_SMALL, bold=True, color=profit_color,
                halign="left", valign="middle", size_hint_y=0.2,
            ))
        content.add_widget(info)

        btns = BoxLayout(orientation="vertical", size_hint_x=0.30, spacing=dp(6))
        done_btn = GhostButton(text="Готово", font_size=FONT_SMALL)
        done_btn.bind(on_release=lambda *_: on_done(order))
        del_btn = DangerButton(text="Удалить", font_size=FONT_SMALL)
        del_btn.bind(on_release=lambda *_: on_delete(order))
        btns.add_widget(done_btn)
        btns.add_widget(del_btn)
        content.add_widget(btns)

        self.add_widget(content)

    def _update_stripe(self, *_):
        self._stripe_rect.pos = self._stripe.pos
        self._stripe_rect.size = self._stripe.size


# ----------------------------------------------------------------- screens --

class OrdersScreen(Screen):
    def __init__(self, db: OrderDB, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        root = BoxLayout(orientation="vertical")
        root.add_widget(TopBar(subtitle="Активные заказы"))

        body = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        self.scroll = ScrollView()
        self.list_box = GridLayout(cols=1, size_hint_y=None, spacing=dp(10))
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.scroll.add_widget(self.list_box)
        body.add_widget(self.scroll)
        root.add_widget(body)

        root.add_widget(NavBar(active="orders"))
        self.add_widget(root)

    def refresh(self):
        self.list_box.clear_widgets()
        orders = self.db.get_all()
        if not orders:
            placeholder = Card(bg_color=GLASS_PANEL, radius=dp(18), size_hint_y=None, height=dp(80))
            placeholder.add_widget(wrap_label(
                text="Заказов пока нет — добавьте первый",
                color=CREAM_DIM, halign="center", valign="middle",
            ))
            self.list_box.add_widget(placeholder)
        for order in orders:
            self.list_box.add_widget(
                OrderRow(order, on_done=self.mark_done, on_delete=self.delete_order,
                         on_open=self.open_order)
            )

    def open_order(self, order: Order):
        app = App.get_running_app()
        app.sm.get_screen("order_detail").load_order(order.id)
        app.sm.current = "order_detail"

    def mark_done(self, order: Order):
        order.status = "done"
        self.db.update_order(order)
        self.refresh()

    def delete_order(self, order: Order):
        self.db.delete_order(order.id)
        self.refresh()

    def on_pre_enter(self, *args):
        self.refresh()


class AddOrderScreen(Screen):
    def __init__(self, db: OrderDB, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        root = BoxLayout(orientation="vertical")
        root.add_widget(TopBar(subtitle="Новый заказ"))

        form = Card(bg_color=(0, 0, 0, 0), radius=0, orientation="vertical",
                    padding=dp(18), spacing=dp(12))

        self.client_input = StyledInput(hint_text="Клиент (например, Иван)", multiline=False,
                                         size_hint_y=None, height=dp(50))
        self.item_input = StyledInput(hint_text="Что делаем (например, сварить стол)", multiline=False,
                                       size_hint_y=None, height=dp(50))
        self.deadline_input = StyledInput(hint_text="Срок: число дней (5) или дата (31.12.2026)",
                                           multiline=False, size_hint_y=None, height=dp(50))
        self.price_input = StyledInput(hint_text="Цена", multiline=False, input_filter="float",
                                        size_hint_y=None, height=dp(50))

        for w in (self.client_input, self.item_input, self.deadline_input, self.price_input):
            form.add_widget(w)

        self.error_label = wrap_label(text="", color=STATUS_OVERDUE, font_size=FONT_SMALL,
                                       size_hint_y=None, height=dp(24), halign="left")
        form.add_widget(self.error_label)

        btn_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        save_btn = BronzeButton(text="Сохранить заказ")
        save_btn.bind(on_release=self.save_order)
        cancel_btn = GhostButton(text="Отмена")
        cancel_btn.bind(on_release=self.cancel)
        btn_row.add_widget(save_btn)
        btn_row.add_widget(cancel_btn)
        form.add_widget(btn_row)

        form.add_widget(Widget())
        root.add_widget(form)
        root.add_widget(NavBar(active="add"))
        self.add_widget(root)

    def cancel(self, *_):
        self.clear_form()
        self.manager.current = "orders"

    def save_order(self, *_):
        client = self.client_input.text.strip()
        item = self.item_input.text.strip()
        price_text = self.price_input.text.strip()

        if not client or not item:
            self.error_label.text = "Заполните клиента и описание заказа"
            return
        try:
            deadline = parse_deadline(self.deadline_input.text)
        except ValueError as e:
            self.error_label.text = str(e)
            return
        try:
            price = float(price_text) if price_text else 0.0
        except ValueError:
            self.error_label.text = "Цена должна быть числом"
            return

        order = Order(id=None, client_name=client, item=item, deadline=deadline,
                       price=price, order_date=date.today())
        self.db.add_order(order)
        self.clear_form()
        self.manager.current = "orders"

    def clear_form(self):
        self.client_input.text = ""
        self.item_input.text = ""
        self.deadline_input.text = ""
        self.price_input.text = ""
        self.error_label.text = ""

    def on_pre_enter(self, *args):
        self.error_label.text = ""


class MaterialRow(Card):
    """Карточка одной позиции склада."""

    def __init__(self, material: Material, on_edit, on_delete, **kwargs):
        super().__init__(bg_color=GLASS_PANEL, radius=dp(18), orientation="horizontal",
                          size_hint_y=None, height=dp(84), padding=dp(14), spacing=dp(10), **kwargs)
        currency = App.get_running_app().settings.get("currency", "")

        info = BoxLayout(orientation="vertical", spacing=dp(2))
        info.add_widget(wrap_label(
            text=f"[b]{material.name}[/b]", markup=True, font_size=FONT_SUBTITLE,
            color=CREAM, halign="left", valign="middle", size_hint_y=0.5,
        ))
        info.add_widget(wrap_label(
            text=f"Остаток: {material.quantity:g} {material.unit}   \u2022   "
                 f"{material.price_per_unit:.0f} {currency}/{material.unit}",
            font_size=FONT_SMALL, color=BRONZE_LIGHT,
            halign="left", valign="middle", size_hint_y=0.5,
        ))
        self.add_widget(info)

        btns = BoxLayout(orientation="vertical", size_hint_x=0.32, spacing=dp(6))
        edit_btn = GhostButton(text="Изменить", font_size=FONT_SMALL)
        edit_btn.bind(on_release=lambda *_: on_edit(material))
        del_btn = DangerButton(text="Удалить", font_size=FONT_SMALL)
        del_btn.bind(on_release=lambda *_: on_delete(material))
        btns.add_widget(edit_btn)
        btns.add_widget(del_btn)
        self.add_widget(btns)


class MaterialsScreen(Screen):
    def __init__(self, db: OrderDB, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        root = BoxLayout(orientation="vertical")
        root.add_widget(TopBar(subtitle="Склад металла"))

        body = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        self.scroll = ScrollView()
        self.list_box = GridLayout(cols=1, size_hint_y=None, spacing=dp(10))
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.scroll.add_widget(self.list_box)
        body.add_widget(self.scroll)

        add_btn = BronzeButton(text="+ Материал", size_hint_y=None, height=dp(52))
        add_btn.bind(on_release=self.go_to_add)
        body.add_widget(add_btn)

        root.add_widget(body)
        root.add_widget(NavBar(active="materials"))
        self.add_widget(root)

    def go_to_add(self, *_):
        app = App.get_running_app()
        app.sm.get_screen("add_material").load_material(None)
        app.sm.current = "add_material"

    def edit_material(self, material: Material):
        app = App.get_running_app()
        app.sm.get_screen("add_material").load_material(material.id)
        app.sm.current = "add_material"

    def delete_material(self, material: Material):
        self.db.delete_material(material.id)
        self.refresh()

    def refresh(self):
        self.list_box.clear_widgets()
        materials = self.db.get_materials()
        if not materials:
            placeholder = Card(bg_color=GLASS_PANEL, radius=dp(18), size_hint_y=None, height=dp(80))
            placeholder.add_widget(wrap_label(
                text="На складе пока пусто — добавьте первую позицию",
                color=CREAM_DIM, halign="center", valign="middle",
            ))
            self.list_box.add_widget(placeholder)
        for material in materials:
            self.list_box.add_widget(
                MaterialRow(material, on_edit=self.edit_material, on_delete=self.delete_material)
            )

    def on_pre_enter(self, *args):
        self.refresh()


class AddMaterialScreen(Screen):
    """Форма добавления/редактирования позиции склада."""

    def __init__(self, db: OrderDB, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.editing_id = None
        root = BoxLayout(orientation="vertical")
        self.top_bar = TopBar(subtitle="Новый материал")
        root.add_widget(self.top_bar)

        form = Card(bg_color=(0, 0, 0, 0), radius=0, orientation="vertical", padding=dp(18), spacing=dp(12))

        self.name_input = StyledInput(hint_text="Название (например, Труба 40х40)", multiline=False,
                                       size_hint_y=None, height=dp(50))
        self.unit_input = StyledInput(hint_text="Единица (м, кг, шт)", text="м", multiline=False,
                                       size_hint_y=None, height=dp(50))
        self.quantity_input = StyledInput(hint_text="Остаток на складе", input_filter="float",
                                           multiline=False, size_hint_y=None, height=dp(50))
        self.price_input = StyledInput(hint_text="Цена за единицу", input_filter="float",
                                        multiline=False, size_hint_y=None, height=dp(50))

        for w in (self.name_input, self.unit_input, self.quantity_input, self.price_input):
            form.add_widget(w)

        self.error_label = wrap_label(text="", color=STATUS_OVERDUE, font_size=FONT_SMALL,
                                       size_hint_y=None, height=dp(24))
        form.add_widget(self.error_label)

        btn_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        self.save_btn = BronzeButton(text="Сохранить")
        self.save_btn.bind(on_release=self.save)
        cancel_btn = GhostButton(text="Отмена")
        cancel_btn.bind(on_release=self.cancel)
        btn_row.add_widget(self.save_btn)
        btn_row.add_widget(cancel_btn)
        form.add_widget(btn_row)

        form.add_widget(Widget())
        root.add_widget(form)
        root.add_widget(NavBar(active="materials"))
        self.add_widget(root)

    def load_material(self, material_id):
        self.editing_id = material_id
        if material_id is None:
            self.top_bar.set_subtitle("Новый материал")
            self.name_input.text = ""
            self.unit_input.text = "м"
            self.quantity_input.text = ""
            self.price_input.text = ""
        else:
            material = self.db.get_material(material_id)
            self.top_bar.set_subtitle("Изменить материал")
            self.name_input.text = material.name
            self.unit_input.text = material.unit
            self.quantity_input.text = f"{material.quantity:g}"
            self.price_input.text = f"{material.price_per_unit:g}"
        self.error_label.text = ""

    def cancel(self, *_):
        app = App.get_running_app()
        app.sm.current = "materials"

    def save(self, *_):
        name = self.name_input.text.strip()
        unit = self.unit_input.text.strip() or "м"
        if not name:
            self.error_label.text = "Укажите название материала"
            return
        try:
            quantity = float(self.quantity_input.text) if self.quantity_input.text.strip() else 0.0
            price = float(self.price_input.text) if self.price_input.text.strip() else 0.0
        except ValueError:
            self.error_label.text = "Остаток и цена должны быть числами"
            return

        if self.editing_id is None:
            self.db.add_material(Material(id=None, name=name, unit=unit, quantity=quantity, price_per_unit=price))
        else:
            self.db.update_material(Material(id=self.editing_id, name=name, unit=unit,
                                              quantity=quantity, price_per_unit=price))

        app = App.get_running_app()
        app.sm.current = "materials"


class OrderDetailScreen(Screen):
    """Детали заказа: списание материалов, прочие расходы, итоговая прибыль."""

    def __init__(self, db: OrderDB, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.order = None

        self.root_box = BoxLayout(orientation="vertical")
        self.top_bar = TopBar(subtitle="Заказ")
        self.root_box.add_widget(self.top_bar)

        self.scroll = ScrollView()
        self.content = BoxLayout(orientation="vertical", size_hint_y=None, padding=dp(14), spacing=dp(14))
        self.content.bind(minimum_height=self.content.setter("height"))
        self.scroll.add_widget(self.content)
        self.root_box.add_widget(self.scroll)

        back_btn = GhostButton(text="\u2190 К заказам", size_hint_y=None, height=dp(52))
        back_btn.bind(on_release=lambda *_: setattr(App.get_running_app().sm, "current", "orders"))
        self.root_box.add_widget(back_btn)

        self.add_widget(self.root_box)

    def load_order(self, order_id: int):
        self.order = self.db.get_by_id(order_id)
        if self.order:
            self.top_bar.set_subtitle(f"Заказ: {self.order.client_name}")
        self.refresh()

    def refresh(self):
        self.content.clear_widgets()
        if not self.order:
            return
        order = self.order
        app = App.get_running_app()
        currency = app.settings.get("currency", "")

        # --- шапка с инфо о заказе ---
        info_card = Card(bg_color=GLASS_PANEL, radius=dp(20), orientation="vertical",
                          padding=dp(14), spacing=dp(4), size_hint_y=None, height=dp(120))
        info_card.add_widget(wrap_label(
            text=f"[b]{order.client_name}[/b] \u2014 {order.item}", markup=True,
            font_size=FONT_SUBTITLE, color=CREAM, halign="left", valign="middle", size_hint_y=0.4,
        ))
        days = order.days_left
        deadline_text = f"Срок: {order.deadline.strftime('%d.%m.%Y')}   \u2022   "
        deadline_text += f"просрочен на {abs(days)} дн." if days < 0 else f"осталось {days} дн."
        info_card.add_widget(wrap_label(
            text=deadline_text, font_size=FONT_BODY, color=CREAM_DIM,
            halign="left", valign="middle", size_hint_y=0.3,
        ))
        info_card.add_widget(wrap_label(
            text=f"Цена заказа: {order.price:.0f} {currency}", font_size=FONT_BODY, color=BRONZE_LIGHT,
            halign="left", valign="middle", size_hint_y=0.3,
        ))
        self.content.add_widget(info_card)

        # --- материалы ---
        self.content.add_widget(wrap_label(
            text="Металл на заказ", bold=True, font_size=FONT_SUBTITLE, color=BRONZE_LIGHT,
            halign="left", valign="middle", size_hint_y=None, height=dp(28),
        ))

        order_materials = self.db.get_order_materials(order.id)
        for om in order_materials:
            row = Card(bg_color=GLASS_PANEL, radius=dp(16), orientation="horizontal",
                       padding=dp(10), spacing=dp(8), size_hint_y=None, height=dp(56))
            row.add_widget(wrap_label(
                text=f"{om.material_name}: {om.quantity_used:g} {om.unit}  \u2192  {om.cost:.0f} {currency}",
                font_size=FONT_SMALL, color=CREAM, halign="left", valign="middle",
            ))
            del_btn = DangerButton(text="X", size_hint_x=None, width=dp(44), font_size=FONT_SMALL)
            del_btn.bind(on_release=lambda *_, om_id=om.id: self.delete_material_usage(om_id))
            row.add_widget(del_btn)
            self.content.add_widget(row)

        materials = self.db.get_materials()
        if materials:
            add_card = Card(bg_color=GLASS_PANEL_LIGHT, radius=dp(18), orientation="vertical",
                             padding=dp(10), spacing=dp(8), size_hint_y=None, height=dp(150))
            self.material_spinner = Spinner(
                text=materials[0].name,
                values=[m.name for m in materials],
                size_hint_y=None, height=dp(44),
                background_color=GLASS_PANEL_LIGHT, color=CREAM,
            )
            self.material_qty_input = StyledInput(hint_text="Сколько потрачено", input_filter="float",
                                                    multiline=False, size_hint_y=None, height=dp(44))
            add_material_btn = BronzeButton(text="+ Списать материал", size_hint_y=None, height=dp(44))
            add_material_btn.bind(on_release=self.add_material_usage)
            add_card.add_widget(self.material_spinner)
            add_card.add_widget(self.material_qty_input)
            add_card.add_widget(add_material_btn)
            self.content.add_widget(add_card)
        else:
            self.content.add_widget(wrap_label(
                text="На складе пусто — сначала добавьте материалы в разделе «Склад»",
                font_size=FONT_SMALL, color=CREAM_DIM, halign="left", valign="middle",
                size_hint_y=None, height=dp(40),
            ))

        # --- прочие расходы ---
        self.content.add_widget(wrap_label(
            text="Прочие расходы", bold=True, font_size=FONT_SUBTITLE, color=BRONZE_LIGHT,
            halign="left", valign="middle", size_hint_y=None, height=dp(28),
        ))

        expenses = self.db.get_order_expenses(order.id)
        for exp in expenses:
            row = Card(bg_color=GLASS_PANEL, radius=dp(16), orientation="horizontal",
                       padding=dp(10), spacing=dp(8), size_hint_y=None, height=dp(56))
            row.add_widget(wrap_label(
                text=f"{exp.description}: {exp.amount:.0f} {currency}",
                font_size=FONT_SMALL, color=CREAM, halign="left", valign="middle",
            ))
            del_btn = DangerButton(text="X", size_hint_x=None, width=dp(44), font_size=FONT_SMALL)
            del_btn.bind(on_release=lambda *_, exp_id=exp.id: self.delete_expense(exp_id))
            row.add_widget(del_btn)
            self.content.add_widget(row)

        exp_card = Card(bg_color=GLASS_PANEL_LIGHT, radius=dp(18), orientation="vertical",
                         padding=dp(10), spacing=dp(8), size_hint_y=None, height=dp(150))
        self.expense_desc_input = StyledInput(hint_text="Расход (например, электроды)", multiline=False,
                                               size_hint_y=None, height=dp(44))
        self.expense_amount_input = StyledInput(hint_text="Сумма", input_filter="float", multiline=False,
                                                 size_hint_y=None, height=dp(44))
        add_expense_btn = BronzeButton(text="+ Добавить расход", size_hint_y=None, height=dp(44))
        add_expense_btn.bind(on_release=self.add_expense)
        exp_card.add_widget(self.expense_desc_input)
        exp_card.add_widget(self.expense_amount_input)
        exp_card.add_widget(add_expense_btn)
        self.content.add_widget(exp_card)

        # --- итог ---
        fin = self.db.get_order_financials(order.id, order.price)
        profit_color = STATUS_OK if fin["profit"] >= 0 else STATUS_OVERDUE
        summary = Card(bg_color=GLASS_PANEL, radius=dp(20), orientation="vertical",
                        padding=dp(14), spacing=dp(4), size_hint_y=None, height=dp(150))
        summary.add_widget(wrap_label(
            text=f"Металл: {fin['material_cost']:.0f} {currency}   \u2022   "
                 f"Расходы: {fin['expenses_total']:.0f} {currency}",
            font_size=FONT_BODY, color=CREAM_DIM, halign="left", valign="middle", size_hint_y=0.4,
        ))
        summary.add_widget(wrap_label(
            text=f"Себестоимость: {fin['total_cost']:.0f} {currency}",
            font_size=FONT_BODY, color=CREAM_DIM, halign="left", valign="middle", size_hint_y=0.3,
        ))
        summary.add_widget(wrap_label(
            text=f"[b]Чистая прибыль: {fin['profit']:.0f} {currency}[/b]", markup=True,
            font_size=FONT_TITLE, color=profit_color, halign="left", valign="middle", size_hint_y=0.3,
        ))
        self.content.add_widget(summary)

    def add_material_usage(self, *_):
        name = self.material_spinner.text
        material = next((m for m in self.db.get_materials() if m.name == name), None)
        if not material:
            return
        try:
            qty = float(self.material_qty_input.text)
        except (ValueError, TypeError):
            return
        if qty <= 0:
            return
        cost = qty * material.price_per_unit
        self.db.add_order_material(OrderMaterial(
            id=None, order_id=self.order.id, material_id=material.id,
            material_name=material.name, unit=material.unit, quantity_used=qty, cost=cost,
        ))
        self.refresh()

    def delete_material_usage(self, om_id: int):
        self.db.delete_order_material(om_id)
        self.refresh()

    def add_expense(self, *_):
        desc = self.expense_desc_input.text.strip()
        try:
            amount = float(self.expense_amount_input.text)
        except (ValueError, TypeError):
            return
        if not desc or amount <= 0:
            return
        self.db.add_order_expense(OrderExpense(id=None, order_id=self.order.id, description=desc, amount=amount))
        self.refresh()

    def delete_expense(self, exp_id: int):
        self.db.delete_order_expense(exp_id)
        self.refresh()


class SettingsScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        root = BoxLayout(orientation="vertical")
        root.add_widget(TopBar(subtitle="Настройки"))

        form = Card(bg_color=(0, 0, 0, 0), radius=0, orientation="vertical",
                    padding=dp(18), spacing=dp(10))

        self.company_input = StyledInput(multiline=False, size_hint_y=None, height=dp(50))
        self.warn_days_input = StyledInput(multiline=False, input_filter="int",
                                            size_hint_y=None, height=dp(50))
        self.interval_input = StyledInput(multiline=False, input_filter="int",
                                           size_hint_y=None, height=dp(50))
        self.currency_input = StyledInput(multiline=False, size_hint_y=None, height=dp(50))

        for label_text, widget in (
            ("Название компании", self.company_input),
            ("За сколько дней до срока предупреждать", self.warn_days_input),
            ("Как часто проверять сроки (часов)", self.interval_input),
            ("Символ валюты", self.currency_input),
        ):
            form.add_widget(wrap_label(text=label_text, color=CREAM_DIM, font_size=FONT_SMALL,
                                        size_hint_y=None, height=dp(20)))
            form.add_widget(widget)

        self.status_label = wrap_label(text="", color=BRONZE_LIGHT, font_size=FONT_SMALL,
                                        size_hint_y=None, height=dp(24))
        form.add_widget(self.status_label)

        save_btn = BronzeButton(text="Сохранить настройки", size_hint_y=None, height=dp(52))
        save_btn.bind(on_release=self.save)
        form.add_widget(save_btn)

        form.add_widget(Widget())
        root.add_widget(form)
        root.add_widget(NavBar(active="settings"))
        self.add_widget(root)

    def on_pre_enter(self, *args):
        s = self.app.settings
        self.company_input.text = s.get("company_name", "")
        self.warn_days_input.text = str(s.get("warn_days", 4))
        self.interval_input.text = str(s.get("notify_interval_hours", 6))
        self.currency_input.text = s.get("currency", "")
        self.status_label.text = ""

    def save(self, *_):
        try:
            warn_days = int(self.warn_days_input.text or 4)
            interval = int(self.interval_input.text or 6)
        except ValueError:
            self.status_label.text = "Дни и часы должны быть числами"
            self.status_label.color = STATUS_OVERDUE
            return

        self.app.settings["company_name"] = self.company_input.text.strip() or "WOOD METAL"
        self.app.settings["warn_days"] = max(0, warn_days)
        self.app.settings["notify_interval_hours"] = max(1, interval)
        self.app.settings["currency"] = self.currency_input.text.strip()
        self.app.apply_settings()

        self.status_label.text = "Сохранено"
        self.status_label.color = BRONZE_LIGHT


# --------------------------------------------------------------------- app --

class OrdersApp(App):
    def build(self):
        self.title = "Заказы — WOOD METAL"
        self.icon = "icon.png"
        self.settings = load_settings()
        self.db = OrderDB()

        root = FloatLayout()

        # фоновое изображение — без него полупрозрачные "стеклянные" панели
        # были бы не видны на однотонном фоне
        try:
            bg = Image(source="assets/bg_glass.jpg", allow_stretch=True, keep_ratio=False,
                       size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
            root.add_widget(bg)
        except Exception:
            pass

        self.sm = ScreenManager(transition=FadeTransition(duration=0.12),
                                 size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        self.sm.add_widget(OrdersScreen(self.db, name="orders"))
        self.sm.add_widget(AddOrderScreen(self.db, name="add"))
        self.sm.add_widget(OrderDetailScreen(self.db, name="order_detail"))
        self.sm.add_widget(MaterialsScreen(self.db, name="materials"))
        self.sm.add_widget(AddMaterialScreen(self.db, name="add_material"))
        self.sm.add_widget(SettingsScreen(self, name="settings"))
        root.add_widget(self.sm)

        self._notify_event = None
        Clock.schedule_once(lambda dt: self.run_notify_check(), 2)
        self._reschedule_notify()

        return root

    def apply_settings(self):
        save_settings(self.settings)
        self._reschedule_notify()

    def _reschedule_notify(self):
        if self._notify_event:
            self._notify_event.cancel()
        interval_sec = self.settings.get("notify_interval_hours", 6) * 60 * 60
        self._notify_event = Clock.schedule_interval(lambda dt: self.run_notify_check(), interval_sec)

    def run_notify_check(self):
        orders = self.db.get_all()
        check_and_notify(orders, warn_days=self.settings.get("warn_days", 4))


if __name__ == "__main__":
    OrdersApp().run()
