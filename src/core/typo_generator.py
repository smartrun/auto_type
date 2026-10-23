import random
from typing import Dict, List
from src.core.models import ActionType, KeyStroke, LanguageMode, TypingAction
from src.core.timing_engine import TimingEngine

# 2벌식 한글에서 자음 키 집합과 모음 키 집합 분리
# 한글 IME 특성상 자음 위치에서 자음 오타를, 모음 위치에서 모음 오타를 내야
# 글자 조합 상태가 깨지거나 다음 글자로 분리되지 않고 Backspace 1번으로 깔끔하게 자소만 지워져
# 최종 완성 텍스트가 원본과 100% 일치합니다!
KO_CONSONANT_NEIGHBORS: Dict[str, List[str]] = {
    'q': ['w', 'a', 's'],           # ㅂ 주변 자음: ㅈ, ㅁ, ㄴ
    'w': ['q', 'e', 'a', 's', 'd'], # ㅈ 주변 자음: ㅂ, ㄷ, ㅁ, ㄴ, ㅇ
    'e': ['w', 'r', 's', 'd', 'f'], # ㄷ 주변 자음: ㅈ, ㄱ, ㄴ, ㅇ, ㄹ
    'r': ['e', 't', 'd', 'f', 'g'], # ㄱ 주변 자음: ㄷ, ㅅ, ㅇ, ㄹ, ㅎ
    't': ['r', 'f', 'g'],           # ㅅ 주변 자음: ㄱ, ㄹ, ㅎ
    'a': ['q', 'w', 's', 'z', 'x'], # ㅁ 주변 자음
    's': ['q', 'w', 'e', 'a', 'd', 'z', 'x', 'c'], # ㄴ 주변 자음
    'd': ['w', 'e', 'r', 's', 'f', 'x', 'c', 'v'], # ㅇ 주변 자음
    'f': ['e', 'r', 't', 'd', 'g', 'c', 'v'],      # ㄹ 주변 자음
    'g': ['r', 't', 'f', 'v'],                     # ㅎ 주변 자음
    'z': ['a', 's', 'x'],           # ㅋ 주변 자음
    'x': ['a', 's', 'd', 'z', 'c'], # ㅌ 주변 자음
    'c': ['s', 'd', 'f', 'x', 'v'], # ㅊ 주변 자음
    'v': ['d', 'f', 'g', 'c'],      # ㅍ 주변 자음
}

KO_VOWEL_NEIGHBORS: Dict[str, List[str]] = {
    'y': ['u', 'h', 'j'],           # ㅛ 주변 모음: ㅕ, ㅗ, ㅓ
    'u': ['y', 'i', 'h', 'j', 'k'], # ㅕ 주변 모음: ㅛ, ㅑ, ㅗ, ㅓ, ㅏ
    'i': ['u', 'o', 'j', 'k', 'l'], # ㅑ 주변 모음: ㅕ, ㅐ, ㅓ, ㅏ, ㅣ
    'o': ['i', 'p', 'k', 'l'],      # ㅐ 주변 모음: ㅑ, ㅔ, ㅏ, ㅣ
    'p': ['o', 'l'],                # ㅔ 주변 모음: ㅐ, ㅣ
    'h': ['y', 'u', 'j', 'b', 'n'], # ㅗ 주변 모음: ㅛ, ㅕ, ㅓ, ㅠ, ㅜ
    'j': ['y', 'u', 'i', 'h', 'k', 'b', 'n', 'm'], # ㅓ 주변 모음
    'k': ['u', 'i', 'o', 'j', 'l', 'n', 'm'],      # ㅏ 주변 모음
    'l': ['i', 'o', 'p', 'k', 'm'],                # ㅣ 주변 모음
    'b': ['h', 'j', 'n'],           # ㅠ 주변 모음
    'n': ['h', 'j', 'k', 'b', 'm'], # ㅜ 주변 모음
    'm': ['j', 'k', 'l', 'n'],      # ㅡ 주변 모음
}

