import ctypes
from ctypes import wintypes
import sys
import time
from typing import List, Optional, Tuple
from src.core.models import LanguageMode


class WindowInfo:
    """열려 있는 윈도우 창 정보"""
    def __init__(self, hwnd: int, title: str, class_name: str):
        self.hwnd = hwnd
        self.title = title
        self.class_name = class_name

    def __repr__(self) -> str:
        return f"{self.title} ({self.class_name})"


if sys.platform == "win32":
    user32 = ctypes.windll.user32
    imm32 = ctypes.windll.imm32
    kernel32 = ctypes.windll.kernel32

    # 64비트 Windows 환경 호환용 타입 정의
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.EnumChildWindows.argtypes = [wintypes.HWND, WNDENUMPROC, wintypes.LPARAM]
    user32.EnumChildWindows.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.BringWindowToTop.restype = wintypes.BOOL
    user32.SetFocus.argtypes = [wintypes.HWND]
    user32.SetFocus.restype = wintypes.HWND
    user32.SetActiveWindow.argtypes = [wintypes.HWND]
    user32.SetActiveWindow.restype = wintypes.HWND
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    user32.AttachThreadInput.restype = wintypes.BOOL

    SW_RESTORE = 9
    SW_SHOW = 5
    WM_IME_CONTROL = 0x0283
    IMC_GETCONVERSIONMODE = 0x0001
    IMC_SETCONVERSIONMODE = 0x0002
    IME_CMODE_NATIVE = 0x0001  # 한글 모드 비트

    VK_MENU = 0x12  # Alt 키
    KEYEVENTF_KEYUP = 0x0002

    class GUITHREADINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("flags", wintypes.DWORD),
            ("hwndActive", wintypes.HWND),
            ("hwndFocus", wintypes.HWND),
            ("hwndCapture", wintypes.HWND),
            ("hwndMenuOwner", wintypes.HWND),
            ("hwndMoveSize", wintypes.HWND),
            ("hwndCaret", wintypes.HWND),
            ("rcCaret", wintypes.RECT),
        ]


