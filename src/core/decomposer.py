from typing import Dict, List, Tuple
from src.core.models import KeyStroke, LanguageMode

# 유니코드 한글 음절 분해용 초성/중성/종성 테이블
CHOSUNG_LIST = [
    'ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ',
    'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'
]

JUNGSUNG_LIST = [
    'ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ',
    'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ'
]

JONGSUNG_LIST = [
    '', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ',
    'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ',
    'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'
]

# 복합 모음 및 겹받침을 단일 타건 자소 시퀀스로 분리하는 테이블
COMPLEX_JAMO_MAP: Dict[str, List[str]] = {
    # 복합 모음
    'ㅘ': ['ㅗ', 'ㅏ'],
    'ㅙ': ['ㅗ', 'ㅐ'],
    'ㅚ': ['ㅗ', 'ㅣ'],
    'ㅝ': ['ㅜ', 'ㅓ'],
    'ㅞ': ['ㅜ', 'ㅔ'],
    'ㅟ': ['ㅜ', 'ㅣ'],
    'ㅢ': ['ㅡ', 'ㅣ'],
    # 겹받침 (종성)
    'ㄳ': ['ㄱ', 'ㅅ'],
    'ㄵ': ['ㄴ', 'ㅈ'],
    'ㄶ': ['ㄴ', 'ㅎ'],
    'ㄺ': ['ㄹ', 'ㄱ'],
    'ㄻ': ['ㄹ', 'ㅁ'],
    'ㄼ': ['ㄹ', 'ㅂ'],
    'ㄽ': ['ㄹ', 'ㅅ'],
    'ㄾ': ['ㄹ', 'ㅌ'],
    'ㄿ': ['ㄹ', 'ㅍ'],
    'ㅀ': ['ㄹ', 'ㅎ'],
    'ㅄ': ['ㅂ', 'ㅅ'],
}

# 단일 자소 -> (QWERTY 물리 키, Shift 여부) 매핑 (2벌식 표준)
JAMO_TO_KEY_MAP: Dict[str, Tuple[str, bool]] = {
    # 자음
    'ㅂ': ('q', False), 'ㅃ': ('q', True),
    'ㅈ': ('w', False), 'ㅉ': ('w', True),
    'ㄷ': ('e', False), 'ㄸ': ('e', True),
    'ㄱ': ('r', False), 'ㄲ': ('r', True),
    'ㅅ': ('t', False), 'ㅆ': ('t', True),
    'ㅁ': ('a', False),
    'ㄴ': ('s', False),
    'ㅇ': ('d', False),
    'ㄹ': ('f', False),
    'ㅎ': ('g', False),
    'ㅋ': ('z', False),
    'ㅌ': ('x', False),
    'ㅊ': ('c', False),
    'ㅍ': ('v', False),
    # 모음
    'ㅛ': ('y', False),
    'ㅕ': ('u', False),
    'ㅑ': ('i', False),
    'ㅐ': ('o', False), 'ㅒ': ('o', True),
    'ㅔ': ('p', False), 'ㅖ': ('p', True),
    'ㅗ': ('h', False),
    'ㅓ': ('j', False),
    'ㅏ': ('k', False),
    'ㅣ': ('l', False),
    'ㅠ': ('b', False),
    'ㅜ': ('n', False),
    'ㅡ': ('m', False),
}

# Shift를 눌러야 입력되는 영문 자판 특수문자 -> 기본 키 매핑
SHIFTED_SYMBOL_MAP: Dict[str, str] = {
    '~': '`', '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
    '^': '6', '&': '7', '*': '8', '(': '9', ')': '0', '_': '-',
    '+': '=', '{': '[', '}': ']', '|': '\\', ':': ';', '"': "'",
    '<': ',', '>': '.', '?': '/'
}

# Shift 없이 그대로 입력되는 기본 기호/숫자
UNSHIFTED_SYMBOLS = set("`1234567890-=[]\\;',./")


