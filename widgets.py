from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.metrics import dp

from theme import (
    BRONZE, BRONZE_LIGHT,
    CREAM, CREAM_DIM, STATUS_OVERDUE,
    GLASS_PANEL, GLASS_PANEL_LIGHT, GLASS_BORDER, GLASS_HIGHLIGHT,
)


def _radius_list(radius):
    """Приводит radius (число или список из 1/4 значений) к списку для RoundedRectangle."""
    if isinstance(radius, (list, tuple)):
        return list(radius)
    return [radius]


class Card(BoxLayout):
    """Карточка в стиле матового стекла: полупрозрачный фон + тонкий бронзовый
    контур + лёгкий блик сверху. Хорошо смотрится поверх фонового изображения.

    radius может быть числом (одинаковое скругление всех углов — тогда рисуются
    ещё и блик с обводкой) или списком из 4 значений [tl, tr, br, bl] для
    асимметричного скругления (например, у верхней/нижней панелей) — в этом
    случае рисуется только сам полупрозрачный фон, без блика и обводки.

    Если glass=False или radius=0 — обычная плоская полупрозрачная заливка.
    """

    def __init__(self, bg_color=GLASS_PANEL, radius=dp(20), glass=True, **kwargs):
        super().__init__(**kwargs)
        self._radius = _radius_list(radius)
        uniform = len(set(self._radius)) <= 1
        self._glass = glass and uniform and self._radius[0] != 0

        with self.canvas.before:
            self._color_instr = Color(*bg_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=self._radius)

            if self._glass:
                Color(*GLASS_HIGHLIGHT)
                self._sheen = RoundedRectangle(pos=self.pos, size=(self.width, 1),
                                                radius=[self._radius[0], self._radius[0], 0, 0])

                Color(*GLASS_BORDER)
                self._border = Line(rounded_rectangle=(0, 0, 1, 1, self._radius[0]), width=1.1)

        self.bind(pos=self._update, size=self._update)

    def _update(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size
        if self._glass:
            self._sheen.pos = self.pos
            self._sheen.size = (self.width, max(1, self.height * 0.38))
            self._border.rounded_rectangle = (self.x, self.y, self.width, self.height, self._radius[0])

    def set_color(self, color):
        self._color_instr.rgba = color


class _RoundedButton(Button):
    """Капсульная кнопка (радиус = половина высоты, как в iOS) со сменой цвета при нажатии."""

    base_color = BRONZE
    pressed_color = BRONZE_LIGHT
    text_color = CREAM

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.color = self.text_color
        self.bold = True
        self.markup = True
        with self.canvas.before:
            self._color_instr = Color(*self.base_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(pos=self._update, size=self._update, state=self._on_state)

    def _update(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size
        # капсульная форма: радиус = половина меньшей стороны
        r = min(self.height, self.width) / 2
        self._rect.radius = [r]

    def _on_state(self, instance, value):
        self._color_instr.rgba = self.pressed_color if value == "down" else self.base_color


class BronzeButton(_RoundedButton):
    """Основная кнопка (главное действие) — сплошная бронза, как акцентная кнопка iOS."""
    base_color = BRONZE
    pressed_color = BRONZE_LIGHT
    text_color = (0.10, 0.07, 0.05, 1)


class GhostButton(_RoundedButton):
    """Второстепенная кнопка — стеклянная, приглушённая."""
    base_color = GLASS_PANEL_LIGHT
    pressed_color = (0.30, 0.22, 0.15, 0.7)
    text_color = BRONZE_LIGHT


class DangerButton(_RoundedButton):
    """Кнопка опасного действия (удалить) — приглушённое стекло с красным акцентом."""
    base_color = (0.34, 0.14, 0.12, 0.65)
    pressed_color = (0.5, 0.18, 0.14, 0.85)
    text_color = CREAM


class NavButton(_RoundedButton):
    """Кнопка нижней навигации — активная подсвечивается бронзой."""
    base_color = (0, 0, 0, 0)
    pressed_color = GLASS_PANEL_LIGHT
    text_color = CREAM_DIM

    def set_active(self, active: bool):
        if active:
            self._color_instr.rgba = BRONZE
            self.color = (0.10, 0.07, 0.05, 1)
        else:
            self._color_instr.rgba = (0, 0, 0, 0)
            self.color = CREAM_DIM


class StyledInput(TextInput):
    """Стеклянное поле ввода: полупрозрачный фон, скруглённые углы, мягкая обводка."""

    def __init__(self, radius=dp(14), **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_active = ""
        self.background_color = (0, 0, 0, 0)  # рисуем фон сами, чтобы получить скругления + стекло
        self.foreground_color = CREAM
        self.hint_text_color = CREAM_DIM
        self.cursor_color = BRONZE_LIGHT
        self.selection_color = (BRONZE[0], BRONZE[1], BRONZE[2], 0.35)
        self.padding = [dp(14), dp(12), dp(14), dp(12)]
        self.font_size = "15sp"

        self._radius = radius
        with self.canvas.before:
            self._color_instr = Color(*GLASS_PANEL_LIGHT)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
            Color(*GLASS_BORDER)
            self._border = Line(rounded_rectangle=(0, 0, 1, 1, radius), width=1)
        self.bind(pos=self._update, size=self._update)

    def _update(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._border.rounded_rectangle = (self.x, self.y, self.width, self.height, self._radius)
