import ctypes
import sys
import time
from typing import Dict
from pynput.keyboard import Controller as PynputController, Key
from src.core.models import LanguageMode
from src.os_driver.win32_window import Win32WindowManager

if sys.platform == "win32":
    user32 = ctypes.windll.user32

    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004
    KEYEVENTF_SCANCODE = 0x0008

    VK_SHIFT = 0x10
    VK_BACK = 0x08
    VK_TAB = 0x09
    VK_RETURN = 0x0D
    VK_SPACE = 0x20
    VK_HANGUL = 0x15

    MAPVK_VK_TO_VSC = 0

    ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort),
            ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long),
            ("dy", ctypes.c_long),
            ("mouseData", ctypes.c_ulong),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [
            ("uMsg", ctypes.c_ulong),
            ("wParamL", ctypes.c_ushort),
            ("wParamH", ctypes.c_ushort),
        ]

    class _INPUT_UNION(ctypes.Union):
        _fields_ = [
            ("ki", KEYBDINPUT),
            ("mi", MOUSEINPUT),
            ("hi", HARDWAREINPUT),
        ]

    class INPUT(ctypes.Structure):
        _fields_ = [
            ("type", ctypes.c_ulong),
            ("union", _INPUT_UNION),
        ]

    # 물리적 QWERTY 키 문자 -> Windows Virtual Key (VK) 코드 매핑
    CHAR_TO_VK: Dict[str, int] = {
        'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45,
        'f': 0x46, 'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A,
        'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E, 'o': 0x4F,
        'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54,
        'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59,
        'z': 0x5A,
        '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
        '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
        ' ': VK_SPACE,
        '\n': VK_RETURN,
        '\t': VK_TAB,
        '`': 0xC0, '-': 0xBD, '=': 0xBB, '[': 0xDB, ']': 0xDD,
        '\\': 0xDC, ';': 0xBA, "'": 0xDE, ',': 0xBC, '.': 0xBE,
        '/': 0xBF,
    }


class KeyboardDriver:
    """
    Windows 11 네이티브 SendInput 및 macOS pynput을 지원하는 하드웨어 수준 키보드 드라이버.
    - 실제 키보드의 스캔코드(ScanCode)와 Virtual Key(VK)를 함께 전송하여
      Windows 11 메모장(Notepad) 등 모든 애플리케이션의 한글 IME가 자소를 완벽하게 조합하도록 합니다.
    """

    def __init__(self) -> None:
        self._pynput = PynputController()
        self.current_lang = LanguageMode.EN

    def _win32_send_vk(self, vk: int, key_up: bool = False) -> None:
        scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
        flags = KEYEVENTF_KEYUP if key_up else 0
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.union.ki = KEYBDINPUT(
            wVk=vk,
            wScan=scan,
            dwFlags=flags,
            time=0,
            dwExtraInfo=0,
        )
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def _win32_send_unicode_char(self, ch: str) -> None:
        """이모지나 특수 유니코드 문자 입력용 폴백"""
        for code_unit in ch.encode("utf-16-le"):
            pass
        utf16_bytes = ch.encode("utf-16-le")
        count = len(utf16_bytes) // 2
        for idx in range(count):
            wscan = int.from_bytes(utf16_bytes[idx * 2 : idx * 2 + 2], "little")
            for flags in (KEYEVENTF_UNICODE, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP):
                inp = INPUT()
                inp.type = INPUT_KEYBOARD
                inp.union.ki = KEYBDINPUT(wVk=0, wScan=wscan, dwFlags=flags, time=0, dwExtraInfo=0)
                user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def sync_or_ensure_language(self, target_lang: LanguageMode, hold_duration: float = 0.035) -> bool:
        """
        대상 창이 요구하는 언어 상태(KO 또는 EN)와 현재 IME 상태가 다르면
        실제 한/영 키(VK_HANGUL)를 눌러 전환합니다.
        반환값: 실제로 한/영 전환 키를 눌렀는지 여부
        """
        if target_lang not in (LanguageMode.KO, LanguageMode.EN):
            return False

        if sys.platform == "win32":
            detected = Win32WindowManager.get_current_ime_language()
            if detected is not None:
                self.current_lang = detected

            if self.current_lang != target_lang:
                self.press_hangul_toggle(hold_duration=hold_duration)
                self.current_lang = target_lang
                time.sleep(0.05)
                return True
            return False
        else:
            if self.current_lang != target_lang:
                self.press_hangul_toggle(hold_duration=hold_duration)
                self.current_lang = target_lang
                time.sleep(0.05)
                return True
            return False

    def press_hangul_toggle(self, hold_duration: float = 0.035) -> None:
        """한/영 전환 키(VK_HANGUL) 1회 타건"""
        if sys.platform == "win32":
            self._win32_send_vk(VK_HANGUL, key_up=False)
            time.sleep(hold_duration)
            self._win32_send_vk(VK_HANGUL, key_up=True)
        else:
            # macOS 기본 한/영 전환 (Ctrl + Space 또는 Caps Lock)
            with self._pynput.pressed(Key.ctrl):
                self._pynput.press(Key.space)
                time.sleep(hold_duration)
                self._pynput.release(Key.space)

    def press_backspace(self, hold_duration: float = 0.035) -> None:
        """Backspace 키 1회 타건 (오타 수정용)"""
        if sys.platform == "win32":
            self._win32_send_vk(VK_BACK, key_up=False)
            time.sleep(hold_duration)
            self._win32_send_vk(VK_BACK, key_up=True)
        else:
            self._pynput.press(Key.backspace)
            time.sleep(hold_duration)
            self._pynput.release(Key.backspace)

    def press_key(self, key: str, shift: bool = False, hold_duration: float = 0.035) -> None:
        """단일 물리 키(자소 또는 영문/기호)를 실제 사람처럼 누르고 뗌"""
        if sys.platform == "win32":
            vk = CHAR_TO_VK.get(key)
            if vk is None:
                # 매핑 테이블에 없는 특수 유니코드 문자
                self._win32_send_unicode_char(key)
                return

            if shift:
                self._win32_send_vk(VK_SHIFT, key_up=False)
                time.sleep(0.012)

            self._win32_send_vk(vk, key_up=False)
            time.sleep(hold_duration)
            self._win32_send_vk(vk, key_up=True)

            if shift:
                time.sleep(0.012)
                self._win32_send_vk(VK_SHIFT, key_up=True)
        else:
            # macOS / 타 플랫폼 폴백
            target = Key.enter if key == '\n' else (Key.tab if key == '\t' else (Key.space if key == ' ' else key))
            if shift:
                with self._pynput.pressed(Key.shift):
                    self._pynput.press(target)
                    time.sleep(hold_duration)
                    self._pynput.release(target)
            else:
                self._pynput.press(target)
                time.sleep(hold_duration)
                self._pynput.release(target)
