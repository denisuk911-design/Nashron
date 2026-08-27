from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from .design_tokens import TOKENS


DARK_COLORS = {
    "bg": "#0f141b",
    "chat_bg": "#081421",
    "surface": "#101b2a",
    "surface_alt": "#17263a",
    "surface_hover": "#21344d",
    "line": "#263b59",
    "line_soft": "#17273b",
    "text": "#f3f6fb",
    "muted": "#b6c0ce",
    "muted_2": "#8793a3",
    "input": "#101821",
    "cyan": "#5de0c1",
    "cyan_dark": "#2e9ed8",
    "violet": "#6554f2",
    "violet_dark": "#4433d6",
    "green": "#54d18f",
    "amber": "#e0b15c",
    "red": "#e06c75",
    "user_bubble": "qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7357ff, stop:1 #3d5df5)",
    "roman_bubble": "#1a2a3f",
    "petr_bubble": "#173728",
    "dialog_bg": "#151b23",
    "button_text": "#f3f6fb",
}

LIGHT_COLORS = {
    "bg": "#f5f7fb",
    "chat_bg": "#f7faff",
    "surface": "#ffffff",
    "surface_alt": "#eef3f8",
    "surface_hover": "#e6edf5",
    "line": "#ccd7e5",
    "line_soft": "#dbe4ef",
    "text": "#162033",
    "muted": "#53657a",
    "muted_2": "#74849a",
    "input": "#ffffff",
    "cyan": "#087f9a",
    "cyan_dark": "#0b6f88",
    "violet": "#6757d8",
    "violet_dark": "#5143b5",
    "green": "#168a53",
    "amber": "#9a6a12",
    "red": "#b83a45",
    "user_bubble": "#e4ebff",
    "roman_bubble": "#ffffff",
    "petr_bubble": "#e8f6ef",
    "dialog_bg": "#ffffff",
    "button_text": "#162033",
}


def _dark_variant(**overrides: str) -> dict[str, str]:
    colors = dict(DARK_COLORS)
    colors.update(overrides)
    return colors