class HangulDecomposer:
    """입력 텍스트를 실제 키보드 타건(KeyStroke) 시퀀스로 분해하는 클래스"""

    @classmethod
    def decompose_jamo_to_strokes(cls, jamo: str, char_index: int) -> List[KeyStroke]:
        """단일 또는 복합 자모(예: 'ㄱ', 'ㅘ', 'ㄺ')를 KeyStroke 리스트로 변환"""
        sub_jamos = COMPLEX_JAMO_MAP.get(jamo, [jamo])
        strokes: List[KeyStroke] = []
        for sj in sub_jamos:
            if sj in JAMO_TO_KEY_MAP:
                key, shift = JAMO_TO_KEY_MAP[sj]
                strokes.append(
                    KeyStroke(
                        key=key,
                        shift=shift,
                        lang=LanguageMode.KO,
                        display_char=sj,
                        char_index=char_index,
                        is_typo_target=True,
                    )
                )
        return strokes

    @classmethod
    def decompose_char(cls, ch: str, char_index: int = -1) -> List[KeyStroke]:
        """단일 문자를 1개 이상의 KeyStroke 시퀀스로 분해"""
        code = ord(ch)

        # 1. 한글 완성형 음절 ('가' ~ '힣': 0xAC00 ~ 0xD7A3)
        if 0xAC00 <= code <= 0xD7A3:
            offset = code - 0xAC00
            cho_idx = offset // (21 * 28)
            jung_idx = (offset % (21 * 28)) // 28
            jong_idx = offset % 28

            strokes: List[KeyStroke] = []
            # 초성
            strokes.extend(cls.decompose_jamo_to_strokes(CHOSUNG_LIST[cho_idx], char_index))
            # 중성
            strokes.extend(cls.decompose_jamo_to_strokes(JUNGSUNG_LIST[jung_idx], char_index))
            # 종성 (있을 경우)
            if jong_idx > 0:
                strokes.extend(cls.decompose_jamo_to_strokes(JONGSUNG_LIST[jong_idx], char_index))
            return strokes

        # 2. 한글 호환용 자모 ('ㄱ' ~ 'ㅣ': 0x3131 ~ 0x3163)
        if ch in JAMO_TO_KEY_MAP or ch in COMPLEX_JAMO_MAP:
            return cls.decompose_jamo_to_strokes(ch, char_index)

        # 3. 영문 소문자 ('a' ~ 'z')
        if 'a' <= ch <= 'z':
            return [
                KeyStroke(
                    key=ch,
                    shift=False,
                    lang=LanguageMode.EN,
                    display_char=ch,
                    char_index=char_index,
                    is_typo_target=True,
                )
            ]

        # 4. 영문 대문자 ('A' ~ 'Z')
        if 'A' <= ch <= 'Z':
            return [
                KeyStroke(
                    key=ch.lower(),
                    shift=True,
                    lang=LanguageMode.EN,
                    display_char=ch,
                    char_index=char_index,
                    is_typo_target=True,
                )
            ]

        # 5. 줄바꿈, 탭, 공백 (언어 중립, 오타 제외)
        if ch == '\n':
            return [
                KeyStroke(
                    key='\n',
                    shift=False,
                    lang=LanguageMode.NEUTRAL,
                    display_char='↵',
                    char_index=char_index,
                    is_typo_target=False,
                )
            ]
        if ch == '\t':
            return [
                KeyStroke(
                    key='\t',
                    shift=False,
                    lang=LanguageMode.NEUTRAL,
                    display_char='⇥',
                    char_index=char_index,
                    is_typo_target=False,
                )
            ]
        if ch == ' ':
            return [
                KeyStroke(
                    key=' ',
                    shift=False,
                    lang=LanguageMode.NEUTRAL,
                    display_char='␣',
                    char_index=char_index,
                    is_typo_target=False,
                )
            ]

        # 6. 숫자 및 기본 기호 (언어 중립)
        if ch in UNSHIFTED_SYMBOLS:
            is_digit_or_letter = ch.isalnum()
            return [
                KeyStroke(
                    key=ch,
                    shift=False,
                    lang=LanguageMode.NEUTRAL,
                    display_char=ch,
                    char_index=char_index,
                    is_typo_target=is_digit_or_letter,
                )
            ]

        # 7. Shift 조합 특수문자 (언어 중립)
        if ch in SHIFTED_SYMBOL_MAP:
            base_key = SHIFTED_SYMBOL_MAP[ch]
            return [
                KeyStroke(
                    key=base_key,
                    shift=True,
                    lang=LanguageMode.NEUTRAL,
                    display_char=ch,
                    char_index=char_index,
                    is_typo_target=False,
                )
            ]

        # 8. 그 외 유니코드 특수문자 (원문 그대로 전달)
        return [
            KeyStroke(
                key=ch,
                shift=False,
                lang=LanguageMode.NEUTRAL,
                display_char=ch,
                char_index=char_index,
                is_typo_target=False,
            )
        ]

    @classmethod
    def decompose_text(cls, text: str) -> List[KeyStroke]:
        """전체 문자열을 타건 시퀀스로 분해 (CRLF를 LF로 정규화)"""
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        result: List[KeyStroke] = []
        for idx, ch in enumerate(normalized):
            result.extend(cls.decompose_char(ch, char_index=idx))
        return result
