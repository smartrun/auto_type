import os
import sys

# 프로젝트 루트를 sys.path에 추가하여 어디서 실행하든 패키지 임포트가 동작하도록 보장
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.gui.app_window import AutoTypeApp


def main() -> None:
    app = AutoTypeApp()
    app.mainloop()


if __name__ == "__main__":
    main()
