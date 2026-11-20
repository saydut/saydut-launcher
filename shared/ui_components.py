"""
Modern UI Components for Saydut Launcher
Shared gradient widgets with glow effects, animations, and modern styling
"""
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QLineEdit,
    QTextEdit, QProgressBar, QVBoxLayout, QHBoxLayout
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import (
    QPainter, QColor, QRadialGradient, QLinearGradient,
    QFont, QPen, QBrush, QPixmap, QPainterPath
)
from PySide6.QtWidgets import QGraphicsDropShadowEffect


# ============================================================================
# COLOR CONSTANTS
# ============================================================================

class Colors:
    """Modern color palette for Saydut Launcher"""
    # Background
    BG_PRIMARY = '#0b1324'
    BG_SECONDARY = '#1a2438'
    BG_ELEVATED = 'rgba(24, 32, 52, 0.85)'
    BG_GLASS = 'rgba(15, 23, 42, 0.5)'

    # Accent colors
    ACCENT_BLUE = '#38bdf8'
    ACCENT_PURPLE = '#6366f1'
    ACCENT_PINK = '#ec4899'
    ACCENT_CYAN = '#22d3ee'
    ACCENT_INDIGO = '#8b5cf6'
    ACCENT_ORANGE = '#f97316'
    ACCENT_TEAL = '#14b8a6'
    ACCENT_GREEN = '#22c55e'
    ACCENT_RED = '#ef4444'
    ACCENT_AMBER = '#f59e0b'

    # Text
    TEXT_PRIMARY = '#f8fafc'
    TEXT_SECONDARY = '#e2e8f0'
    TEXT_TERTIARY = '#94a3b8'
    TEXT_DISABLED = '#64748b'

    # States
    SUCCESS = '#22c55e'
    WARNING = '#f59e0b'
    ERROR = '#ef4444'
    INFO = '#38bdf8'


# ============================================================================
# BACKGROUND & EFFECTS
# ============================================================================

class GlowBackground(QWidget):
    """
    Animated radial gradient background with grid overlay
    Extracted from launcher's GlowBackground widget
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(Colors.BG_PRIMARY))

        # Glow 1: Top-left cyan
        glow1 = QRadialGradient(120, 80, 320)
        glow1.setColorAt(0.0, QColor(56, 189, 248, 110))  # Cyan
        glow1.setColorAt(0.6, QColor(56, 189, 248, 35))
        glow1.setColorAt(1.0, QColor(11, 19, 36, 0))
        painter.fillRect(self.rect(), glow1)

        # Glow 2: Top-right indigo
        glow2 = QRadialGradient(self.width() - 120, 140, 380)
        glow2.setColorAt(0.0, QColor(99, 102, 241, 100))  # Indigo
        glow2.setColorAt(0.6, QColor(99, 102, 241, 30))
        glow2.setColorAt(1.0, QColor(11, 19, 36, 0))
        painter.fillRect(self.rect(), glow2)

        # Glow 3: Bottom-center pink
        glow3 = QRadialGradient(self.width() * 0.5, self.height() - 80, 420)
        glow3.setColorAt(0.0, QColor(236, 72, 153, 80))  # Pink
        glow3.setColorAt(0.6, QColor(236, 72, 153, 24))
        glow3.setColorAt(1.0, QColor(11, 19, 36, 0))
        painter.fillRect(self.rect(), glow3)

        # Grid overlay
        painter.setPen(QColor(30, 41, 59, 60))
        step = 48
        for x in range(0, self.width(), step):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), step):
            painter.drawLine(0, y, self.width(), y)

        super().paintEvent(event)


class AnimatedHeader(QFrame):
    """
    3-phase animated gradient header
    Cycles through cyan → indigo → teal gradients
    """
    def __init__(self, title: str = "", subtitle: str = ""):
        super().__init__()
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)  # 1 second per phase

        self.setFixedHeight(120)

        # Create text labels if provided
        if title or subtitle:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(24, 20, 24, 20)

            if title:
                self.title_label = QLabel(title)
                self.title_label.setStyleSheet(
                    "color: #ffffff; font-size: 28px; font-weight: 800; "
                    "background: transparent;"
                )
                layout.addWidget(self.title_label)

            if subtitle:
                self.subtitle_label = QLabel(subtitle)
                self.subtitle_label.setStyleSheet(
                    "color: #e2e8f0; font-size: 14px; font-weight: 500; "
                    "background: transparent;"
                )
                layout.addWidget(self.subtitle_label)

    def set_title(self, title: str, subtitle: str = ""):
        """Update header title and subtitle"""
        if hasattr(self, 'title_label'):
            self.title_label.setText(title)
        if subtitle and hasattr(self, 'subtitle_label'):
            self.subtitle_label.setText(subtitle)

    def _tick(self):
        self._phase = (self._phase + 1) % 3
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, self.width(), self.height())

        # Phase 0: Cyan → Indigo → Pink
        if self._phase == 0:
            gradient.setColorAt(0.0, QColor("#0ea5e9"))
            gradient.setColorAt(0.5, QColor("#6366f1"))
            gradient.setColorAt(1.0, QColor("#ec4899"))
        # Phase 1: Cyan light → Purple → Orange
        elif self._phase == 1:
            gradient.setColorAt(0.0, QColor("#22d3ee"))
            gradient.setColorAt(0.5, QColor("#8b5cf6"))
            gradient.setColorAt(1.0, QColor("#f97316"))
        # Phase 2: Blue → Teal → Rose
        else:
            gradient.setColorAt(0.0, QColor("#38bdf8"))
            gradient.setColorAt(0.5, QColor("#14b8a6"))
            gradient.setColorAt(1.0, QColor("#f43f5e"))

        painter.fillRect(self.rect(), gradient)
        super().paintEvent(event)


# ============================================================================
# PILLS & BADGES
# ============================================================================

class StatPill(QLabel):
    """Small pill for displaying stats (e.g., 'Programs: 9')"""
    def __init__(self, title: str, value: str):
        super().__init__(f"{title}  {value}")
        self.setStyleSheet(
            "background: rgba(15, 23, 42, 0.5); "
            "color: #e2e8f0; "
            "border: none; "
            "border-radius: 12px; "
            "padding: 6px 10px; "
            "font-weight: 700;"
        )

    def update_value(self, value: str):
        """Update the pill's value"""
        title = self.text().split("  ")[0]
        self.setText(f"{title}  {value}")


