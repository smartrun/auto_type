from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class LanguageMode(Enum):
    KO = auto()       # 한글 입력 상태 필요
    EN = auto()       # 영문 입력 상태 필요
    NEUTRAL = auto()  # 현재 상태 무관 (숫자, 공백, 일반 기호, 제어키)


class ActionType(Enum):
    KEY_PRESS = auto()      # 일반 키 입력 (자소, 영문, 기호 등)
    BACKSPACE = auto()      # 오타 수정용 백스페이스
    LANG_SWITCH = auto()    # 한/영 전환
    PAUSE = auto()          # 오타 인지 대기 또는 문장 부호 후 호흡 대기


@dataclass(frozen=True)
class KeyStroke:
    """단일 키보드 타건 정보 (2벌식 자소 1타 또는 영문/기호 1타)"""
    key: str                        # 물리적 QWERTY 키 문자 (예: 'r', 'k', ' ', '\n', '\t') 또는 특수 이름
    shift: bool = False             # Shift 조합 여부 (쌍자음, 대문자, 특수문자 상단 등)
    lang: LanguageMode = LanguageMode.NEUTRAL
    display_char: str = ""          # 디버깅/로그 표시용 (예: 'ㄱ', 'ㅏ', 'A')
    char_index: int = -1            # 원본 텍스트에서의 글자 인덱스
    is_typo_target: bool = True     # 오타 발생 가능 대상인지 여부 (공백/줄바꿈은 기본적으로 제외 가능)


@dataclass
class TypingAction:
    """실제 드라이버가 실행할 개별 액션"""
    action_type: ActionType
    keystroke: Optional[KeyStroke] = None
    delay_before: float = 0.0       # 이 액션을 실행하기 전 대기 시간 (초)
    hold_duration: float = 0.035    # 키를 누르고 있는 시간 (초)
    is_typo: bool = False           # 오타로 인해 발생한 액션인지 여부
    description: str = ""           # UI 상태 표시용 설명