THEME_COLORS = {
    "dark": DARK_COLORS,
    "light": LIGHT_COLORS,
    "dark_graphite": _dark_variant(
        bg="#111318", chat_bg="#171a20", surface="#1d2028", surface_alt="#252a34",
        surface_hover="#303744", line="#3a4352", line_soft="#2b313c", cyan="#8ed4c3",
        cyan_dark="#6a9fbd", violet="#737bff", violet_dark="#515bd1", roman_bubble="#202632",
        petr_bubble="#19352f", dialog_bg="#171a20",
    ),
    "dark_ocean": _dark_variant(
        bg="#071522", chat_bg="#082238", surface="#0e2538", surface_alt="#15334b",
        surface_hover="#1b4562", line="#24516e", line_soft="#19384f", cyan="#68e0d0",
        cyan_dark="#48a9d2", violet="#5f73ff", violet_dark="#394dc4", roman_bubble="#12304a",
        petr_bubble="#123a38", dialog_bg="#0e2538",
    ),
    "dark_forest": _dark_variant(
        bg="#0b1714", chat_bg="#0c211c", surface="#13271f", surface_alt="#1b352a",
        surface_hover="#264936", line="#315c46", line_soft="#244432", cyan="#8bd8a8",
        cyan_dark="#51a982", violet="#7968e8", violet_dark="#5343bc", roman_bubble="#183329",
        petr_bubble="#173b2b", dialog_bg="#13271f",
    ),
    "dark_amber": _dark_variant(
        bg="#19140e", chat_bg="#211a10", surface="#2a2116", surface_alt="#382b1a",
        surface_hover="#4a3820", line="#66502b", line_soft="#49391f", cyan="#e1d08a",
        cyan_dark="#c49d52", violet="#806be3", violet_dark="#5845ba", roman_bubble="#30271b",
        petr_bubble="#253523", dialog_bg="#2a2116",
    ),
    "night_city": _dark_variant(
        bg="#080d19", chat_bg="#0b1324", surface="#101b31", surface_alt="#172642",
        surface_hover="#21365a", line="#2c4670", line_soft="#1d3152", cyan="#7ee7f5",
        cyan_dark="#3e9fe0", violet="#6c63ff", violet_dark="#4b43c8", roman_bubble="#14243e",
        petr_bubble="#132d35", dialog_bg="#0c1424",
    ),
    "city": _dark_variant(
        bg="#101720", chat_bg="#131d29", surface="#1a2735", surface_alt="#223244",
        surface_hover="#2b4055", line="#38526b", line_soft="#263b50", cyan="#82d4d8",
        cyan_dark="#5a9bbd", violet="#6977e8", violet_dark="#4b57bd", roman_bubble="#1d2c3d",
        petr_bubble="#183535", dialog_bg="#131d29",
    ),
    "mountains": _dark_variant(
        bg="#10161c", chat_bg="#151d24", surface="#1c2730", surface_alt="#26333d",
        surface_hover="#33434f", line="#455965", line_soft="#303f49", cyan="#9bc7c8",
        cyan_dark="#729baa", violet="#747dd7", violet_dark="#555eaf", roman_bubble="#22313e",
        petr_bubble="#203b35", dialog_bg="#151d24",
    ),
    "space": _dark_variant(
        bg="#080a13", chat_bg="#0c1020", surface="#141a2d", surface_alt="#1c2440",
        surface_hover="#273154", line="#38456e", line_soft="#252e4c", cyan="#79d8e7",
        cyan_dark="#4b95c4", violet="#7868f4", violet_dark="#5646c7", roman_bubble="#19223a",
        petr_bubble="#173433", dialog_bg="#0c1020",
    ),
    "warm_paper": {
        **LIGHT_COLORS,
        "bg": "#e9e2d5", "chat_bg": "#f4eee3", "surface": "#fffaf1", "surface_alt": "#eee5d6",
        "surface_hover": "#e5d9c8", "line": "#cdbfae", "line_soft": "#ded2c1", "text": "#292622",
        "muted": "#6e655b", "muted_2": "#8e8275", "input": "#fffdf8", "cyan": "#267d79",
        "cyan_dark": "#286b8a", "violet": "#7561c9", "violet_dark": "#57459d", "green": "#3c8055",
        "user_bubble": "#e3e0ff", "roman_bubble": "#fffaf1", "petr_bubble": "#e2f1e6",
        "dialog_bg": "#f7f2e9", "button_text": "#292622",
    },
    "minimal": {
        **DARK_COLORS,
        "bg": "#101216", "chat_bg": "#101216", "surface": "#17191e", "surface_alt": "#1e2128",
        "surface_hover": "#282c35", "line": "#303641", "line_soft": "#242831", "cyan": "#b7c4d6",
        "cyan_dark": "#8294ad", "violet": "#667085", "violet_dark": "#4d596b", "roman_bubble": "#1a1d23",
        "petr_bubble": "#1b2523", "dialog_bg": "#14161a",
    },
}


@dataclass(frozen=True)
class ThemeDefinition:
    theme_id: str
    name_key: str
    colors: dict[str, str]
    pattern: str
    pattern_alpha: int
    dark_chrome: bool


_THEME_PATTERNS = {
    "dark": ("stars", 36),
    "light": ("stars", 20),
    "dark_graphite": ("graphite", 28),
    "dark_ocean": ("ocean", 34),
    "dark_forest": ("forest", 30),
    "dark_amber": ("workshop", 30),
    "night_city": ("city", 34),
    "city": ("city", 18),
    "mountains": ("graphite", 16),
    "space": ("stars", 18),
    "warm_paper": ("paper", 20),
    "minimal": ("none", 0),
}

THEME_DEFINITIONS = {
    theme_id: ThemeDefinition(
        theme_id=theme_id,
        name_key=f"theme.{theme_id}",
        colors=colors,
        pattern=_THEME_PATTERNS[theme_id][0],
        pattern_alpha=_THEME_PATTERNS[theme_id][1],
        dark_chrome=theme_id not in {"light", "warm_paper"},
    )
    for theme_id, colors in THEME_COLORS.items()
}


