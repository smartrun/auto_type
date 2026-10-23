import random
from typing import Tuple


class TimingEngine:
    """분당 타수(CPM, Strokes Per Minute) 범위 내에서 인간적인 랜덤 딜레이를 생성하는 엔진"""

    def __init__(self, min_cpm: int = 200, max_cpm: int = 300):
        self.set_cpm_range(min_cpm, max_cpm)

    def set_cpm_range(self, min_cpm: int, max_cpm: int) -> None:
        self.min_cpm = max(10, min(min_cpm, max_cpm))
        self.max_cpm = max(self.min_cpm, max(min_cpm, max_cpm))

    def sample_cpm_and_delay(self, prev_key: str = "", current_key: str = "") -> Tuple[int, float]:
        """
        현재 타건의 순간 타수(CPM)와 대기 시간(초)을 반환합니다.
        가우시안 분포와 균등 분포를 혼합하여 범위(min_cpm ~ max_cpm) 안에서 자연스러운 리듬감을 만듭니다.
        """
        if self.min_cpm == self.max_cpm:
            cpm = float(self.min_cpm)
        else:
            mean = (self.min_cpm + self.max_cpm) / 2.0
            std = (self.max_cpm - self.min_cpm) / 4.0
            sampled = random.gauss(mean, std)
            # 범위를 벗어나면 균등 분포로 보정
            cpm = max(float(self.min_cpm), min(float(self.max_cpm), sampled))

        base_delay = 60.0 / cpm

        # 동일한 물리 키를 연속으로 치는 경우 (예: 'll' 또는 초성/종성 연속) 약간의 물리적 가감속
        if prev_key and prev_key == current_key:
            base_delay *= random.uniform(0.85, 1.10)

        # 문장 부호나 줄바꿈 직후에는 사람이 숨을 고르는 미세 딜레이 추가
        if prev_key in ('.', ',', '!', '?', '\n'):
            base_delay += random.uniform(0.08, 0.22)
        elif prev_key == ' ':
            base_delay += random.uniform(0.01, 0.05)

        return int(round(cpm)), base_delay

    @staticmethod
    def sample_hold_duration() -> float:
        """키를 누르고 떼기까지의 시간 (초): 22ms ~ 58ms"""
        return random.uniform(0.022, 0.058)

    @staticmethod
    def sample_typo_reaction_delay() -> float:
        """오타를 친 직후 사람이 '앗 오타 났다!'라고 인지하고 Backspace로 손이 가는 시간 (초)"""
        return random.uniform(0.14, 0.34)

    @staticmethod
    def sample_post_backspace_delay() -> float:
        """Backspace로 지운 직후 원래 키를 다시 누르기까지의 시간 (초)"""
        return random.uniform(0.08, 0.18)

    @staticmethod
    def sample_lang_switch_delay() -> float:
        """한/영 전환 키 입력 전후 안정화 딜레이 (초)"""
        return random.uniform(0.05, 0.09)