class Win32WindowManager:
    """Windows 열려 있는 창 목록 조회, 창 포커스 활성화, IME 한/영 상태 감지 및 제어"""

    @staticmethod
    def list_open_windows(exclude_title_substring: str = "Auto-Typer") -> List[WindowInfo]:
        """화면에 보이는 캡션이 있는 모든 창 목록 반환 (메모장 등을 상단에 우선 정렬)"""
        if sys.platform != "win32":
            return []

        windows: List[WindowInfo] = []

        def enum_handler(hwnd: int, lparam: int) -> bool:
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.strip()

                    class_buff = ctypes.create_unicode_buffer(256)
                    user32.GetClassNameW(hwnd, class_buff, 256)
                    class_name = class_buff.value.strip()

                    # Program Manager나 자기 자신 창 제외
                    if title and title != "Program Manager" and exclude_title_substring not in title:
                        windows.append(WindowInfo(hwnd=hwnd, title=title, class_name=class_name))
            return True

        user32.EnumWindows(WNDENUMPROC(enum_handler), 0)

        # 메모장(Notepad)이나 텍스트 편집기 창이 가장 위에 오도록 정렬
        def sort_key(w: WindowInfo) -> Tuple[int, str]:
            is_notepad = (
                "메모장" in w.title
                or "Notepad" in w.title
                or "Notepad" in w.class_name
            )
            return (0 if is_notepad else 1, w.title)

        windows.sort(key=sort_key)
        return windows

    @staticmethod
    def _find_editor_child(parent_hwnd: int) -> Optional[int]:
        """Windows 11 신형 메모장(RichEditD2DPT) 또는 기존 메모장(Edit)의 텍스트 입력 에디트 컨트롤 탐색"""
        editor_hwnds: List[Tuple[int, str]] = []

        def child_enum(hwnd: int, lparam: int) -> bool:
            c_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, c_buf, 256)
            c_name = c_buf.value
            if c_name in ("RichEditD2DPT", "Edit", "Scintilla"):
                editor_hwnds.append((hwnd, c_name))
            return True

        user32.EnumChildWindows(parent_hwnd, WNDENUMPROC(child_enum), 0)
        if editor_hwnds:
            # RichEditD2DPT(Windows 11 메모장) 우선
            for h, name in editor_hwnds:
                if name == "RichEditD2DPT":
                    return h
            return editor_hwnds[0][0]
        return None

    @classmethod
    def activate_window(cls, hwnd: int) -> bool:
        """
        지정한 핸들(hwnd)의 창을 강제로 최상단 활성화(Foreground)하고 키보드 포커스를 에디터에 맞춤
        (Windows 11의 SetForegroundWindow 제약 우회 적용)
        """
        if sys.platform != "win32" or not hwnd:
            return False

        if not user32.IsWindow(hwnd):
            return False

        # 1. 최소화되어 있으면 일반 크기로 복원
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        else:
            user32.ShowWindow(hwnd, SW_SHOW)

        current_thread = kernel32.GetCurrentThreadId()
        fg_hwnd = user32.GetForegroundWindow()
        fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0
        target_thread = user32.GetWindowThreadProcessId(hwnd, None)

        # 2. Windows 11 포커스 도용 방지 정책(Foreground Lock) 우회:
        # Alt 키 가상 이벤트를 펄스로 주면 Windows가 사용자 상호작용으로 인식하여 포커스 전환 허용
        try:
            user32.keybd_event(VK_MENU, 0, 0, 0)
            user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
        except Exception:
            pass

        # 3. 스레드 입력 큐 연결(AttachThreadInput)
        attached_fg = False
        attached_target = False
        if fg_thread and fg_thread != current_thread:
            attached_fg = bool(user32.AttachThreadInput(current_thread, fg_thread, True))
        if target_thread and target_thread != current_thread:
            attached_target = bool(user32.AttachThreadInput(current_thread, target_thread, True))

        try:
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
            user32.SetActiveWindow(hwnd)

            # 4. 메모장 등 내부 자식 입력 컨트롤(Edit / RichEdit)이 있으면 해당 컨트롤에 직접 SetFocus 부여
            editor_child = cls._find_editor_child(hwnd)
            if editor_child:
                user32.SetFocus(editor_child)
            else:
                user32.SetFocus(hwnd)
        finally:
            if attached_fg:
                user32.AttachThreadInput(current_thread, fg_thread, False)
            if attached_target:
                user32.AttachThreadInput(current_thread, target_thread, False)

        time.sleep(0.18)
        return user32.GetForegroundWindow() == hwnd

    @staticmethod
    def get_focused_control_hwnd() -> int:
        """현재 활성화된 창 내부에서 실제 키보드 포커스를 가진 에디트 컨트롤(메모장 텍스트 영역 등) 핸들 조회"""
        if sys.platform != "win32":
            return 0
        fg_hwnd = user32.GetForegroundWindow()
        if not fg_hwnd:
            return 0
        tid = user32.GetWindowThreadProcessId(fg_hwnd, None)
        gui_info = GUITHREADINFO()
        gui_info.cbSize = ctypes.sizeof(GUITHREADINFO)
        if user32.GetGUIThreadInfo(tid, ctypes.byref(gui_info)):
            if gui_info.hwndFocus:
                return gui_info.hwndFocus
            if gui_info.hwndActive:
                return gui_info.hwndActive
        return fg_hwnd

    @classmethod
    def get_current_ime_language(cls) -> Optional[LanguageMode]:
        """현재 포커스된 창의 IME 한/영 모드를 조회 (KO 또는 EN 반환)"""
        if sys.platform != "win32":
            return None
        target_hwnd = cls.get_focused_control_hwnd()
        if not target_hwnd:
            return None
        ime_hwnd = imm32.ImmGetDefaultIMEWnd(target_hwnd)
        if not ime_hwnd:
            return None
        status = user32.SendMessageW(ime_hwnd, WM_IME_CONTROL, IMC_GETCONVERSIONMODE, 0)
        if status & IME_CMODE_NATIVE:
            return LanguageMode.KO
        return LanguageMode.EN