class ThemeBackdrop(QWidget):
    """Chat background with a very low-contrast, theme-specific line pattern."""

    def __init__(self, theme: str = "dark") -> None:
        super().__init__()
        self._theme = theme if theme in THEME_DEFINITIONS else "dark"
        self._background_path = ""
        self._background_pixmap = QPixmap()
        self._background_opacity = 18
        self._background_mode = "cover"
        self._background_darkening = 45
        self._background_blur = 0
        self.setAttribute(Qt.WA_StyledBackground, True)

    def set_theme(self, theme: str) -> None:
        self._theme = theme if theme in THEME_DEFINITIONS else "dark"
        self.update()

    def set_background(
        self,
        path: str = "",
        opacity: int = 18,
        mode: str = "cover",
        darkening: int = 45,
        blur: int = 0,
    ) -> None:
        next_path = str(path or "").strip()
        if next_path != self._background_path:
            self._background_path = next_path
            self._background_pixmap = QPixmap(next_path) if next_path else QPixmap()
        try:
            next_opacity = int(opacity)
        except (TypeError, ValueError):
            next_opacity = 18
        self._background_opacity = max(0, min(70, next_opacity))
        self._background_mode = mode if mode in {"cover", "fit", "tile", "center", "stretch"} else "cover"
        self._background_darkening = max(0, min(90, int(darkening)))
        self._background_blur = max(0, min(20, int(blur)))
        self.update()

    def paintEvent(self, event) -> None:
        definition = THEME_DEFINITIONS.get(self._theme, THEME_DEFINITIONS["dark"])
        colors = definition.colors
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(colors["chat_bg"]))
        if self._background_path:
            pixmap = self._background_pixmap
            if not pixmap.isNull() and self._background_opacity:
                if self._background_blur:
                    factor = max(2, min(12, self._background_blur // 2 + 2))
                    small = pixmap.scaled(
                        max(1, pixmap.width() // factor),
                        max(1, pixmap.height() // factor),
                        Qt.IgnoreAspectRatio,
                        Qt.SmoothTransformation,
                    )
                    pixmap = small.scaled(pixmap.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                painter.save()
                painter.setOpacity(self._background_opacity / 100.0)
                if self._background_mode == "tile":
                    painter.drawTiledPixmap(self.rect(), pixmap)
                elif self._background_mode == "center":
                    x = (self.width() - pixmap.width()) // 2
                    y = (self.height() - pixmap.height()) // 2
                    painter.drawPixmap(x, y, pixmap)
                elif self._background_mode == "fit":
                    scaled = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    x = (self.width() - scaled.width()) // 2
                    y = (self.height() - scaled.height()) // 2
                    painter.drawPixmap(x, y, scaled)
                elif self._background_mode == "stretch":
                    painter.drawPixmap(self.rect(), pixmap)
                else:
                    scaled = pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    x = (self.width() - scaled.width()) // 2
                    y = (self.height() - scaled.height()) // 2
                    painter.drawPixmap(x, y, scaled)
                painter.restore()
                overlay = QColor(colors["chat_bg"])
                overlay.setAlpha(round(255 * self._background_darkening / 100))
                painter.fillRect(self.rect(), overlay)
        pen = QPen(QColor(colors["line"]))
        pen.setWidth(1)
        pen.setColor(QColor(colors["line"]))
        pen.setStyle(Qt.SolidLine)
        # Keep the pattern deliberately quiet so the message text remains primary.
        pattern_color = QColor(colors["line"])
        pattern_color.setAlpha(definition.pattern_alpha)
        pen.setColor(pattern_color)
        painter.setPen(pen)
        width, height = self.width(), self.height()
        if definition.pattern == "none":
            pass
        elif definition.pattern == "city":
            for x in range(40, width + 80, 140):
                building_height = 70 + (x % 170)
                painter.drawRect(x, height - building_height, 86, building_height)
                for wy in range(height - building_height + 24, height - 16, 34):
                    painter.drawPoint(x + 18, wy)
                    painter.drawPoint(x + 50, wy)
            for y in range(60, height, 120):
                painter.drawLine(0, y, width, y)
        elif definition.pattern == "paper":
            for x in range(0, width, 34):
                painter.drawLine(x, 0, x + 90, height)
        elif definition.pattern == "ocean":
            for y in range(80, height + 220, 150):
                painter.drawArc(-120, y - 70, width // 2 + 240, 150, 0, 180 * 16)
        elif definition.pattern == "forest":
            for x in range(80, width + 220, 190):
                painter.drawLine(x, height, x - 48, max(0, height - 240))
                painter.drawLine(x - 30, height - 115, x - 105, height - 165)
                painter.drawLine(x - 15, height - 160, x + 62, height - 215)
        elif definition.pattern == "workshop":
            for y in range(110, height, 190):
                painter.drawLine(40, y, 150, y)
                painter.drawLine(150, y, 190, y + 36)
                painter.drawEllipse(QPointF(36, y - 4), 4, 4)
        elif definition.pattern == "graphite":
            for x in range(-height, width, 180):
                painter.drawLine(x, 0, x + height, height)
        elif definition.pattern == "stars":
            for x, y in ((90, 120), (260, 260), (520, 150), (760, 360), (980, 180), (1240, 300)):
                if x < width and y < height:
                    painter.drawEllipse(QPointF(x, y), 2, 2)
        painter.end()


class ThemeManager:
    """Keeps application styling in one place so widgets only use object names."""

    @staticmethod
    def theme_ids() -> tuple[str, ...]:
        return tuple(THEME_DEFINITIONS)

    @staticmethod
    def definition(theme: str = "dark") -> ThemeDefinition:
        return THEME_DEFINITIONS.get(theme, THEME_DEFINITIONS["dark"])

    @staticmethod
    def stylesheet(theme: str = "dark") -> str:
        return ThemeManager._stylesheet(ThemeManager.definition(theme).colors)

    @staticmethod
    def palette(theme: str = "dark") -> QPalette:
        c = ThemeManager.definition(theme).colors
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(c["dialog_bg"]))
        palette.setColor(QPalette.WindowText, QColor(c["text"]))
        palette.setColor(QPalette.Base, QColor(c["input"]))
        palette.setColor(QPalette.AlternateBase, QColor(c["surface_alt"]))
        palette.setColor(QPalette.ToolTipBase, QColor(c["surface"]))
        palette.setColor(QPalette.ToolTipText, QColor(c["text"]))
        palette.setColor(QPalette.Text, QColor(c["text"]))
        palette.setColor(QPalette.Button, QColor(c["surface_alt"]))
        palette.setColor(QPalette.ButtonText, QColor(c["button_text"]))
        palette.setColor(QPalette.Highlight, QColor(c["violet"]))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        palette.setColor(QPalette.PlaceholderText, QColor(c["muted_2"]))
        return palette

    @staticmethod
    def native_chrome_colors(theme: str = "dark") -> tuple[bool, int, int, int]:
        definition = ThemeManager.definition(theme)
        colors = definition.colors

        def colorref(value: str) -> int:
            value = value.lstrip("#")
            red, green, blue = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
            return red | (green << 8) | (blue << 16)

        return definition.dark_chrome, colorref(colors["dialog_bg"]), colorref(colors["text"]), colorref(colors["line"])

    @staticmethod
    def _stylesheet(c: dict[str, str]) -> str:
        f = TOKENS.font_family
        return f"""
        QWidget {{ color: {c['text']}; font-family: {f}; font-size: 10pt; }}
        QMainWindow, QDialog, QMessageBox {{ background: {c['dialog_bg']}; color: {c['text']}; }}
        QDialog QWidget, QMessageBox QWidget {{ background: {c['dialog_bg']}; color: {c['text']}; }}
        QMessageBox QLabel, QDialog QLabel {{ color: {c['text']}; }}
        QDialog QTabWidget::pane, QDialog QStackedWidget, QDialog QWizard, QDialog QWizardPage {{ background: {c['dialog_bg']}; color: {c['text']}; border: 0; }}
        QTabBar::tab {{ background: {c['surface_alt']}; color: {c['muted']}; border: 1px solid {c['line']}; padding: 7px 12px; }}
        QTabBar::tab:selected, QTabBar::tab:hover {{ background: {c['surface_hover']}; color: {c['text']}; border-color: {c['cyan_dark']}; }}
        QGroupBox {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['line']}; border-radius: 8px; margin-top: 12px; padding: 12px 8px 8px; }}
        QGroupBox::title {{ color: {c['text']}; subcontrol-position: top left; padding: 0 5px; }}
        QTableWidget, QTableView, QTreeWidget, QDialog QListWidget, QDialog QTreeView, QTextBrowser {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['line']}; alternate-background-color: {c['surface_alt']}; selection-background-color: {c['violet_dark']}; selection-color: #ffffff; }}
        QHeaderView::section {{ background: {c['surface_alt']}; color: {c['text']}; border: 1px solid {c['line']}; padding: 6px; }}
        QTableWidget::item, QTableView::item, QTreeWidget::item {{ color: {c['text']}; padding: 4px; }}
        QDialog QFrame {{ color: {c['text']}; }}
        QMessageBox QPushButton, QDialog QPushButton, QPushButton {{
            background: {c['surface_alt']};
            color: {c['button_text']};
            border: 1px solid {c['line']};
            border-radius: 8px;
            padding: 7px 12px;
        }}
        QMessageBox QPushButton:hover, QDialog QPushButton:hover, QPushButton:hover {{
            background: {c['surface_hover']};
            border-color: {c['cyan_dark']};
        }}
        QComboBox, QSpinBox {{
            background: {c['input']};
            color: {c['text']};
            border: 1px solid {c['line']};
            border-radius: 8px;
            padding: 6px 9px;
        }}
        QComboBox QAbstractItemView {{
            background: {c['surface']};
            color: {c['text']};
            border: 1px solid {c['line']};
            selection-background-color: {c['surface_hover']};
            selection-color: {c['text']};
        }}
        QCheckBox {{ color: {c['text']}; spacing: 8px; }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {c['line']};
            border-radius: 4px;
            background: {c['input']};
        }}
        QCheckBox::indicator:checked {{ background: {c['cyan_dark']}; border-color: {c['cyan_dark']}; }}
        QWidget#appRoot {{ background: {c['bg']}; }}
        QWidget#topBar {{ background: {c['surface']}; border-bottom: 1px solid {c['line']}; }}
        QWidget#statusBar {{ background: {c['surface']}; border-top: 1px solid {c['line_soft']}; }}
        QWidget#composer {{ background: transparent; border-top: 1px solid {c['line_soft']}; }}
        QWidget#navPanel, QWidget#inspectorPanel {{ background: {c['surface']}; border: 1px solid {c['line']}; border-radius: 8px; }}
        QWidget#chatPanel {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {c['chat_bg']}, stop:1 {c['bg']}); }}
        QFrame#card {{ background: {c['surface_alt']}; border: 1px solid {c['line']}; border-radius: 8px; }}
        QFrame#profileCard {{ background: {c['surface_alt']}; border: 1px solid {c['line']}; border-left: 2px solid {c['cyan']}; border-radius: 8px; }}
        QLabel#brand {{ color: {c['text']}; font-size: 16pt; font-weight: 700; }}
        QLabel#brandSubtitle {{ color: {c['muted']}; font-size: 10pt; }}
        QLabel#appLogo {{ background: transparent; min-width: 44px; min-height: 44px; max-width: 44px; max-height: 44px; }}
        QLabel#brandImage {{ background: transparent; min-width: 34px; min-height: 34px; max-width: 34px; max-height: 34px; }}
        QLabel#brandMark {{ color: {c['cyan']}; font-size: 14pt; font-weight: 700; border: 1px solid {c['cyan_dark']}; border-radius: 8px; padding: 2px 6px; }}
        QLabel#pageTitle {{ color: {c['text']}; font-size: 11pt; font-weight: 700; }}
        QLabel#sectionTitle {{ color: {c['cyan']}; font-size: 10pt; font-weight: 700; }}
        QLabel#muted {{ color: {c['muted']}; }}
        QLabel#tiny {{ color: {c['muted_2']}; font-size: 8pt; }}
        QLabel#online {{ color: {c['green']}; font-size: 9pt; }}
        QLabel#statusPill {{ color: {c['text']}; background: {c['surface_alt']}; border: 1px solid {c['line_soft']}; border-radius: 16px; padding: 8px 14px; font-size: 9pt; }}
        QToolButton, QPushButton#iconButton {{ background: transparent; color: {c['muted']}; border: 1px solid transparent; border-radius: 8px; padding: 7px; }}
        QToolButton:hover, QPushButton#iconButton:hover {{ background: {c['surface_hover']}; color: {c['text']}; border-color: {c['line']}; }}
        QPushButton#primaryButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {c['cyan_dark']}, stop:1 {c['violet_dark']}); color: white; border: 0; border-radius: 9px; padding: 10px 14px; font-weight: 700; }}
        QPushButton#primaryButton:hover {{ background: {c['cyan_dark']}; }}
        QPushButton#smallAction {{ background: {c['surface']}; color: {c['muted']}; border: 1px solid {c['line']}; border-radius: 9px; padding: 9px 10px; }}
        QPushButton#smallAction:hover {{ background: {c['surface_hover']}; color: {c['text']}; border-color: {c['cyan_dark']}; }}
        QPushButton#sendButton {{ background: {c['violet']}; color: white; border: 0; border-radius: 18px; font-size: 14pt; padding: 4px 12px; }}
        QPushButton#sendButton:hover {{ background: #9675f2; }}
        QPushButton#roundIconButton {{ background: {c['surface_alt']}; color: {c['muted']}; border: 1px solid {c['line']}; border-radius: 20px; font-size: 15pt; padding: 0; }}
        QPushButton#roundIconButton:hover {{ background: {c['surface_hover']}; color: {c['text']}; border-color: {c['cyan_dark']}; }}
        QPushButton#stopButton {{ background: {c['red']}; color: white; border: 0; border-radius: 9px; padding: 8px 12px; }}
        QLineEdit, QTextEdit {{ background: {c['input']}; color: {c['text']}; border: 1px solid {c['line']}; border-radius: 8px; padding: 8px 10px; selection-background-color: {c['violet_dark']}; selection-color: white; }}
        QTextEdit#messageInput {{ background: {c['surface']}; border: 1px solid {c['line']}; border-radius: 22px; padding: 12px 16px; }}
        QLineEdit:focus, QTextEdit:focus {{ border-color: {c['cyan_dark']}; }}
        QListWidget#messageList {{ background: transparent; border: 0; outline: 0; padding: 18px 28px; }}
        QListWidget#messageList::item {{ border: 0; padding: 0; margin: 8px 0; }}
        QListWidget#conversationList {{ background: transparent; border: 0; outline: 0; }}
        QListWidget#conversationList::item {{ color: {c['muted']}; padding: 10px; border-radius: 9px; }}
        QListWidget#conversationList::item:selected, QListWidget#conversationList::item:hover {{ background: {c['surface_hover']}; color: {c['text']}; }}
        QScrollBar:vertical {{ background: transparent; width: 8px; margin: 4px; }}
        QScrollBar::handle:vertical {{ background: {c['line']}; border-radius: 4px; min-height: 30px; }}
        QScrollBar::handle:vertical:hover {{ background: {c['cyan_dark']}; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
        QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 4px; }}
        QScrollBar::handle:horizontal {{ background: {c['line']}; border-radius: 4px; min-width: 30px; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
        QScrollArea {{ background: transparent; border: 0; }}
        QFrame#messageRow {{ background: transparent; border: 0; }}
        QFrame#messageCard {{ background: {c['roman_bubble']}; border: 1px solid {c['line_soft']}; border-radius: 18px; }}
        QFrame#messageCardPetr {{ background: {c['petr_bubble']}; border: 1px solid {c['green']}; border-radius: 18px; }}
        QFrame#messageCardUser {{ background: {c['user_bubble']}; border: 1px solid {c['violet']}; border-radius: 18px; }}
        QFrame#messageCard[selected="true"], QFrame#messageCardPetr[selected="true"], QFrame#messageCardUser[selected="true"] {{ border: 2px solid {c['cyan']}; background: {c['surface_hover']}; }}
        QLabel#messageAvatar {{ border-radius: 24px; }}
        QLabel#messageBody {{ color: {c['text']}; font-size: 11pt; line-height: 1.38; }}
        QLabel#messageMeta {{ color: {c['muted']}; font-size: 8pt; }}
        QLabel#messageRole {{ color: {c['muted']}; font-size: 8pt; padding-left: 6px; }}
        QLabel#messageActivity {{ color: {c['muted_2']}; font-size: 8pt; font-style: italic; padding-top: 2px; }}
        QLabel#goalBanner {{ color: {c['text']}; background: {c['surface_alt']}; border: 1px solid {c['violet']}; border-radius: 12px; padding: 8px 14px; margin: 0 28px; font-size: 9pt; }}
        QLabel#imageThumbnail {{ background: {c['bg']}; border: 1px solid {c['line']}; border-radius: 8px; padding: 4px; }}
        QLabel#typingBubble {{ color: #9fdde1; background: {c['roman_bubble']}; border: 1px solid {c['cyan_dark']}; border-radius: 16px; padding: 8px 12px; }}
        QPushButton#newMessagesButton {{ background: {c['violet']}; color: #ffffff; border: 0; border-radius: 14px; padding: 6px 12px; font-size: 9pt; }}
        QPushButton#newMessagesButton:hover {{ background: {c['violet_dark']}; }}
        QProgressBar {{ background: {c['surface']}; border: 0; border-radius: 4px; height: 7px; text-visible: 0; }}
        QProgressBar::chunk {{ background: {c['cyan']}; border-radius: 4px; }}
        QSplitter::handle {{ background: {c['line']}; width: 1px; }}
        """