# 영문/숫자 QWERTY 인접 키 테이블
EN_QWERTY_NEIGHBORS: Dict[str, List[str]] = {
    'q': ['w', 'a', 's'],
    'w': ['q', 'e', 'a', 's', 'd'],
    'e': ['w', 'r', 's', 'd', 'f'],
    'r': ['e', 't', 'd', 'f', 'g'],
    't': ['r', 'y', 'f', 'g', 'h'],
    'y': ['t', 'u', 'g', 'h', 'j'],
    'u': ['y', 'i', 'h', 'j', 'k'],
    'i': ['u', 'o', 'j', 'k', 'l'],
    'o': ['i', 'p', 'k', 'l'],
    'p': ['o', 'l'],
    'a': ['q', 'w', 's', 'z', 'x'],
    's': ['q', 'w', 'e', 'a', 'd', 'z', 'x', 'c'],
    'd': ['w', 'e', 'r', 's', 'f', 'x', 'c', 'v'],
    'f': ['e', 'r', 't', 'd', 'g', 'c', 'v', 'b'],
    'g': ['r', 't', 'y', 'f', 'h', 'v', 'b', 'n'],
    'h': ['t', 'y', 'u', 'g', 'j', 'b', 'n', 'm'],
    'j': ['y', 'u', 'i', 'h', 'k', 'n', 'm'],
    'k': ['u', 'i', 'o', 'j', 'l', 'm'],
    'l': ['i', 'o', 'p', 'k'],
    'z': ['a', 's', 'x'],
    'x': ['a', 's', 'd', 'z', 'c'],
    'c': ['s', 'd', 'f', 'x', 'v'],
    'v': ['d', 'f', 'g', 'c', 'b'],
    'b': ['f', 'g', 'h', 'v', 'n'],
    'n': ['g', 'h', 'j', 'b', 'm'],
    'm': ['h', 'j', 'k', 'n'],
    '1': ['2', 'q'],
    '2': ['1', '3', 'q', 'w'],
    '3': ['2', '4', 'w', 'e'],
    '4': ['3', '5', 'e', 'r'],
    '5': ['4', '6', 'r', 't'],
    '6': ['5', '7', 't', 'y'],
    '7': ['6', '8', 'y', 'u'],
    '8': ['7', '9', 'u', 'i'],
    '9': ['8', '0', 'i', 'o'],
    '0': ['9', 'o', 'p'],
}

KEY_TO_KO_DISPLAY: Dict[str, str] = {
    'q': 'ㅂ', 'w': 'ㅈ', 'e': 'ㄷ', 'r': 'ㄱ', 't': 'ㅅ',
    'a': 'ㅁ', 's': 'ㄴ', 'd': 'ㅇ', 'f': 'ㄹ', 'g': 'ㅎ',
    'z': 'ㅋ', 'x': 'ㅌ', 'c': 'ㅊ', 'v': 'ㅍ',
    'y': 'ㅛ', 'u': 'ㅕ', 'i': 'ㅑ', 'o': 'ㅐ', 'p': 'ㅔ',
    'h': 'ㅗ', 'j': 'ㅓ', 'k': 'ㅏ', 'l': 'ㅣ',
    'b': 'ㅠ', 'n': 'ㅜ', 'm': 'ㅡ',
}


