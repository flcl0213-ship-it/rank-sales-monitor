# -*- coding: utf-8 -*-
"""브랜드 추가/수정 다이얼로그"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict


class BrandDialog(tk.Toplevel):
    FIELDS = [
        ('company_name',        '회사명 *'),
        ('brand_name',          '브랜드명 (표시용) *'),
        ('naver_seller_id',     '네이버 판매자 ID'),
        ('naver_client_id',     '네이버 커머스 Client ID'),
        ('naver_client_secret', '네이버 커머스 Client Secret'),
        ('coupang_vendor_id',   '쿠팡 Vendor ID'),
        ('coupang_access_key',  '쿠팡 Access Key'),
        ('coupang_secret_key',  '쿠팡 Secret Key'),
        ('memo',                '메모'),
    ]

    def __init__(self, parent, data: Dict = None, on_save: Callable = None):
        super().__init__(parent)
        self.title("브랜드 추가" if data is None else "브랜드 수정")
        self.resizable(False, False)
        self.grab_set()
        self.on_save = on_save
        self.vars: Dict[str, tk.StringVar] = {}

        for i, (key, label) in enumerate(self.FIELDS):
            tk.Label(self, text=label, anchor='e', width=28).grid(row=i, column=0, padx=10, pady=4, sticky='e')
            v = tk.StringVar(value=data.get(key, '') if data else '')
            self.vars[key] = v
            show = '*' if 'secret' in key.lower() else ''
            tk.Entry(self, textvariable=v, width=36, show=show).grid(row=i, column=1, padx=10, pady=4, sticky='w')

        btn_frame = tk.Frame(self)
        btn_frame.grid(row=len(self.FIELDS), column=0, columnspan=2, pady=12)
        tk.Button(btn_frame, text="저장", command=self._save,
                  bg='#2c3e50', fg='white', relief=tk.FLAT, width=10).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="취소", command=self.destroy,
                  relief=tk.FLAT, width=10).pack(side=tk.LEFT)

    def _save(self):
        data = {k: v.get().strip() for k, v in self.vars.items()}
        if not data['company_name'] or not data['brand_name']:
            tk.messagebox.showwarning("입력 오류", "회사명과 브랜드명은 필수입니다.", parent=self)
            return
        if self.on_save:
            self.on_save(data)
        self.destroy()
