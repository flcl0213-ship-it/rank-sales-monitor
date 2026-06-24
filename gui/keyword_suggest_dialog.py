# -*- coding: utf-8 -*-
"""키워드 추천 다이얼로그 — 네이버 검색광고 API 연동"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable


class KeywordSuggestDialog(tk.Toplevel):
    def __init__(self, parent, seed_keyword: str = '', on_add: Callable = None):
        super().__init__(parent)
        self.title("키워드 추천")
        self.geometry("640x520")
        self.resizable(True, True)
        self.grab_set()
        self.on_add = on_add

        # 검색 입력
        top = tk.Frame(self, pady=8)
        top.pack(fill=tk.X, padx=12)
        tk.Label(top, text="씨앗 키워드:", font=('맑은 고딕', 10)).pack(side=tk.LEFT)
        self.seed_var = tk.StringVar(value=seed_keyword)
        tk.Entry(top, textvariable=self.seed_var, width=28,
                 font=('맑은 고딕', 10)).pack(side=tk.LEFT, padx=6)
        tk.Button(top, text="검색", command=self._search,
                  bg='#2980b9', fg='white', relief=tk.FLAT, padx=12).pack(side=tk.LEFT)

        self.info_lbl = tk.Label(self, text="씨앗 키워드를 입력하고 검색하세요.",
                                  fg='#888', font=('맑은 고딕', 9))
        self.info_lbl.pack(anchor='w', padx=14)

        # 결과 테이블
        cols = ('check', 'keyword', 'total', 'pc', 'mobile', 'competition')
        self.tree = ttk.Treeview(self, columns=cols, show='headings', height=18)
        self.tree.heading('check',       text='선택')
        self.tree.heading('keyword',     text='키워드')
        self.tree.heading('total',       text='월간검색(합계)')
        self.tree.heading('pc',          text='PC')
        self.tree.heading('mobile',      text='모바일')
        self.tree.heading('competition', text='경쟁도')
        self.tree.column('check',       width=45,  anchor=tk.CENTER)
        self.tree.column('keyword',     width=200, anchor=tk.W)
        self.tree.column('total',       width=110, anchor=tk.CENTER)
        self.tree.column('pc',          width=80,  anchor=tk.CENTER)
        self.tree.column('mobile',      width=80,  anchor=tk.CENTER)
        self.tree.column('competition', width=70,  anchor=tk.CENTER)

        self.tree.tag_configure('high',   background='#fdecea')
        self.tree.tag_configure('mid',    background='#fff8e1')
        self.tree.tag_configure('low',    background='#e8f5e9')
        self.tree.tag_configure('checked', background='#d5f5e3')

        sb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 0), pady=4)
        sb.pack(side=tk.LEFT, fill=tk.Y, pady=4, padx=(0, 4))

        self.tree.bind('<Button-1>', self._on_click)
        self._checked = set()

        # 하단 버튼
        btn_frame = tk.Frame(self, pady=8)
        btn_frame.pack(fill=tk.X, padx=12)
        tk.Button(btn_frame, text="선택 항목 서브키워드로 추가",
                  command=self._add_selected,
                  bg='#27ae60', fg='white', relief=tk.FLAT, padx=12).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="닫기", command=self.destroy,
                  relief=tk.FLAT, padx=12).pack(side=tk.LEFT, padx=4)

        if seed_keyword:
            self._search()

    def _search(self):
        seed = self.seed_var.get().strip()
        if not seed:
            messagebox.showwarning("입력 오류", "씨앗 키워드를 입력하세요.", parent=self)
            return
        self.info_lbl.config(text="검색 중...", fg='#888')
        self.update()

        from core.naver.searchad_api import get_related_keywords
        results = get_related_keywords(seed, top_n=100)

        self.tree.delete(*self.tree.get_children())
        self._checked.clear()
        self._results = results

        for r in results:
            comp = r['competition']
            tag  = {'높음': 'high', '보통': 'mid', '낮음': 'low'}.get(comp, '')
            total_str = f"{r['total']:,}" if r['total'] else '< 10'
            pc_str    = f"{r['pc']:,}"    if r['pc']    else '< 10'
            mob_str   = f"{r['mobile']:,}" if r['mobile'] else '< 10'
            self.tree.insert('', tk.END, iid=r['keyword'], tags=(tag,),
                             values=('□', r['keyword'], total_str, pc_str, mob_str, comp))

        self.info_lbl.config(
            text=f"연관 키워드 {len(results)}개  |  행 클릭으로 선택 (녹색 = 선택됨)",
            fg='#2c3e50'
        )

    def _on_click(self, event):
        row = self.tree.identify_row(event.y)
        if not row:
            return
        if row in self._checked:
            self._checked.discard(row)
            cur_tags = [t for t in self.tree.item(row, 'tags') if t != 'checked']
            self.tree.item(row, tags=cur_tags)
            self.tree.set(row, 'check', '□')
        else:
            self._checked.add(row)
            self.tree.item(row, tags=('checked',))
            self.tree.set(row, 'check', '☑')

    def _add_selected(self):
        if not self._checked:
            messagebox.showinfo("알림", "추가할 키워드를 선택하세요.", parent=self)
            return
        if self.on_add:
            self.on_add(list(self._checked))
        messagebox.showinfo("완료", f"{len(self._checked)}개 키워드가 추가되었습니다.", parent=self)
        self._checked.clear()
        for row in self.tree.get_children():
            cur_tags = [t for t in self.tree.item(row, 'tags') if t != 'checked']
            self.tree.item(row, tags=cur_tags)
            self.tree.set(row, 'check', '□')
