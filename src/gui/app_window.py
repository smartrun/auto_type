from typing import Dict, List, Optional
import customtkinter as ctk

from src.core.decomposer import HangulDecomposer
from src.core.typer_worker import TyperWorker
from src.os_driver.win32_window import Win32WindowManager, WindowInfo


MANUAL_FOCUS_OPTION = "⚡ [수동 포커스] 카운트다운 동안 직접 마우스로 창 클릭하기"


class AutoTypeApp(ctk.CTk):
    """크로스 플랫폼 휴먼 라이크 자동 타이핑 프로그램 메인 GUI"""

    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.title("Auto-Typer - 휴먼 라이크 자동 타이핑기")
        self.geometry("760x720")
        self.minsize(680, 650)

        self._window_map: Dict[str, int] = {}
        self._worker = TyperWorker(
            on_status=self._on_worker_status,
            on_progress=self._on_worker_progress,
            on_finished=self._on_worker_finished,
        )

        self._build_ui()
        self.refresh_window_list()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ------------------------------------------------------------------
        # 1. 상단: 대상 창(메모장 등) 선택 영역
        # ------------------------------------------------------------------
        target_frame = ctk.CTkFrame(self, corner_radius=10)
        target_frame.grid(row=0, column=0, padx=16, pady=(14, 8), sticky="ew")
        target_frame.grid_columnconfigure(1, weight=1)

        lbl_target = ctk.CTkLabel(
            target_frame,
            text="🎯 타이핑 대상 창:",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        lbl_target.grid(row=0, column=0, padx=(14, 8), pady=12, sticky="w")

        self.window_combo = ctk.CTkOptionMenu(
            target_frame,
            values=[MANUAL_FOCUS_OPTION],
            font=ctk.CTkFont(size=13),
            dynamic_resizing=False,
        )
        self.window_combo.grid(row=0, column=1, padx=6, pady=12, sticky="ew")

        btn_refresh = ctk.CTkButton(
            target_frame,
            text="🔄 창 목록 새로고침",
            width=140,
            command=self.refresh_window_list,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        btn_refresh.grid(row=0, column=2, padx=(6, 14), pady=12)

        # ------------------------------------------------------------------
        # 2. 중단: 타이핑할 텍스트 입력 영역
        # ------------------------------------------------------------------
        text_frame = ctk.CTkFrame(self, corner_radius=10)
        text_frame.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")
        text_frame.grid_columnconfigure(0, weight=1)
        text_frame.grid_rowconfigure(1, weight=1)

        header_sub = ctk.CTkFrame(text_frame, fg_color="transparent")
        header_sub.grid(row=0, column=0, padx=14, pady=(10, 4), sticky="ew")
        header_sub.grid_columnconfigure(0, weight=1)

        lbl_text = ctk.CTkLabel(
            header_sub,
            text="📝 타이핑할 텍스트 입력 (한글/영문/특수문자 자동 전환 및 자소 단위 입력):",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        lbl_text.grid(row=0, column=0, sticky="w")

        self.lbl_char_stats = ctk.CTkLabel(
            header_sub,
            text="글자 수: 0자 | 예상 타건(자소) 수: 0타",
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "gray70"),
        )
        self.lbl_char_stats.grid(row=0, column=1, padx=(10, 8), sticky="e")

        btn_clear = ctk.CTkButton(
            header_sub,
            text="지우기",
            width=64,
            height=26,
            fg_color=("gray75", "gray30"),
            text_color=("black", "white"),
            command=self._clear_text,
        )
        btn_clear.grid(row=0, column=2, sticky="e")

        self.textbox = ctk.CTkTextbox(
            text_frame,
            font=ctk.CTkFont(family="Malgun Gothic", size=14),
            wrap="word",
        )
        self.textbox.grid(row=1, column=0, padx=14, pady=(4, 14), sticky="nsew")
        self.textbox.insert(
            "1.0",
            "안녕하세요! 자동 타이핑 프로그램 테스트입니다.\n"
            "Hello World! 한글과 English를 알아서 전환하며 사람처럼 자소를 1개씩 입력합니다.\n"
            "오타가 나더라도 스스로 Backspace를 눌러 수정합니다.",
        )
        self.textbox.bind("<KeyRelease>", self._update_text_stats)
        self._update_text_stats()

        # ------------------------------------------------------------------
        # 3. 설정 영역: 타수(CPM), 정확도(%), 카운트다운
        # ------------------------------------------------------------------
        settings_frame = ctk.CTkFrame(self, corner_radius=10)
        settings_frame.grid(row=2, column=0, padx=16, pady=8, sticky="ew")
        settings_frame.grid_columnconfigure(1, weight=1)
        settings_frame.grid_columnconfigure(3, weight=1)

        # (1) 타수 범위 설정
        lbl_speed = ctk.CTkLabel(
            settings_frame,
            text="⚡ 타이핑 속도 범위 (분당 타수):",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        lbl_speed.grid(row=0, column=0, padx=(14, 8), pady=(14, 8), sticky="w")

        speed_sub = ctk.CTkFrame(settings_frame, fg_color="transparent")
        speed_sub.grid(row=0, column=1, columnspan=3, padx=8, pady=(14, 8), sticky="w")

        self.entry_min_cpm = ctk.CTkEntry(speed_sub, width=75, justify="center", font=ctk.CTkFont(size=13))
        self.entry_min_cpm.insert(0, "200")
        self.entry_min_cpm.pack(side="left")

        ctk.CTkLabel(speed_sub, text=" 타  ~  ", font=ctk.CTkFont(size=13)).pack(side="left")

        self.entry_max_cpm = ctk.CTkEntry(speed_sub, width=75, justify="center", font=ctk.CTkFont(size=13))
        self.entry_max_cpm.insert(0, "300")
        self.entry_max_cpm.pack(side="left")

        ctk.CTkLabel(
            speed_sub,
            text=" 타/분 (매 타건마다 범위 내에서 랜덤하게 속도 변화)",
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "gray70"),
        ).pack(side="left", padx=(6, 0))

        # (2) 정확도 설정 (0% ~ 100%)
        lbl_acc_title = ctk.CTkLabel(
            settings_frame,
            text="🎯 타이핑 정확도 (오타 & 수정):",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        lbl_acc_title.grid(row=1, column=0, padx=(14, 8), pady=8, sticky="w")

        acc_sub = ctk.CTkFrame(settings_frame, fg_color="transparent")
        acc_sub.grid(row=1, column=1, columnspan=3, padx=8, pady=8, sticky="ew")
        acc_sub.grid_columnconfigure(0, weight=1)

        self.slider_accuracy = ctk.CTkSlider(
            acc_sub,
            from_=0,
            to=100,
            number_of_steps=100,
            command=self._on_accuracy_slider_change,
        )
        self.slider_accuracy.set(94)
        self.slider_accuracy.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.entry_accuracy = ctk.CTkEntry(acc_sub, width=65, justify="center", font=ctk.CTkFont(size=13))
        self.entry_accuracy.insert(0, "94")
        self.entry_accuracy.bind("<Return>", self._on_accuracy_entry_change)
        self.entry_accuracy.bind("<FocusOut>", self._on_accuracy_entry_change)
        self.entry_accuracy.grid(row=0, column=1)

        ctk.CTkLabel(
            acc_sub,
            text="%  (오타 발생 시 사람처럼 Backspace로 지우고 다시 입력)",
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "gray70"),
        ).grid(row=0, column=2, padx=(6, 6))

        # (3) 시작 대기 카운트다운 설정
        lbl_cd = ctk.CTkLabel(
            settings_frame,
            text="⏱️ 시작 전 준비 시간:",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        lbl_cd.grid(row=2, column=0, padx=(14, 8), pady=(8, 14), sticky="w")

        cd_sub = ctk.CTkFrame(settings_frame, fg_color="transparent")
        cd_sub.grid(row=2, column=1, columnspan=3, padx=8, pady=(8, 14), sticky="w")

        self.combo_countdown = ctk.CTkSegmentedButton(
            cd_sub,
            values=["1초", "3초", "5초", "10초"],
            font=ctk.CTkFont(size=13),
        )
        self.combo_countdown.set("3초")
        self.combo_countdown.pack(side="left")

        ctk.CTkLabel(
            cd_sub,
            text="  |  🚨 비상 정지 단축키: 언제든 [ESC] 또는 [F12] 키 입력",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#C0392B", "#E74C3C"),
        ).pack(side="left", padx=(12, 0))

        # ------------------------------------------------------------------
        # 4. 하단: 상태 표시줄 및 제어 버튼
        # ------------------------------------------------------------------
        bottom_frame = ctk.CTkFrame(self, corner_radius=10)
        bottom_frame.grid(row=3, column=0, padx=16, pady=(8, 16), sticky="ew")
        bottom_frame.grid_columnconfigure(0, weight=1)

        self.lbl_status = ctk.CTkLabel(
            bottom_frame,
            text="대기 중 — 대상 창(메모장 등)을 선택하고 [타이핑 시작]을 눌러주세요.",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        self.lbl_status.grid(row=0, column=0, padx=14, pady=(12, 6), sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(bottom_frame)
        self.progress_bar.grid(row=1, column=0, padx=14, pady=(0, 12), sticky="ew")
        self.progress_bar.set(0.0)

        btn_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=14, pady=(0, 14), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_start = ctk.CTkButton(
            btn_frame,
            text="▶ 타이핑 시작 (Start)",
            height=42,
            fg_color="#27AE60",
            hover_color="#1E8449",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.on_start_clicked,
        )
        self.btn_start.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.btn_pause = ctk.CTkButton(
            btn_frame,
            text="⏸ 일시정지 (Pause)",
            height=42,
            fg_color="#F39C12",
            hover_color="#D68910",
            font=ctk.CTkFont(size=15, weight="bold"),
            state="disabled",
            command=self.on_pause_clicked,
        )
        self.btn_pause.grid(row=0, column=1, padx=6, sticky="ew")

        self.btn_stop = ctk.CTkButton(
            btn_frame,
            text="⏹ 정지 (Stop / ESC)",
            height=42,
            fg_color="#C0392B",
            hover_color="#922B21",
            font=ctk.CTkFont(size=15, weight="bold"),
            state="disabled",
            command=self.on_stop_clicked,
        )
        self.btn_stop.grid(row=0, column=2, padx=(6, 0), sticky="ew")

    # ------------------------------------------------------------------
    # 이벤트 핸들러 및 헬퍼 메서드
    # ------------------------------------------------------------------
    def refresh_window_list(self) -> None:
        """현재 열려 있는 창 목록을 조회하여 드롭다운에 채움 (메모장이 있으면 자동 선택)"""
        windows: List[WindowInfo] = Win32WindowManager.list_open_windows(exclude_title_substring="Auto-Typer")
        self._window_map.clear()

        options = [MANUAL_FOCUS_OPTION]
        notepad_option: Optional[str] = None

        for w in windows:
            label = f"🪟 {w.title}  [#{w.hwnd}]"
            self._window_map[label] = w.hwnd
            options.append(label)
            if notepad_option is None and ("메모장" in w.title or "Notepad" in w.title or "Notepad" in w.class_name):
                notepad_option = label

        self.window_combo.configure(values=options)
        if notepad_option:
            self.window_combo.set(notepad_option)
        else:
            self.window_combo.set(MANUAL_FOCUS_OPTION)

    def _clear_text(self) -> None:
        self.textbox.delete("1.0", "end")
        self._update_text_stats()

    def _update_text_stats(self, _event: object = None) -> None:
        content = self.textbox.get("1.0", "end-1c")
        strokes = HangulDecomposer.decompose_text(content)
        self.lbl_char_stats.configure(
            text=f"글자 수: {len(content):,}자 | 예상 타건(자소) 수: {len(strokes):,}타"
        )

    def _on_accuracy_slider_change(self, val: float) -> None:
        int_val = int(round(val))
        self.entry_accuracy.delete(0, "end")
        self.entry_accuracy.insert(0, str(int_val))

    def _on_accuracy_entry_change(self, _event: object = None) -> None:
        try:
            val = float(self.entry_accuracy.get().strip())
            val = max(0.0, min(100.0, val))
        except ValueError:
            val = 95.0
        self.slider_accuracy.set(val)
        self.entry_accuracy.delete(0, "end")
        self.entry_accuracy.insert(0, str(int(round(val))))

    def on_start_clicked(self) -> None:
        text = self.textbox.get("1.0", "end-1c")
        if not text.strip():
            self.lbl_status.configure(text="⚠️ 입력할 텍스트가 비어 있습니다. 텍스트를 먼저 붙여넣어 주세요.")
            return

        try:
            min_cpm = int(self.entry_min_cpm.get().strip())
        except ValueError:
            min_cpm = 200

        try:
            max_cpm = int(self.entry_max_cpm.get().strip())
        except ValueError:
            max_cpm = 300

        if min_cpm > max_cpm:
            min_cpm, max_cpm = max_cpm, min_cpm
            self.entry_min_cpm.delete(0, "end")
            self.entry_min_cpm.insert(0, str(min_cpm))
            self.entry_max_cpm.delete(0, "end")
            self.entry_max_cpm.insert(0, str(max_cpm))

        try:
            accuracy = float(self.entry_accuracy.get().strip())
            accuracy = max(0.0, min(100.0, accuracy))
        except ValueError:
            accuracy = 94.0

        cd_str = self.combo_countdown.get().replace("초", "").strip()
        countdown_sec = int(cd_str) if cd_str.isdigit() else 3

        selected_win = self.window_combo.get()
        target_hwnd = self._window_map.get(selected_win, None)

        self.progress_bar.set(0.0)
        self.btn_start.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="⏸ 일시정지 (Pause)")
        self.btn_stop.configure(state="normal")

        self._worker.start_typing(
            text=text,
            min_cpm=min_cpm,
            max_cpm=max_cpm,
            accuracy=accuracy,
            countdown_sec=countdown_sec,
            target_hwnd=target_hwnd,
        )

    def on_pause_clicked(self) -> None:
        paused = self._worker.toggle_pause()
        if paused:
            self.btn_pause.configure(text="▶ 재개 (Resume)")
        else:
            self.btn_pause.configure(text="⏸ 일시정지 (Pause)")

    def on_stop_clicked(self) -> None:
        self._worker.stop_typing("정지 버튼 클릭으로 중단되었습니다.")

    def _on_worker_status(self, msg: str) -> None:
        self.after(0, lambda: self.lbl_status.configure(text=msg))

    def _on_worker_progress(self, current: int, total: int, _cpm: int, _typos: int) -> None:
        ratio = current / total if total > 0 else 0.0
        self.after(0, lambda: self.progress_bar.set(ratio))

    def _on_worker_finished(self, _success: bool, msg: str) -> None:
        def _reset_ui() -> None:
            self.lbl_status.configure(text=msg)
            self.btn_start.configure(state="normal")
            self.btn_pause.configure(state="disabled", text="⏸ 일시정지 (Pause)")
            self.btn_stop.configure(state="disabled")

        self.after(0, _reset_ui)
