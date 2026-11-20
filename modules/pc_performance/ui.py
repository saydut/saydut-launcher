"""
PC Performance Module UI
Faithful port of omenhz.py - ALL features preserved
Hz control, Power plan, CPU policy (EPP/Boost/Min-Max/Core parking/Cooling),
AC/Battery auto-switching, Config persistence, System monitoring
"""
import os
import re
import json
import subprocess
import ctypes
import platform
import threading
import time
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Tuple, Dict

from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTabWidget, QComboBox, QMessageBox, QScrollArea,
    QSlider, QCheckBox,
)

import psutil

from shared import (
    Colors, GlowButton, OutlineButton,
    ModernCard, ModernProgressBar, ModernTextBox,
    create_separator, create_spacer,
)

TAB_STYLE = f"""
    QTabWidget::pane {{ border:none; background:rgba(17,24,39,0.92); border-radius:16px; }}
    QTabBar::tab {{ background:{Colors.BG_SECONDARY}; color:{Colors.TEXT_SECONDARY};
        padding:12px 24px; border:none; border-top-left-radius:12px;
        border-top-right-radius:12px; margin-right:4px; font-weight:600; }}
    QTabBar::tab:selected {{ background:rgba(17,24,39,0.92); color:{Colors.TEXT_PRIMARY}; }}
    QTabBar::tab:hover {{ background:rgba(30,41,59,0.8); }}
"""

SLIDER_STYLE = f"""
    QSlider::groove:horizontal {{ background: {Colors.BG_SECONDARY}; height: 8px; border-radius: 4px; }}
    QSlider::handle:horizontal {{ background: #ec4899; width: 18px; height: 18px;
        margin: -5px 0; border-radius: 9px; }}
    QSlider::sub-page:horizontal {{ background: #ec4899; border-radius: 4px; }}
"""

COMBO_STYLE = f"""
    QComboBox {{ background:{Colors.BG_SECONDARY}; color:{Colors.TEXT_PRIMARY};
        border:1px solid rgba(71,85,105,0.5); border-radius:10px; padding:10px 14px; font-weight:600; }}
    QComboBox:hover {{ border-color:#ec4899; }}
    QComboBox::drop-down {{ border:none; }}
    QComboBox QAbstractItemView {{ background:{Colors.BG_SECONDARY}; color:{Colors.TEXT_PRIMARY};
        selection-background-color:#ec4899; }}
"""


# ── Windows Battery Status ───────────────────────────────────────
class _PowerStatus(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_byte),
        ("BatteryFlag", ctypes.c_byte),
        ("BatteryLifePercent", ctypes.c_byte),
        ("Reserved1", ctypes.c_byte),
        ("BatteryLifeTime", ctypes.c_int),
        ("BatteryFullLifeTime", ctypes.c_int),
    ]


def is_plugged_in() -> Optional[bool]:
    try:
        s = _PowerStatus()
        ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s))
        if s.ACLineStatus == 1:
            return True
        if s.ACLineStatus == 0:
            return False
        return None
    except Exception:
        return None


def get_battery_percent() -> int:
    try:
        s = _PowerStatus()
        ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s))
        p = s.BatteryLifePercent
        return p if p <= 100 else -1
    except Exception:
        return -1


# ── Display Hz ───────────────────────────────────────────────────
def _has_win32api():
    try:
        import win32api
        return True
    except ImportError:
        return False


def get_current_hz() -> Optional[int]:
    try:
        import win32api, win32con
        dev = win32api.EnumDisplayDevices(None, 0)
        s = win32api.EnumDisplaySettings(dev.DeviceName, win32con.ENUM_CURRENT_SETTINGS)
        return int(s.DisplayFrequency)
    except Exception:
        return None


def list_supported_hz() -> List[int]:
    try:
        import win32api, win32con
        dev = win32api.EnumDisplayDevices(None, 0)
        cur = win32api.EnumDisplaySettings(dev.DeviceName, win32con.ENUM_CURRENT_SETTINGS)
        tw, th, tbpp = int(cur.PelsWidth), int(cur.PelsHeight), int(cur.BitsPerPel)
        freqs_strict, freqs_loose = set(), set()
        i = 0
        while True:
            try:
                s = win32api.EnumDisplaySettings(dev.DeviceName, i)
            except Exception:
                break
            try:
                w, h, bpp, f = int(s.PelsWidth), int(s.PelsHeight), int(s.BitsPerPel), int(s.DisplayFrequency)
                if 20 <= f <= 500 and w == tw and h == th:
                    freqs_loose.add(f)
                    if bpp == tbpp:
                        freqs_strict.add(f)
            except Exception:
                pass
            i += 1
        return sorted(freqs_strict) if freqs_strict else sorted(freqs_loose)
    except Exception:
        return []


