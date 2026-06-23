# -*- coding: utf-8 -*-
"""
순위 & 판매현황 모니터링 — 메인 실행 파일
"""

import tkinter as tk
from database.models import init_db
from gui.main_window import MainWindow


def main():
    init_db()
    root = tk.Tk()
    root.title("순위 & 판매현황 모니터링")
    root.geometry("1400x800")
    root.minsize(1100, 600)

    app = MainWindow(root)
    root.mainloop()


if __name__ == '__main__':
    main()