class StatusPill(QLabel):
    """Status indicator pill"""
    def __init__(self, text: str, color: Optional[str] = None):
        super().__init__(text)
        bg_color = color or Colors.BG_SECONDARY
        self.setStyleSheet(
            f"background: {bg_color}; "
            f"color: {Colors.TEXT_SECONDARY}; "
            "border: none; "
            "border-radius: 12px; "
            "padding: 4px 10px; "
            "font-weight: 700;"
        )


class ShimmerBadge(QLabel):
    """Animated shimmer badge (e.g., 'UPDATE' indicator)"""
    def __init__(self, text: str, accent: str = Colors.ACCENT_BLUE):
        super().__init__(text)
        self._accent = accent
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(450)  # 450ms cycle
        self._tick()

    def _tick(self):
        self._phase = (self._phase + 1) % 3
        color = self._accent if self._phase == 0 else "#1f2937"
        text_color = "#f8fafc" if self._phase == 0 else "#e2e8f0"
        self.setStyleSheet(
            f"background: {color}; "
            f"color: {text_color}; "
            "border-radius: 12px; "
            "padding: 4px 10px; "
            "font-weight: 700;"
        )


# ============================================================================
# BUTTONS
# ============================================================================

def button_style(
    bg: str,
    hover: str,
    text: str = Colors.TEXT_SECONDARY,
    border: str = "none",
    radius: int = 14,
    padding: str = "8px 12px",
    weight: int = 700,
) -> str:
    """Generate QPushButton stylesheet"""
    return (
        f"QPushButton{{"
        f"background: {bg}; "
        f"color: {text}; "
        f"border: {border}; "
        f"border-radius: {radius}px; "
        f"padding: {padding}; "
        f"font-weight: {weight};"
        f"}}"
        f"\nQPushButton:hover{{background: {hover};}}"
    )


class GlowButton(QPushButton):
    """
    Modern button with glow effect on hover
    Includes drop shadow with accent color
    """
    def __init__(self, text: str, accent: str = Colors.ACCENT_BLUE, parent=None):
        super().__init__(text, parent)
        self.accent = accent
        self.setCursor(Qt.PointingHandCursor)

        # Apply base styles
        self.setStyleSheet(
            f"QPushButton {{"
            f"background: {accent}; "
            f"color: #ffffff; "
            f"border: none; "
            f"border-radius: 14px; "
            f"padding: 10px 16px; "
            f"font-weight: 700; "
            f"font-size: 14px;"
            f"}}"
            f"\nQPushButton:hover {{"
            f"background: qlineargradient("
            f"x1:0, y1:0, x2:0, y2:1, "
            f"stop:0 {accent}, "
            f"stop:1 rgba(0, 0, 0, 0.2)"
            f");"
            f"}}"
            f"\nQPushButton:pressed {{"
            f"background: rgba(0, 0, 0, 0.3);"
            f"}}"
        )

        # Add glow shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(accent))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)


