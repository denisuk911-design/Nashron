from __future__ import annotations

from PySide6.QtGui import QColor, QPalette

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


class ThemeManager:
    """Keeps application styling in one place so widgets only use object names."""

    @staticmethod
    def stylesheet(theme: str = "dark") -> str:
        if theme == "light":
            return ThemeManager._stylesheet(LIGHT_COLORS)
        return ThemeManager._stylesheet(DARK_COLORS)

    @staticmethod
    def palette(theme: str = "dark") -> QPalette:
        c = LIGHT_COLORS if theme == "light" else DARK_COLORS
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
    def _stylesheet(c: dict[str, str]) -> str:
        f = TOKENS.font_family
        return f"""
        QWidget {{ color: {c['text']}; font-family: {f}; font-size: 10pt; }}
        QMainWindow, QDialog, QMessageBox {{ background: {c['dialog_bg']}; color: {c['text']}; }}
        QMessageBox QLabel, QDialog QLabel {{ color: {c['text']}; }}
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
        QLabel#appLogo {{ color: {c['text']}; font-size: 18pt; font-weight: 800; border: 1px solid {c['violet']}; border-radius: 22px; min-width: 44px; min-height: 44px; max-width: 44px; max-height: 44px; }}
        QLabel#brandMark {{ color: {c['cyan']}; font-size: 14pt; font-weight: 700; border: 1px solid {c['cyan_dark']}; border-radius: 8px; padding: 2px 6px; }}
        QLabel#pageTitle {{ color: {c['text']}; font-size: 11pt; font-weight: 700; }}
        QLabel#sectionTitle {{ color: #80bfe4; font-size: 10pt; font-weight: 700; }}
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
        QScrollBar::handle:vertical {{ background: #29435d; border-radius: 4px; min-height: 30px; }}
        QScrollBar::handle:vertical:hover {{ background: {c['cyan_dark']}; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
        QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 4px; }}
        QScrollBar::handle:horizontal {{ background: #29435d; border-radius: 4px; min-width: 30px; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
        QScrollArea {{ background: transparent; border: 0; }}
        QFrame#messageRow {{ background: transparent; border: 0; }}
        QFrame#messageCard {{ background: {c['roman_bubble']}; border: 1px solid {c['line_soft']}; border-radius: 18px; }}
        QFrame#messageCardPetr {{ background: {c['petr_bubble']}; border: 1px solid #2c7a5b; border-radius: 18px; }}
        QFrame#messageCardUser {{ background: {c['user_bubble']}; border: 1px solid {c['violet']}; border-radius: 18px; }}
        QLabel#messageAvatar {{ border-radius: 24px; }}
        QLabel#messageBody {{ color: {c['text']}; font-size: 11pt; line-height: 1.38; }}
        QLabel#messageMeta {{ color: {c['muted']}; font-size: 8pt; }}
        QLabel#messageRole {{ color: {c['muted']}; font-size: 8pt; padding-left: 6px; }}
        QLabel#messageActivity {{ color: {c['muted_2']}; font-size: 8pt; font-style: italic; padding-top: 2px; }}
        QLabel#goalBanner {{ color: {c['text']}; background: {c['surface_alt']}; border: 1px solid {c['violet']}; border-radius: 12px; padding: 8px 14px; margin: 0 28px; font-size: 9pt; }}
        QLabel#imageThumbnail {{ background: {c['bg']}; border: 1px solid {c['line']}; border-radius: 8px; padding: 4px; }}
        QLabel#typingBubble {{ color: #9fdde1; background: {c['roman_bubble']}; border: 1px solid {c['cyan_dark']}; border-radius: 16px; padding: 8px 12px; }}
        QProgressBar {{ background: {c['surface']}; border: 0; border-radius: 4px; height: 7px; text-visible: 0; }}
        QProgressBar::chunk {{ background: {c['cyan']}; border-radius: 4px; }}
        QSplitter::handle {{ background: {c['line']}; width: 1px; }}
        """