class TypoGenerator:
    """
    정확도(0% ~ 100%) 설정에 따라 인간형 오타 및 Backspace 수정 액션을 생성하는 엔진.
    - 한글 조합 중 오타가 나도 자음은 인접 자음으로, 모음은 인접 모음으로 오타를 내고
      즉시 Backspace로 지운 뒤 원래 자소를 입력하여 한글 조합 깨짐 없이 최종 결과물 100% 일치를 보장합니다.
    """

    @staticmethod
    def get_wrong_keystroke(stroke: KeyStroke) -> KeyStroke:
        """주어진 타건(stroke)에 대해 물리적으로 인접한 오타 KeyStroke를 생성"""
        k = stroke.key.lower()
        if stroke.lang == LanguageMode.KO:
            if k in KO_CONSONANT_NEIGHBORS:
                wrong_k = random.choice(KO_CONSONANT_NEIGHBORS[k])
            elif k in KO_VOWEL_NEIGHBORS:
                wrong_k = random.choice(KO_VOWEL_NEIGHBORS[k])
            else:
                wrong_k = k
            disp = KEY_TO_KO_DISPLAY.get(wrong_k, wrong_k)
            return KeyStroke(
                key=wrong_k,
                shift=False,  # 오타는 일반적으로 Shift 없는 인접 단타로 발생
                lang=stroke.lang,
                display_char=disp,
                char_index=stroke.char_index,
                is_typo_target=False,
            )
        else:
            neighbors = EN_QWERTY_NEIGHBORS.get(k, ['s' if k != 's' else 'a'])
            wrong_k = random.choice(neighbors)
            disp = wrong_k.upper() if stroke.shift else wrong_k
            return KeyStroke(
                key=wrong_k,
                shift=stroke.shift,
                lang=stroke.lang,
                display_char=disp,
                char_index=stroke.char_index,
                is_typo_target=False,
            )

    @classmethod
    def build_action_sequence(
        cls,
        strokes: List[KeyStroke],
        accuracy_percent: float,
        timing: TimingEngine,
        initial_lang: LanguageMode = LanguageMode.EN,
    ) -> List[TypingAction]:
        """
        분해된 KeyStroke 리스트를 받아:
        1. 한/영 자동 전환 액션 (LANG_SWITCH)
        2. 정확도 기반 오타 + 인지 딜레이 + Backspace 수정 액션
        3. 정상 타건 액션
        이 모두 포함된 최종 TypingAction 리스트를 생성합니다.
        """
        accuracy = max(0.0, min(100.0, float(accuracy_percent)))
        error_prob = (100.0 - accuracy) / 100.0

        actions: List[TypingAction] = []
        current_lang = initial_lang
        prev_key = ""

        i = 0
        n = len(strokes)
        while i < n:
            stroke = strokes[i]

            # 1. 한/영 전환이 필요한지 확인 (NEUTRAL은 현재 언어 유지)
            if stroke.lang in (LanguageMode.KO, LanguageMode.EN) and stroke.lang != current_lang:
                actions.append(
                    TypingAction(
                        action_type=ActionType.LANG_SWITCH,
                        keystroke=KeyStroke(
                            key="VK_HANGUL",
                            lang=stroke.lang,
                            display_char="한/영",
                            char_index=stroke.char_index,
                            is_typo_target=False,
                        ),
                        delay_before=timing.sample_lang_switch_delay(),
                        hold_duration=timing.sample_hold_duration(),
                        is_typo=False,
                        description=f"한/영 전환 -> {'한글' if stroke.lang == LanguageMode.KO else '영문'}",
                    )
                )
                current_lang = stroke.lang

            # 2. 한글 복합모음(ㅘ, ㅝ 등) 또는 겹받침(ㄺ, ㅄ 등)의 두 번째 타건인지 확인
            # 한글 IME에서 겹자음/복합모음의 두 번째 자소나 종성에서 오타가 나면 다음 음절로 넘어갈 수 있으므로
            # 동일 한글 음절의 첫 자소(초성)나 중성 첫 타, 혹은 영문/숫자에서만 오타를 발생시키면
            # Backspace 1번으로 언제나 100% 깔끔하게 지워지고 한글 조합이 절대 깨지지 않습니다!
            can_make_typo = stroke.is_typo_target
            if can_make_typo and stroke.lang == LanguageMode.KO:
                # 같은 글자(char_index) 내에서 몇 번째 타건인지 계산
                pos_in_char = 0
                idx_back = i - 1
                while idx_back >= 0 and strokes[idx_back].char_index == stroke.char_index:
                    pos_in_char += 1
                    idx_back -= 1
                # 초성(pos_in_char == 0) 또는 단모음 중성(pos_in_char == 1)에서만 오타 허용
                # 만약 다음 타건도 같은 글자의 중성(즉 복합모음의 첫 타)이거나 종성 위치(pos_in_char >= 2)면
                # IME 조합 안전성을 위해 초성(pos_in_char == 0)에서만 오타를 내거나, 종성이 없는 글자의 중성에서만 오타를 냄
                if pos_in_char >= 2:
                    can_make_typo = False
                elif pos_in_char == 1:
                    # 뒤에 같은 글자의 타건(복합모음 2번째 타 또는 종성)이 있으면 초성에서만 오타가 나도록 보호
                    if i + 1 < n and strokes[i + 1].char_index == stroke.char_index:
                        can_make_typo = False

            # 3. 오타 발생 여부 결정
            make_typo = can_make_typo and (random.random() < error_prob)

            if make_typo:
                wrong_stroke = cls.get_wrong_keystroke(stroke)
                _, typo_delay = timing.sample_cpm_and_delay(prev_key, wrong_stroke.key)

                # (A) 잘못된 인접 키 누름
                actions.append(
                    TypingAction(
                        action_type=ActionType.KEY_PRESS,
                        keystroke=wrong_stroke,
                        delay_before=typo_delay,
                        hold_duration=timing.sample_hold_duration(),
                        is_typo=True,
                        description=f"오타 입력: '{wrong_stroke.display_char}' (원래 '{stroke.display_char}')",
                    )
                )

                # (B) 오타 인지 후 Backspace 입력
                actions.append(
                    TypingAction(
                        action_type=ActionType.BACKSPACE,
                        keystroke=KeyStroke(
                            key="BACKSPACE",
                            lang=LanguageMode.NEUTRAL,
                            display_char="⌫",
                            char_index=stroke.char_index,
                            is_typo_target=False,
                        ),
                        delay_before=timing.sample_typo_reaction_delay(),
                        hold_duration=timing.sample_hold_duration(),
                        is_typo=True,
                        description=f"오타 수정 (Backspace)",
                    )
                )

                # (C) Backspace 직후 원래의 올바른 키 입력
                actions.append(
                    TypingAction(
                        action_type=ActionType.KEY_PRESS,
                        keystroke=stroke,
                        delay_before=timing.sample_post_backspace_delay(),
                        hold_duration=timing.sample_hold_duration(),
                        is_typo=False,
                        description=f"교정 입력: '{stroke.display_char}'",
                    )
                )
            else:
                # 정상 타건 입력
                _, normal_delay = timing.sample_cpm_and_delay(prev_key, stroke.key)
                actions.append(
                    TypingAction(
                        action_type=ActionType.KEY_PRESS,
                        keystroke=stroke,
                        delay_before=normal_delay,
                        hold_duration=timing.sample_hold_duration(),
                        is_typo=False,
                        description=f"입력: '{stroke.display_char}'",
                    )
                )

            prev_key = stroke.key
            i += 1

        return actions
