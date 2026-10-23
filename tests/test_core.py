from typing import List
from src.core.decomposer import HangulDecomposer
from src.core.models import ActionType, LanguageMode, TypingAction
from src.core.timing_engine import TimingEngine
from src.core.typo_generator import TypoGenerator


def test_hangul_syllable_decomposition() -> None:
    """한글 완성형(초성/중성/종성, 쌍자음, 복합모음, 겹받침) 분해 검증"""
    # '닭' -> ㄷ(e), ㅏ(k), ㄹ(f), ㄱ(r)
    strokes = HangulDecomposer.decompose_text("닭")
    assert [(s.key, s.shift, s.display_char) for s in strokes] == [
        ("e", False, "ㄷ"),
        ("k", False, "ㅏ"),
        ("f", False, "ㄹ"),
        ("r", False, "ㄱ"),
    ]

    # '꽤' -> ㄲ(r, Shift), ㅗ(h), ㅐ(o)
    strokes_kkwae = HangulDecomposer.decompose_text("꽤")
    assert [(s.key, s.shift, s.display_char) for s in strokes_kkwae] == [
        ("r", True, "ㄲ"),
        ("h", False, "ㅗ"),
        ("o", False, "ㅐ"),
    ]


def test_mixed_korean_english_lang_switch() -> None:
    """한글과 영문이 섞여 있을 때 한/영 전환 액션이 정확히 삽입되는지 검증"""
    text = "안녕 Hello!"
    strokes = HangulDecomposer.decompose_text(text)
    timing = TimingEngine(min_cpm=200, max_cpm=300)
    actions = TypoGenerator.build_action_sequence(
        strokes=strokes,
        accuracy_percent=100.0,
        timing=timing,
        initial_lang=LanguageMode.EN,
    )

    lang_switches = [a for a in actions if a.action_type == ActionType.LANG_SWITCH]
    # 초기 EN -> '안녕' 시작 전 KO 전환 1회 -> 'Hello' 시작 전 EN 전환 1회 = 총 2회
    assert len(lang_switches) == 2
    assert lang_switches[0].keystroke is not None and lang_switches[0].keystroke.lang == LanguageMode.KO
    assert lang_switches[1].keystroke is not None and lang_switches[1].keystroke.lang == LanguageMode.EN


def test_typo_and_backspace_recovery_final_consistency() -> None:
    """정확도가 낮아 오타가 대량 발생하더라도 Backspace 복구 후 최종 유효 타건 시퀀스가 원본과 100% 일치하는지 검증"""
    text = "안녕하세요! Auto-Typer 200~300타 테스트입니다."
    expected_strokes = HangulDecomposer.decompose_text(text)
    timing = TimingEngine(min_cpm=200, max_cpm=300)

    # 정확도 0% (가능한 모든 자소에서 오타 발생 후 Backspace 복구)
    actions: List[TypingAction] = TypoGenerator.build_action_sequence(
        strokes=expected_strokes,
        accuracy_percent=0.0,
        timing=timing,
        initial_lang=LanguageMode.EN,
    )

    # 액션 스트림을 에뮬레이션하여 Backspace로 지워진 키를 제거한 최종 키 시퀀스 추출
    effective_keys = []
    typo_count = 0
    for act in actions:
        if act.action_type == ActionType.KEY_PRESS and act.keystroke is not None:
            effective_keys.append((act.keystroke.key, act.keystroke.shift, act.keystroke.display_char))
            if act.is_typo:
                typo_count += 1
        elif act.action_type == ActionType.BACKSPACE:
            assert len(effective_keys) > 0, "Backspace가 빈 버퍼에서 호출되면 안 됩니다."
            effective_keys.pop()

    assert typo_count > 0
    expected_keys = [(s.key, s.shift, s.display_char) for s in expected_strokes]
    assert effective_keys == expected_keys


def test_cpm_timing_range() -> None:
    """200~300타 범위 설정 시 샘플링된 CPM이 지정 범위를 준수하는지 검증"""
    timing = TimingEngine(min_cpm=200, max_cpm=300)
    for _ in range(100):
        cpm, delay = timing.sample_cpm_and_delay("a", "b")
        assert 200 <= cpm <= 300
        assert 0.19 <= delay <= 0.31
