import threading
import time
from typing import Callable, Optional
from pynput import keyboard as pynput_kb

from src.core.decomposer import HangulDecomposer
from src.core.models import ActionType, LanguageMode, TypingAction
from src.core.timing_engine import TimingEngine
from src.core.typo_generator import TypoGenerator
from src.os_driver.keyboard_driver import KeyboardDriver
from src.os_driver.win32_window import Win32WindowManager


class TyperWorker:
    """
    백그라운드 스레드에서 카운트다운, 창 포커스 활성화, 자소 타이핑, 오타/수정 및
    글로벌 비상 정지 단축키(ESC / F12)를 관리하는 컨트롤러
    """

    def __init__(
        self,
        on_status: Optional[Callable[[str], None]] = None,
        on_progress: Optional[Callable[[int, int, int, int], None]] = None,
        on_finished: Optional[Callable[[bool, str], None]] = None,
    ) -> None:
        self.on_status = on_status          # 상태 텍스트 업데이트 콜백
        self.on_progress = on_progress      # (현재 인덱스, 전체 수, 현재 CPM, 누적 오타 수) 콜백
        self.on_finished = on_finished      # (정상완료여부, 메시지) 콜백

        self._driver = KeyboardDriver()
        self._thread: Optional[threading.Thread] = None
        self._hotkey_listener: Optional[pynput_kb.Listener] = None

        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # 기본값: 일시정지 아님 (진행 가능)

        self.is_running = False
        self.is_paused = False

    def start_typing(
        self,
        text: str,
        min_cpm: int = 200,
        max_cpm: int = 300,
        accuracy: float = 95.0,
        countdown_sec: int = 3,
        target_hwnd: Optional[int] = None,
    ) -> None:
        if self.is_running:
            return

        self._stop_event.clear()
        self._pause_event.set()
        self.is_running = True
        self.is_paused = False

        self._start_global_hotkey_listener()

        self._thread = threading.Thread(
            target=self._run_worker,
            args=(text, min_cpm, max_cpm, accuracy, countdown_sec, target_hwnd),
            daemon=True,
        )
        self._thread.start()

    def toggle_pause(self) -> bool:
        """일시정지 / 재개 토글. 반환값: 일시정지 상태 여부"""
        if not self.is_running:
            return False
        if self.is_paused:
            self.is_paused = False
            self._pause_event.set()
            self._emit_status("▶ 타이핑을 재개합니다...")
        else:
            self.is_paused = True
            self._pause_event.clear()
            self._emit_status("⏸ 일시정지됨 (재개 버튼을 누르세요)")
        return self.is_paused

    def stop_typing(self, reason: str = "사용자에 의해 중단됨 (ESC)") -> None:
        if not self.is_running:
            return
        self._stop_event.set()
        self._pause_event.set()  # 대기 중인 스레드 깨우기
        self._emit_status(f"⏹ {reason}")

    def _start_global_hotkey_listener(self) -> None:
        self._stop_global_hotkey_listener()

        def on_press(key: pynput_kb.Key | pynput_kb.KeyCode | None) -> None:
            if key in (pynput_kb.Key.esc, pynput_kb.Key.f12):
                self.stop_typing("비상 정지 단축키(ESC/F12) 입력으로 중단되었습니다.")

        self._hotkey_listener = pynput_kb.Listener(on_press=on_press)
        self._hotkey_listener.daemon = True
        self._hotkey_listener.start()

    def _stop_global_hotkey_listener(self) -> None:
        if self._hotkey_listener is not None:
            try:
                self._hotkey_listener.stop()
            except Exception:
                pass
            self._hotkey_listener = None

    def _sleep_interruptible(self, duration: float) -> bool:
        """중단(Stop) 및 일시정지(Pause)를 체크하며 대기. 중단 시 False 반환."""
        end_time = time.perf_counter() + duration
        while time.perf_counter() < end_time:
            if self._stop_event.is_set():
                return False
            if not self._pause_event.is_set():
                # 일시정지 동안 멈춤 시간 보정
                pause_start = time.perf_counter()
                self._pause_event.wait()
                end_time += (time.perf_counter() - pause_start)
                if self._stop_event.is_set():
                    return False
            remaining = end_time - time.perf_counter()
            if remaining > 0:
                time.sleep(min(0.015, remaining))
        return not self._stop_event.is_set()

    def _run_worker(
        self,
        text: str,
        min_cpm: int,
        max_cpm: int,
        accuracy: float,
        countdown_sec: int,
        target_hwnd: Optional[int],
    ) -> None:
        try:
            # 1. 카운트다운 수행
            for sec in range(countdown_sec, 0, -1):
                if target_hwnd:
                    self._emit_status(f"⏳ {sec}초 후 선택한 창을 활성화하고 타이핑을 시작합니다... (중단: ESC)")
                else:
                    self._emit_status(f"⏳ {sec}초 후 타이핑을 시작합니다! 메모장 등 입력할 창을 클릭하세요 (중단: ESC)")
                if not self._sleep_interruptible(1.0):
                    self._finish(False, "카운트다운 중 중단되었습니다.")
                    return

            # 2. 지정된 대상 창이 있으면 자동 활성화 (SetForegroundWindow)
            if target_hwnd:
                self._emit_status("🎯 선택한 대상 창으로 포커스를 이동하는 중...")
                Win32WindowManager.activate_window(target_hwnd)
                if not self._sleep_interruptible(0.25):
                    self._finish(False, "창 활성화 중 중단되었습니다.")
                    return

            # 3. 현재 대상 창의 초기 IME 한/영 상태 감지
            detected_lang = Win32WindowManager.get_current_ime_language()
            initial_lang = detected_lang if detected_lang is not None else LanguageMode.EN
            self._driver.current_lang = initial_lang

            # 4. 텍스트 자소 분해 및 액션 시퀀스 생성
            strokes = HangulDecomposer.decompose_text(text)
            timing = TimingEngine(min_cpm=min_cpm, max_cpm=max_cpm)
            actions = TypoGenerator.build_action_sequence(
                strokes=strokes,
                accuracy_percent=accuracy,
                timing=timing,
                initial_lang=initial_lang,
            )

            total_actions = len(actions)
            typo_count = 0

            if total_actions == 0:
                self._finish(True, "입력할 텍스트가 없습니다.")
                return

            # 5. 순차적으로 타이핑 액션 실행
            for idx, action in enumerate(actions, start=1):
                if self._stop_event.is_set():
                    self._finish(False, "사용자에 의해 타이핑이 중단되었습니다.")
                    return

                # 타건 전 딜레이 대기
                if action.delay_before > 0:
                    if not self._sleep_interruptible(action.delay_before):
                        self._finish(False, "사용자에 의해 타이핑이 중단되었습니다.")
                        return

                current_cpm = int(round(60.0 / max(0.05, action.delay_before))) if action.delay_before > 0 else min_cpm

                # 액션 유형별 실행
                if action.action_type == ActionType.LANG_SWITCH and action.keystroke:
                    self._driver.sync_or_ensure_language(
                        action.keystroke.lang,
                        hold_duration=action.hold_duration,
                    )
                    self._emit_status(f"🔄 {action.description}")

                elif action.action_type == ActionType.BACKSPACE:
                    self._driver.press_backspace(hold_duration=action.hold_duration)
                    self._emit_status(f"⌫ {action.description}")

                elif action.action_type == ActionType.KEY_PRESS and action.keystroke:
                    ks = action.keystroke
                    # 타건 직전 혹시 사용자가 한/영 키를 건드렸거나 창 초기 상태가 달랐을 경우를 대비해 언어 모드 보장
                    if ks.lang in (LanguageMode.KO, LanguageMode.EN):
                        self._driver.sync_or_ensure_language(ks.lang, hold_duration=0.025)

                    if action.is_typo:
                        typo_count += 1

                    self._driver.press_key(
                        key=ks.key,
                        shift=ks.shift,
                        hold_duration=action.hold_duration,
                    )
                    self._emit_status(f"⌨️ {action.description}  (속도: ~{current_cpm}타/분, 오타교정: {typo_count}회)")

                self._emit_progress(idx, total_actions, current_cpm, typo_count)

            self._finish(True, f"✅ 타이핑 완료! (총 {len(strokes)}타 입력, 오타 발생 및 자동 수정 {typo_count}회)")

        except Exception as e:
            self._finish(False, f"⚠️ 오류 발생: {e}")

    def _emit_status(self, msg: str) -> None:
        if self.on_status:
            self.on_status(msg)

    def _emit_progress(self, current: int, total: int, cpm: int, typos: int) -> None:
        if self.on_progress:
            self.on_progress(current, total, cpm, typos)

    def _finish(self, success: bool, msg: str) -> None:
        self.is_running = False
        self.is_paused = False
        self._stop_global_hotkey_listener()
        if self.on_finished:
            self.on_finished(success, msg)