def set_hz(hz: int) -> Tuple[bool, str]:
    try:
        import win32api, win32con
        dev = win32api.EnumDisplayDevices(None, 0)
        cur = win32api.EnumDisplaySettings(dev.DeviceName, win32con.ENUM_CURRENT_SETTINGS)
        if int(cur.DisplayFrequency) == hz:
            return True, "Zaten bu Hz'de."
        cur.DisplayFrequency = hz
        win32api.ChangeDisplaySettings(cur, 0)
        return True, "OK"
    except Exception as e:
        return False, str(e)


# ── powercfg helpers ─────────────────────────────────────────────
def _run_powercfg(args):
    try:
        p = subprocess.run(["powercfg", *args], check=False, capture_output=True, text=True, creationflags=0x08000000)
        return p.returncode, ((p.stdout or "") + "\n" + (p.stderr or "")).strip()
    except Exception as e:
        return 1, str(e)


def list_power_schemes():
    rc, txt = _run_powercfg(["/list"])
    if rc != 0:
        return []
    schemes = []
    for line in txt.splitlines():
        m = re.search(r'([0-9a-fA-F\-]{36})\s*\((.+?)\)\s*(\*)?', line, re.IGNORECASE)
        if m:
            schemes.append((m.group(1).strip(), m.group(2).strip(), bool(m.group(3))))
    return schemes


def get_active_scheme():
    for guid, name, active in list_power_schemes():
        if active:
            return guid, name
    return None, None


def set_power_scheme(guid):
    _run_powercfg(["/setactive", guid])


def restore_default_schemes():
    _run_powercfg(["-restoredefaultschemes"])


def duplicate_scheme(base_guid):
    rc, out = _run_powercfg(["-duplicatescheme", base_guid])
    if rc != 0:
        return None
    m = re.search(r'([0-9a-fA-F\-]{36})', out)
    return m.group(1) if m else None


def change_scheme_name(guid, name, desc=""):
    _run_powercfg(["-changename", guid, name, desc])


# ── CPU Policy ───────────────────────────────────────────────────
SUB_PROCESSOR = "54533251-82be-4824-96c1-47b60b740d00"
PERFEPP = "36687f9e-e3a5-4dbf-b1dc-15eb381c6863"
PERFBOOSTMODE = "be337238-0d82-4146-a960-4f3749d470c7"
PROCTHROTTLEMIN = "893dee8e-2bef-41e0-89c6-b55d0929964c"
PROCTHROTTLEMAX = "bc5038f7-23e0-4960-96da-33abaf5935ec"
CPMINCORES = "0cc5b647-c1df-4637-891a-dec35c318583"
SYSTEMCOOLINGPOLICY = "94d3a615-a899-4ac5-ae2b-e4d8f634367f"

BOOST_LABELS = {0: "Disabled (Tasarruf)", 1: "Enabled", 2: "Aggressive (Performans)"}
COOLING_LABELS = {1: "Active (Fan ile)", 0: "Passive (Kısarak)"}


def apply_cpu_policy(scheme, plugged, epp, boost, cpu_min, cpu_max, core_park, cooling):
    if not scheme:
        return
    ac = bool(plugged)
    cmd = "/setacvalueindex" if ac else "/setdcvalueindex"
    for setting, val in [(PERFEPP, max(0, min(100, epp))), (PERFBOOSTMODE, max(0, min(2, boost))),
                         (PROCTHROTTLEMIN, max(0, min(100, cpu_min))), (PROCTHROTTLEMAX, max(1, min(100, cpu_max))),
                         (CPMINCORES, max(0, min(100, core_park))), (SYSTEMCOOLINGPOLICY, 1 if cooling == 1 else 0)]:
        _run_powercfg([cmd, scheme, SUB_PROCESSOR, setting, str(int(val))])
    _run_powercfg(["/setactive", scheme])


# ── Config ───────────────────────────────────────────────────────
@dataclass
class CpuPolicy:
    epp: int = 0
    boost_mode: int = 1
    cpu_min: int = 5
    cpu_max: int = 100
    core_parking_min: int = 100
    cooling_policy: int = 1


