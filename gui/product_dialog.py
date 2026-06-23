# -*- coding: utf-8 -*-
"""네이버 / 쿠팡 상품 추가·수정 다이얼로그"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, List


class NaverProductDialog(tk.Toplevel):
    def __init__(self, parent, brands: List[Dict], data: Dict = None, on_save: Callable = None):
        super().__init__(parent)
        self.title("네이버 상품 추가" if data is None else "네이버 상품 수정")
        self.resizable(False, False)
        self.grab_set()
        self.on_save = on_save
        self.brands  = brands

        fields = [
            ('model_name',       '모델명 (예: B100D)'),
            ('product_name',     '상품명 *'),
            ('seller',           '판매자/스토어명'),
            ('url_naver',        '네이버 상품 URL'),
            ('naver_product_id', '네이버 상품 ID (선택)'),
        ]

        tk.Label(self, text='브랜드 *', anchor='e', width=22).grid(row=0, column=0, padx=10, pady=4, sticky='e')
        self.brand_var = tk.StringVar()
        cb = ttk.Combobox(self, textvariable=self.brand_var,
                          values=[b['brand_name'] for b in brands], state='readonly', width=38)
        cb.grid(row=0, column=1, padx=10, pady=4, sticky='w')
        if data:
            cur = next((b['brand_name'] for b in brands if b['id'] == data.get('brand_id')), '')
            self.brand_var.set(cur)

        self.vars: Dict[str, tk.StringVar] = {}
        for i, (key, label) in enumerate(fields, start=1):
            tk.Label(self, text=label, anchor='e', width=22).grid(row=i, column=0, padx=10, pady=4, sticky='e')
            v = tk.StringVar(value=data.get(key, '') if data else '')
            self.vars[key] = v
            tk.Entry(self, textvariable=v, width=50).grid(row=i, column=1, padx=10, pady=4, sticky='w')

        row = len(fields) + 1
        btn = tk.Frame(self)
        btn.grid(row=row, column=0, columnspan=2, pady=12)
        tk.Button(btn, text="저장", command=self._save,
                  bg='#2c3e50', fg='white', relief=tk.FLAT, width=10).pack(side=tk.LEFT, padx=6)
        tk.Button(btn, text="취소", command=self.destroy,
                  relief=tk.FLAT, width=10).pack(side=tk.LEFT)

    def _save(self):
        brand_name = self.brand_var.get()
        brand_id   = next((b['id'] for b in self.brands if b['brand_name'] == brand_name), None)
        name       = self.vars['product_name'].get().strip()
        if not brand_id or not name:
            messagebox.showwarning("입력 오류", "브랜드와 상품명은 필수입니다.", parent=self)
            return
        data = {'brand_id': brand_id}
        data.update({k: v.get().strip() for k, v in self.vars.items()})
        if self.on_save:
            self.on_save(data)
        self.destroy()


class CoupangProductDialog(tk.Toplevel):
    def __init__(self, parent, brands: List[Dict], data: Dict = None, on_save: Callable = None):
        super().__init__(parent)
        self.title("쿠팡 상품 추가" if data is None else "쿠팡 상품 수정")
        self.resizable(False, False)
        self.grab_set()
        self.on_save = on_save
        self.brands  = brands

        fields = [
            ('model_name',          '모델명 (예: B100D)'),
            ('product_name',        '상품명 (옵션포함) *'),
            ('url_coupang',         '쿠팡 상품 URL'),
            ('coupang_product_id',  '쿠팡 상품 ID (선택)'),
        ]

        tk.Label(self, text='브랜드 *', anchor='e', width=22).grid(row=0, column=0, padx=10, pady=4, sticky='e')
        self.brand_var = tk.StringVar()
        cb = ttk.Combobox(self, textvariable=self.brand_var,
                          values=[b['brand_name'] for b in brands], state='readonly', width=52)
        cb.grid(row=0, column=1, padx=10, pady=4, sticky='w')
        if data:
            cur = next((b['brand_name'] for b in brands if b['id'] == data.get('brand_id')), '')
            self.brand_var.set(cur)

        self.vars: Dict[str, tk.StringVar] = {}
        for i, (key, label) in enumerate(fields, start=1):
            tk.Label(self, text=label, anchor='e', width=22).grid(row=i, column=0, padx=10, pady=4, sticky='e')
            v = tk.StringVar(value=data.get(key, '') if data else '')
            self.vars[key] = v
            tk.Entry(self, textvariable=v, width=60).grid(row=i, column=1, padx=10, pady=4, sticky='w')

        row = len(fields) + 1
        btn = tk.Frame(self)
        btn.grid(row=row, column=0, columnspan=2, pady=12)
        tk.Button(btn, text="저장", command=self._save,
                  bg='#e67e22', fg='white', relief=tk.FLAT, width=10).pack(side=tk.LEFT, padx=6)
        tk.Button(btn, text="취소", command=self.destroy,
                  relief=tk.FLAT, width=10).pack(side=tk.LEFT)

    def _save(self):
        brand_name = self.brand_var.get()
        brand_id   = next((b['id'] for b in self.brands if b['brand_name'] == brand_name), None)
        name       = self.vars['product_name'].get().strip()
        if not brand_id or not name:
            messagebox.showwarning("입력 오류", "브랜드와 상품명은 필수입니다.", parent=self)
            return
        data = {'brand_id': brand_id}
        data.update({k: v.get().strip() for k, v in self.vars.items()})
        if self.on_save:
            self.on_save(data)
        self.destroy()
