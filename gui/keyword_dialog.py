# -*- coding: utf-8 -*-
"""키워드 관리 다이얼로그"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict
from database.db_manager import get_keywords, add_keyword, delete_keyword


class KeywordDialog(tk.Toplevel):
    def __init__(self, parent, product: Dict, platform: str = 'naver', on_change: Callable = None):
        super().__init__(parent)
        plat_label = '네이버' if platform == 'naver' else '쿠팡'
        self.title(f"키워드 관리 [{plat_label}] — {product['product_name']}")
        self.geometry("560x440")
        self.resizable(True, True)
        self.grab_set()
        self.product   = product
        self.platform  = platform
        self.on_change = on_change

        # 설명
        info = tk.Label(self,
            text="대표 키워드: 1개 (메인화면에 순위+판매 동시 표시)  |  서브 키워드: 제한 없음",
            fg='#555', font=('맑은 고딕', 9))
        info.pack(pady=(8, 0))

        # 추가 입력
        add_frame = tk.Frame(self, pady=6)
        add_frame.pack(fill=tk.X, padx=12)

        self.kw_var   = tk.StringVar()
        self.type_var = tk.StringVar(value='sub')

        tk.Entry(add_frame, textvariable=self.kw_var, width=30).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Combobox(add_frame, textvariable=self.type_var,
                     values=['main (대표)', 'sub (서브)'], width=14, state='readonly').pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(add_frame, text="추가", command=self._add,
                  bg='#2c3e50', fg='white', relief=tk.FLAT, padx=8).pack(side=tk.LEFT)

        # 목록
        cols = ('id', 'type', 'keyword')
        self.tree = ttk.Treeview(self, columns=cols, show='headings', height=14)
        self.tree.heading('id',      text='ID')
        self.tree.heading('type',    text='구분')
        self.tree.heading('keyword', text='키워드')
        self.tree.column('id',      width=40)
        self.tree.column('type',    width=80)
        self.tree.column('keyword', width=360)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)
        self.tree.tag_configure('main', background='#d6eaf8', font=('맑은 고딕', 9, 'bold'))

        btn = tk.Button(self, text="선택 삭제", command=self._delete,
                        bg='#c0392b', fg='white', relief=tk.FLAT)
        btn.pack(pady=6)
        self._reload()

    def _reload(self):
        self.tree.delete(*self.tree.get_children())
        for kw in get_keywords(self.product['id'], self.platform):
            tag = 'main' if kw['type'] == 'main' else ''
            self.tree.insert('', tk.END, iid=str(kw['id']), tags=(tag,),
                             values=(kw['id'], kw['type'], kw['keyword']))

    def _add(self):
        keyword = self.kw_var.get().strip()
        if not keyword:
            messagebox.showwarning("입력 오류", "키워드를 입력하세요.", parent=self)
            return
        ktype_raw = self.type_var.get()
        ktype = 'main' if ktype_raw.startswith('main') else 'sub'
        add_keyword(self.product['id'], keyword, ktype=ktype, platform=self.platform)

        self.kw_var.set('')
        self._reload()
        if self.on_change:
            self.on_change()

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            return
        if messagebox.askyesno("삭제", "선택한 키워드를 삭제하시겠습니까?", parent=self):
            for iid in sel:
                delete_keyword(int(iid))
            self._reload()
            if self.on_change:
                self.on_change()