@dataclass
class AppConfig:
    auto_mode: bool = True
    set_power_plan: bool = True
    set_cpu_policy: bool = True
    ac_hz: Optional[int] = None
    battery_hz: Optional[int] = None
    ac_plan_guid: Optional[str] = None
    battery_plan_guid: Optional[str] = None
    cpu_ac: CpuPolicy = field(default_factory=lambda: CpuPolicy(epp=0, boost_mode=2, cpu_min=5, cpu_max=100, core_parking_min=100, cooling_policy=1))
    cpu_bat: CpuPolicy = field(default_factory=lambda: CpuPolicy(epp=90, boost_mode=0, cpu_min=5, cpu_max=70, core_parking_min=20, cooling_policy=0))


CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "OmenHzController")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


def _dict_to_policy(d, fb):
    try:
        return CpuPolicy(**{k: int(d.get(k, getattr(fb, k))) for k in ('epp', 'boost_mode', 'cpu_min', 'cpu_max', 'core_parking_min', 'cooling_policy')})
    except Exception:
        return fb


def load_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_PATH):
        return AppConfig()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        cfg = AppConfig(
            auto_mode=bool(raw.get("auto_mode", True)), set_power_plan=bool(raw.get("set_power_plan", True)),
            set_cpu_policy=bool(raw.get("set_cpu_policy", True)),
            ac_hz=raw.get("ac_hz"), battery_hz=raw.get("battery_hz"),
            ac_plan_guid=raw.get("ac_plan_guid"), battery_plan_guid=raw.get("battery_plan_guid"))
        cfg.cpu_ac = _dict_to_policy(raw.get("cpu_ac") or {}, cfg.cpu_ac)
        cfg.cpu_bat = _dict_to_policy(raw.get("cpu_bat") or {}, cfg.cpu_bat)
        return cfg
    except Exception:
        return AppConfig()