class OutlineButton(QPushButton):
    """Button with outline style (transparent bg, accent border)"""
    def __init__(self, text: str, accent: str = Colors.ACCENT_BLUE, parent=None):
        super().__init__(text, parent)
        self.accent = accent
        self.setCursor(Qt.PointingHandCursor)

        self.setStyleSheet(
            f"QPushButton {{"
            f"background: transparent; "
            f"color: {accent}; "
            f"border: 2px solid {accent}; "
            f"border-radius: 14px; "
            f"padding: 8px 16px; "
            f"font-weight: 700; "
            f"font-size: 14px;"
            f"}}"
            f"\nQPushButton:hover {{"
            f"background: {accent}; "
            f"color: #ffffff;"
            f"}}"
        )


# ============================================================================
# INPUTS
# ============================================================================

class ModernInput(QLineEdit):
    """
    Modern input field with glow focus effect
    """
    def __init__(
        self,
        placeholder: str = "",
        accent: str = Colors.ACCENT_BLUE,
        password: bool = False,
        parent=None
    ):
        super().__init__(parent)
        self.accent = accent

        if placeholder:
            self.setPlaceholderText(placeholder)

        if password:
            self.setEchoMode(QLineEdit.Password)

        self.setStyleSheet(
            f"QLineEdit {{"
            f"background: rgba(15, 23, 42, 0.8); "
            f"color: {Colors.TEXT_PRIMARY}; "
            f"border: 2px solid transparent; "
            f"border-radius: 12px; "
            f"padding: 10px 14px; "
            f"font-size: 14px;"
            f"}}"
            f"\nQLineEdit:focus {{"
            f"border: 2px solid {accent};"
            f"}}"
            f"\nQLineEdit::placeholder {{"
            f"color: {Colors.TEXT_TERTIARY};"
            f"}}"
        )


class ModernTextBox(QTextEdit):
    """Modern text box with accent border on focus"""
    def __init__(self, placeholder: str = "", accent: str = Colors.ACCENT_BLUE, parent=None):
        super().__init__(parent)
        self.accent = accent

        if placeholder:
            self.setPlaceholderText(placeholder)

        self.setStyleSheet(
            f"QTextEdit {{"
            f"background: rgba(15, 23, 42, 0.8); "
            f"color: {Colors.TEXT_PRIMARY}; "
            f"border: 2px solid transparent; "
            f"border-radius: 12px; "
            f"padding: 10px; "
            f"font-size: 14px; "
            f"font-family: 'Consolas', monospace;"
            f"}}"
            f"\nQTextEdit:focus {{"
            f"border: 2px solid {accent};"
            f"}}"
        )


# ============================================================================
# CARDS & CONTAINERS
# ============================================================================

class ModernCard(QFrame):
    """
    Elevated card with subtle glow shadow
    Perfect for grouping related content
    """
    def __init__(self, accent: str = Colors.ACCENT_BLUE, parent=None):
        super().__init__(parent)
        self.accent = accent

        self.setStyleSheet(
            f"QFrame {{"
            f"background: {Colors.BG_ELEVATED}; "
            f"border: none; "
            f"border-radius: 20px;"
            f"}}"
        )

        # Add subtle shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(accent))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)


class GlassPanel(QFrame):
    """Glass-morphism style panel"""
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setStyleSheet(
            f"QFrame {{"
            f"background: {Colors.BG_GLASS}; "
            f"border: 1px solid rgba(255, 255, 255, 0.1); "
            f"border-radius: 16px;"
            f"}}"
        )


# ============================================================================
# PROGRESS BARS
# ============================================================================

class ModernProgressBar(QProgressBar):
    """Modern gradient progress bar"""
    def __init__(self, accent: str = Colors.ACCENT_BLUE, parent=None):
        super().__init__(parent)
        self.accent = accent

        self.setTextVisible(True)
        self.setAlignment(Qt.AlignCenter)

        self.setStyleSheet(
            f"QProgressBar {{"
            f"background: rgba(15, 23, 42, 0.8); "
            f"border: none; "
            f"border-radius: 8px; "
            f"text-align: center; "
            f"color: {Colors.TEXT_PRIMARY}; "
            f"font-weight: 700;"
            f"}}"
            f"\nQProgressBar::chunk {{"
            f"background: qlineargradient("
            f"x1:0, y1:0, x2:1, y2:0, "
            f"stop:0 {accent}, "
            f"stop:1 {Colors.ACCENT_PURPLE}"
            f"); "
            f"border-radius: 8px;"
            f"}}"
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_separator(color: str = Colors.TEXT_TERTIARY, height: int = 1) -> QFrame:
    """Create a horizontal separator line"""
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Plain)
    line.setStyleSheet(f"background: {color}; max-height: {height}px;")
    return line


def create_spacer(height: int = 10) -> QWidget:
    """Create vertical spacer"""
    spacer = QWidget()
    spacer.setFixedHeight(height)
    return spacer