def save_config(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(asdict(cfg), f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════
# MAIN WIDGET
# ══════════════════════════════════════════════════════════════════
class PCPerformanceWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cfg = load_config()
        self._last_plug = None
        self._hz_ok = _has_win32api()

        self.supported_hz = list_supported_hz() if self._hz_ok else []
        if not self.supported_hz:
            self.supported_hz = [60, 75, 120, 144, 165, 240]

        if self.cfg.ac_hz is None:
            cur = get_current_hz() if self._hz_ok else None
            self.cfg.ac_hz = cur or self.supported_hz[-1]
        if self.cfg.battery_hz is None:
            self.cfg.battery_hz = self.supported_hz[0]

        self.schemes = []
        self.scheme_display = []
        self.disp2guid = {}
        self.guid2disp = {}
        self._load_schemes(initial=True)
        save_config(self.cfg)

        self._setup_ui()
        self._start_timers()

    # ── UI Setup ──────────────────────────────────────────────────
    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        # Header
        hdr = ModernCard()
        hl = QVBoxLayout(hdr)
        hl.setContentsMargins(20, 16, 20, 16)
        t = QLabel("⚡ Ekran + Güç Kontrol Merkezi")
        t.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:24px;font-weight:800;background:transparent;")
        hl.addWidget(t)
        self.status_lbl = QLabel(self._status_text())
        self.status_lbl.setStyleSheet(f"color:#00ffcc;font-size:12px;font-weight:600;background:transparent;")
        hl.addWidget(self.status_lbl)
        self.live_lbl = QLabel("CPU: -")
        self.live_lbl.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:11px;background:transparent;")
        hl.addWidget(self.live_lbl)
        lay.addWidget(hdr)

        tabs = QTabWidget()
        tabs.setStyleSheet(TAB_STYLE)
        tabs.addTab(self._tab_monitor(), "Sistem İzle")
        tabs.addTab(self._tab_hz(), "Hz Kontrol")
        tabs.addTab(self._tab_power(), "Güç Planları")
        tabs.addTab(self._tab_cpu(), "CPU Policy")
        tabs.addTab(self._tab_info(), "Bilgi")
        lay.addWidget(tabs, 1)

    def _status_text(self):
        cur = get_current_hz() if self._hz_ok else None
        plug = is_plugged_in()
        _, plan = get_active_scheme()
        return (f"Şu anki: {cur or '?'}Hz  •  "
                f"Durum: {'Prizde' if plug is True else ('Bataryada' if plug is False else '?')}  •  "
                f"Aktif Plan: {plan or '?'}")

    # ── Monitor Tab ───────────────────────────────────────────────
    def _tab_monitor(self):
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.setContentsMargins(20, 20, 20, 20)
        ly.setSpacing(16)

        bc = ModernCard()
        bl = QHBoxLayout(bc)
        bl.setContentsMargins(16, 12, 16, 12)
        self.lbl_bat = QLabel("🔋 Pil: --")
        self.lbl_bat.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:16px;font-weight:700;background:transparent;")
        bl.addWidget(self.lbl_bat)
        self.lbl_ac = QLabel("⚡ --")
        self.lbl_ac.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:14px;background:transparent;")
        bl.addWidget(self.lbl_ac)
        bl.addStretch()
        ly.addWidget(bc)

        def mkbar(txt):
            c = ModernCard()
            cl = QVBoxLayout(c)
            cl.setContentsMargins(16, 12, 16, 12)
            cl.setSpacing(8)
            l = QLabel(txt)
            l.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:14px;font-weight:600;background:transparent;")
            cl.addWidget(l)
            b = ModernProgressBar()
            b.setFixedHeight(14)
            cl.addWidget(b)
            return c, l, b

        c1, self.lbl_cpu, self.bar_cpu = mkbar("CPU: %0")
        ly.addWidget(c1)
        c2, self.lbl_ram, self.bar_ram = mkbar("RAM: %0")
        ly.addWidget(c2)
        c3, self.lbl_disk, self.bar_disk = mkbar("Disk: %0")
        ly.addWidget(c3)

        n = psutil.cpu_count()
        self.pcpu = []
        if n and n <= 32:
            pc = ModernCard()
            pcl = QVBoxLayout(pc)
            pcl.setContentsMargins(16, 12, 16, 12)
            pcl.setSpacing(4)
            pcl.addWidget(QLabel("Çekirdek Kullanımı"))
            for i in range(n):
                r = QHBoxLayout()
                l = QLabel(f"C{i}: 0%")
                l.setFixedWidth(80)
                l.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:11px;background:transparent;")
                r.addWidget(l)
                b = ModernProgressBar()
                b.setFixedHeight(8)
                r.addWidget(b)
                pcl.addLayout(r)
                self.pcpu.append((l, b))
            ly.addWidget(pc)

        ly.addStretch()
        return w

    # ── Hz Tab ────────────────────────────────────────────────────
    def _tab_hz(self):
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.setContentsMargins(20, 20, 20, 20)
        ly.setSpacing(16)

        if not self._hz_ok:
            ly.addWidget(QLabel("⚠️ win32api modülü bulunamadı.\npip install pywin32\n\nHz kontrol devre dışı."))
            ly.addStretch()
            return w

        # Toggles
        tc = ModernCard()
        tl = QVBoxLayout(tc)
        tl.setContentsMargins(16, 14, 16, 14)
        tl.setSpacing(8)

        self.sw_auto = QCheckBox("Otomatik Geçiş (Priz/Batarya)")
        self.sw_auto.setStyleSheet(f"QCheckBox{{color:{Colors.TEXT_PRIMARY};font-weight:600;background:transparent;}}")
        self.sw_auto.setChecked(self.cfg.auto_mode)
        self.sw_auto.stateChanged.connect(self._on_toggle)
        tl.addWidget(self.sw_auto)

        self.sw_plan = QCheckBox("Power Plan Değiştir")
        self.sw_plan.setStyleSheet(f"QCheckBox{{color:{Colors.TEXT_PRIMARY};font-weight:600;background:transparent;}}")
        self.sw_plan.setChecked(self.cfg.set_power_plan)
        self.sw_plan.stateChanged.connect(self._on_toggle)
        tl.addWidget(self.sw_plan)

        self.sw_cpupol = QCheckBox("CPU Policy Uygula (EPP/Boost/%)")
        self.sw_cpupol.setStyleSheet(f"QCheckBox{{color:{Colors.TEXT_PRIMARY};font-weight:600;background:transparent;}}")
        self.sw_cpupol.setChecked(self.cfg.set_cpu_policy)
        self.sw_cpupol.stateChanged.connect(self._on_toggle)
        tl.addWidget(self.sw_cpupol)
        ly.addWidget(tc)

        # Hz combos
        hc = ModernCard()
        hl = QVBoxLayout(hc)
        hl.setContentsMargins(16, 14, 16, 14)
        hl.setSpacing(8)

        hl.addWidget(self._lbl("Prizde (AC) Hz:"))
        self.ac_hz = QComboBox()
        self.ac_hz.setStyleSheet(COMBO_STYLE)
        for hz in self.supported_hz:
            self.ac_hz.addItem(str(hz), hz)
        if self.cfg.ac_hz in self.supported_hz:
            self.ac_hz.setCurrentIndex(self.supported_hz.index(self.cfg.ac_hz))
        self.ac_hz.currentIndexChanged.connect(lambda: self._save_hz("ac"))
        hl.addWidget(self.ac_hz)

        hl.addWidget(self._lbl("Bataryada Hz:"))
        self.bat_hz = QComboBox()
        self.bat_hz.setStyleSheet(COMBO_STYLE)
        for hz in self.supported_hz:
            self.bat_hz.addItem(str(hz), hz)
        if self.cfg.battery_hz in self.supported_hz:
            self.bat_hz.setCurrentIndex(self.supported_hz.index(self.cfg.battery_hz))
        self.bat_hz.currentIndexChanged.connect(lambda: self._save_hz("bat"))
        hl.addWidget(self.bat_hz)
        ly.addWidget(hc)

        # Apply buttons
        bc = ModernCard()
        bcl = QVBoxLayout(bc)
        bcl.setContentsMargins(16, 14, 16, 14)
        bcl.setSpacing(8)

        b1 = GlowButton("⚡ Şimdi Uygula (Mevcut Duruma Göre)", accent="#ec4899")
        b1.setFixedHeight(44)
        b1.clicked.connect(self._apply_current)
        bcl.addWidget(b1)

        b2 = OutlineButton("Manuel: AC Ayarlarını Uygula")
        b2.clicked.connect(lambda: self._apply_targets(True))
        bcl.addWidget(b2)

        b3 = OutlineButton("Manuel: Battery Ayarlarını Uygula")
        b3.clicked.connect(lambda: self._apply_targets(False))
        bcl.addWidget(b3)
        ly.addWidget(bc)

        ly.addWidget(QLabel(f"Ayarlar: {CONFIG_PATH}").setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:10px;") or QLabel(f"Ayarlar: {CONFIG_PATH}"))
        ly.addStretch()
        return w

    # ── Power Tab ─────────────────────────────────────────────────
    def _tab_power(self):
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.setContentsMargins(20, 20, 20, 20)
        ly.setSpacing(16)

        top = QHBoxLayout()
        top.addWidget(self._lbl("Power Plan"))
        top.addStretch()
        br = OutlineButton("Planları Yenile")
        br.clicked.connect(self._ui_refresh)
        top.addWidget(br)
        ly.addLayout(top)

        ly.addWidget(self._lbl("Prizde (AC) Power Plan:"))
        self.ac_plan = QComboBox()
        self.ac_plan.setStyleSheet(COMBO_STYLE)
        self.ac_plan.currentIndexChanged.connect(lambda: self._save_plan("ac"))
        ly.addWidget(self.ac_plan)

        ly.addWidget(self._lbl("Bataryada Power Plan:"))
        self.bat_plan = QComboBox()
        self.bat_plan.setStyleSheet(COMBO_STYLE)
        self.bat_plan.currentIndexChanged.connect(lambda: self._save_plan("bat"))
        ly.addWidget(self.bat_plan)

        self._sync_combos()

        self.plan_stat = QLabel("")
        self.plan_stat.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:12px;background:transparent;")
        ly.addWidget(self.plan_stat)

        ly.addWidget(create_separator())

        br2 = QHBoxLayout()
        b_rst = OutlineButton("Standart Planları Geri Yükle")
        b_rst.clicked.connect(lambda: (restore_default_schemes(), self._ui_refresh()))
        br2.addWidget(b_rst)
        b_mk = OutlineButton("Balanced'tan 2 Plan Üret")
        b_mk.clicked.connect(self._make_two)
        br2.addWidget(b_mk)
        ly.addLayout(br2)

        ly.addWidget(create_separator())
        ly.addWidget(self._lbl("Hızlı Ayarlar"))

        for name, guid in [("🔋 Güç Tasarrufu", "a1841308-3541-4fab-bc81-f71556f20b4a"),
                           ("⚖️ Dengeli", "381b4222-f694-41f0-9685-ff5bb260df2e"),
                           ("🚀 Yüksek Performans", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"),
                           ("⚡ Ultimate Performance", "e9a42b02-d5df-448d-aa00-03f14749eb61")]:
            b = OutlineButton(name)
            b.clicked.connect(lambda _c=False, g=guid: (set_power_scheme(g), self._ui_refresh(), self.plan_stat.setText("✅ Hızlı ayar uygulandı!")))
            ly.addWidget(b)

        ly.addStretch()
        return w

    # ── CPU Policy Tab ────────────────────────────────────────────
    def _tab_cpu(self):
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.setContentsMargins(20, 20, 20, 20)
        ly.setSpacing(8)

        ly.addWidget(self._lbl("CPU Policy (Gerçek Tasarruf/Performans)"))
        ct = QTabWidget()
        ct.setStyleSheet(TAB_STYLE)
        ct.addTab(self._cpu_panel("ac"), "AC (Priz)")
        ct.addTab(self._cpu_panel("bat"), "Battery (Pil)")
        ly.addWidget(ct, 1)
        return w

    def _cpu_panel(self, mode):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        cw = QWidget()
        cw.setStyleSheet("background:transparent;")
        ly = QVBoxLayout(cw)
        ly.setContentsMargins(12, 12, 12, 12)
        ly.setSpacing(12)

        pol = self.cfg.cpu_ac if mode == "ac" else self.cfg.cpu_bat

        # EPP
        ly.addWidget(self._lbl("EPP (0=Performans, 100=Tasarruf)"))
        epp_l, epp_s = self._mkslider(0, 100, pol.epp)
        ly.addWidget(epp_l)
        ly.addWidget(epp_s)
        epp_s.valueChanged.connect(lambda v: (epp_l.setText(str(v)), self._cpu_set(mode, "epp", v)))

        # Boost
        ly.addWidget(self._lbl("Boost Mode"))
        bc = QComboBox()
        bc.setStyleSheet(COMBO_STYLE)
        for k, v in BOOST_LABELS.items():
            bc.addItem(v, k)
        bc.setCurrentIndex(int(pol.boost_mode))
        bc.currentIndexChanged.connect(lambda: self._cpu_set(mode, "boost_mode", bc.currentData()))
        ly.addWidget(bc)

        # Max CPU
        ly.addWidget(self._lbl("CPU Max (%)"))
        mx_l, mx_s = self._mkslider(1, 100, pol.cpu_max)
        ly.addWidget(mx_l)
        ly.addWidget(mx_s)
        mx_s.valueChanged.connect(lambda v: (mx_l.setText(str(v)), self._cpu_set(mode, "cpu_max", v)))

        # Min CPU
        ly.addWidget(self._lbl("CPU Min (%)"))
        mn_l, mn_s = self._mkslider(0, 100, pol.cpu_min)
        ly.addWidget(mn_l)
        ly.addWidget(mn_s)
        mn_s.valueChanged.connect(lambda v: (mn_l.setText(str(v)), self._cpu_set(mode, "cpu_min", v)))

        # Core parking
        ly.addWidget(self._lbl("Core Parking Min Cores (%)"))
        pk_l, pk_s = self._mkslider(0, 100, pol.core_parking_min)
        ly.addWidget(pk_l)
        ly.addWidget(pk_s)
        pk_s.valueChanged.connect(lambda v: (pk_l.setText(str(v)), self._cpu_set(mode, "core_parking_min", v)))

        # Cooling
        ly.addWidget(self._lbl("Cooling Policy"))
        cc = QComboBox()
        cc.setStyleSheet(COMBO_STYLE)
        cc.addItem(COOLING_LABELS[1], 1)
        cc.addItem(COOLING_LABELS[0], 0)
        cc.setCurrentIndex(0 if pol.cooling_policy == 1 else 1)
        cc.currentIndexChanged.connect(lambda: self._cpu_set(mode, "cooling_policy", cc.currentData()))
        ly.addWidget(cc)

        btn = GlowButton("Bu Sekmenin CPU Policy'sini Seçili Planına Yaz", accent="#ec4899")
        btn.clicked.connect(lambda: self._write_cpu(mode))
        ly.addWidget(btn)

        ly.addStretch()
        scroll.setWidget(cw)
        return scroll

    # ── Info Tab ──────────────────────────────────────────────────
    def _tab_info(self):
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.setContentsMargins(16, 16, 16, 16)

        lines = ["── SİSTEM BİLGİSİ ──",
                  f"OS: {platform.system()} {platform.release()} ({platform.version()})",
                  f"İşlemci: {platform.processor()}",
                  f"Çekirdek: {psutil.cpu_count(logical=False)} Fiziksel / {psutil.cpu_count()} Mantıksal",
                  f"RAM: {psutil.virtual_memory().total/(1024**3):.1f} GB"]
        try:
            f = psutil.cpu_freq()
            if f:
                lines.append(f"CPU Frekans: {f.current:.0f} MHz (max: {f.max:.0f} MHz)")
        except Exception:
            pass
        if self._hz_ok:
            lines.append(f"Ekran Hz: {get_current_hz() or '?'} Hz")
            lines.append(f"Desteklenen Hz: {self.supported_hz}")
        lines += ["", "── DİSKLER ──"]
        for p in psutil.disk_partitions():
            try:
                u = psutil.disk_usage(p.mountpoint)
                lines.append(f"{p.device}: {u.total/(1024**3):.1f} GB, %{u.percent} kullanım")
            except Exception:
                pass

        box = ModernTextBox()
        box.setReadOnly(True)
        box.setText("\n".join(lines))
        ly.addWidget(box, 1)
        return w

    # ── Helpers ───────────────────────────────────────────────────
    def _lbl(self, t):
        l = QLabel(t)
        l.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-weight:600;background:transparent;")
        return l

    def _mkslider(self, lo, hi, val):
        l = QLabel(str(val))
        l.setStyleSheet(f"color:#ec4899;font-weight:700;background:transparent;")
        l.setAlignment(Qt.AlignRight)
        s = QSlider(Qt.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        s.setStyleSheet(SLIDER_STYLE)
        return l, s

    # ── Timers ────────────────────────────────────────────────────
    def _start_timers(self):
        self._t = QTimer(self)
        self._t.timeout.connect(self._tick)
        self._t.start(2000)
        self._tick()
        threading.Thread(target=self._monitor, daemon=True).start()

    def _tick(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            self.lbl_cpu.setText(f"CPU: %{cpu:.0f}")
            self.bar_cpu.setValue(int(cpu))
            ram = psutil.virtual_memory().percent
            self.lbl_ram.setText(f"RAM: %{ram:.0f}")
            self.bar_ram.setValue(int(ram))
            disk = psutil.disk_usage("C:\\").percent
            self.lbl_disk.setText(f"Disk: %{disk:.0f}")
            self.bar_disk.setValue(int(disk))

            pct = get_battery_percent()
            self.lbl_bat.setText(f"🔋 Pil: %{pct}" if pct >= 0 else "🔋 Pil: Masaüstü")
            plug = is_plugged_in()
            self.lbl_ac.setText("⚡ Prize Takılı" if plug is True else ("🔋 Pilde" if plug is False else ""))

            pc = psutil.cpu_percent(percpu=True)
            for i, (l, b) in enumerate(self.pcpu):
                if i < len(pc):
                    l.setText(f"C{i}: {pc[i]:.0f}%")
                    b.setValue(int(pc[i]))

            f = psutil.cpu_freq()
            ghz = f"{f.current/1000:.2f} GHz" if f and f.current else "?"
            self.live_lbl.setText(f"CPU: {cpu:.0f}%  •  Frekans: {ghz}")
            self.status_lbl.setText(self._status_text())
        except Exception:
            pass

    def _monitor(self):
        while True:
            try:
                plug = is_plugged_in()
                if self.cfg.auto_mode and plug is not None and plug != self._last_plug:
                    self._last_plug = plug
                    self._apply_targets(plug)
            except Exception:
                pass
            time.sleep(3)

    # ── Actions ───────────────────────────────────────────────────
    def _on_toggle(self):
        if hasattr(self, 'sw_auto'):
            self.cfg.auto_mode = self.sw_auto.isChecked()
            self.cfg.set_power_plan = self.sw_plan.isChecked()
            self.cfg.set_cpu_policy = self.sw_cpupol.isChecked()
            save_config(self.cfg)

    def _save_hz(self, mode):
        if mode == "ac":
            self.cfg.ac_hz = self.ac_hz.currentData()
        else:
            self.cfg.battery_hz = self.bat_hz.currentData()
        save_config(self.cfg)

    def _save_plan(self, mode):
        if mode == "ac":
            self.cfg.ac_plan_guid = self.disp2guid.get(self.ac_plan.currentText())
        else:
            self.cfg.battery_plan_guid = self.disp2guid.get(self.bat_plan.currentText())
        save_config(self.cfg)

    def _cpu_set(self, mode, field, val):
        pol = self.cfg.cpu_ac if mode == "ac" else self.cfg.cpu_bat
        setattr(pol, field, int(val))
        if pol.cpu_min > pol.cpu_max:
            pol.cpu_min = pol.cpu_max
        save_config(self.cfg)

    def _apply_current(self):
        plug = is_plugged_in()
        if plug is not None:
            self._apply_targets(plug)

    def _apply_targets(self, plugged):
        hz = self.cfg.ac_hz if plugged else self.cfg.battery_hz
        plan = self.cfg.ac_plan_guid if plugged else self.cfg.battery_plan_guid
        pol = self.cfg.cpu_ac if plugged else self.cfg.cpu_bat
        if self.cfg.set_power_plan and plan:
            set_power_scheme(plan)
        if self.cfg.set_cpu_policy and plan:
            apply_cpu_policy(plan, plugged, pol.epp, pol.boost_mode, pol.cpu_min, pol.cpu_max, pol.core_parking_min, pol.cooling_policy)
        if self._hz_ok and hz:
            set_hz(int(hz))

    def _write_cpu(self, mode):
        plan = self.cfg.ac_plan_guid if mode == "ac" else self.cfg.battery_plan_guid
        pol = self.cfg.cpu_ac if mode == "ac" else self.cfg.cpu_bat
        if not plan:
            QMessageBox.warning(self, "Uyarı", "Önce bir power plan seçin.")
            return
        apply_cpu_policy(plan, mode == "ac", pol.epp, pol.boost_mode, pol.cpu_min, pol.cpu_max, pol.core_parking_min, pol.cooling_policy)

    # ── Plan helpers ──────────────────────────────────────────────
    def _load_schemes(self, initial=False):
        self.schemes = list_power_schemes()
        self.scheme_display = []
        self.disp2guid = {}
        self.guid2disp = {}
        for guid, name, _ in self.schemes:
            d = f"{name} — {guid}"
            self.scheme_display.append(d)
            self.disp2guid[d] = guid
            self.guid2disp[guid.lower()] = d
        if not self.scheme_display:
            self.scheme_display = ["(Okunamadı)"]
        if initial:
            ag, _ = get_active_scheme()
            if not self.cfg.ac_plan_guid:
                self.cfg.ac_plan_guid = ag
            if not self.cfg.battery_plan_guid:
                self.cfg.battery_plan_guid = ag

    def _sync_combos(self):
        self.ac_plan.blockSignals(True)
        self.bat_plan.blockSignals(True)
        self.ac_plan.clear()
        self.bat_plan.clear()
        for d in self.scheme_display:
            self.ac_plan.addItem(d)
            self.bat_plan.addItem(d)
        if self.cfg.ac_plan_guid:
            d = self.guid2disp.get(self.cfg.ac_plan_guid.lower())
            if d:
                i = self.ac_plan.findText(d)
                if i >= 0:
                    self.ac_plan.setCurrentIndex(i)
        if self.cfg.battery_plan_guid:
            d = self.guid2disp.get(self.cfg.battery_plan_guid.lower())
            if d:
                i = self.bat_plan.findText(d)
                if i >= 0:
                    self.bat_plan.setCurrentIndex(i)
        self.ac_plan.blockSignals(False)
        self.bat_plan.blockSignals(False)

    def _ui_refresh(self):
        self._load_schemes()
        self._sync_combos()

    def _make_two(self):
        base = None
        for g, n, _ in list_power_schemes():
            if "balanced" in n.lower() or "dengeli" in n.lower():
                base = g
                break
        if not base and self.schemes:
            base = self.schemes[0][0]
        if not base:
            return
        n1 = duplicate_scheme(base)
        if n1:
            change_scheme_name(n1, "KEMAL - High Performance", "AC için")
        n2 = duplicate_scheme(base)
        if n2:
            change_scheme_name(n2, "KEMAL - Power Saver", "Battery için")
        self._ui_refresh()
        self.plan_stat.setText("2 yeni plan oluşturuldu.")
