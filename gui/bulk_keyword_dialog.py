# -*- coding: utf-8 -*-
"""대표 키워드 일괄 등록 다이얼로그"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading


def _db_suggest(keyword: str):
    """DB에 등록된 키워드 중 유사어 반환"""
    try:
        from database.db_manager import get_conn
        conn = get_conn()
        rows = conn.execute(
            "SELECT DISTINCT keyword FROM keywords WHERE keyword LIKE ? AND status='active' ORDER BY keyword LIMIT 15",
            (f'%{keyword}%',)
        ).fetchall()
        conn.close()
        return [r['keyword'] for r in rows]
    except Exception:
        return []


class _AutoEntry(tk.Frame):
    """자동완성 Entry 위젯"""
    def __init__(self, parent, width=22, **kw):
        super().__init__(parent, **kw)
        self.var       = tk.StringVar()
        self._timer    = None
        self._popup    = None
        self._suppress = False

        self.entry = tk.Entry(self, textvariable=self.var, width=width,
                              font=('맑은 고딕', 9))
        self.entry.pack(fill=tk.X)
        self.var.trace_add('write', self._on_change)
        self.entry.bind('<FocusOut>', self._close_popup)
        self.entry.bind('<Escape>',  lambda e: self._close_popup())
        self.entry.bind('<Down>',    self._focus_popup)

    def get(self): return self.var.get().strip()
    def set(self, v):
        self._suppress = True
        self.var.set(v)
        self._suppress = False

    def _on_change(self, *_):
        if self._suppress:
            return
        if self._timer:
            self.after_cancel(self._timer)
        kw = self.var.get().strip()
        if len(kw) < 2:
            self._close_popup()
            return
        self._timer = self.after(200, lambda: self._fetch(kw))

    def _fetch(self, kw):
        suggestions = _db_suggest(kw)
        self._show_popup(suggestions)

    def _show_popup(self, suggestions):
        self._close_popup()
        if not suggestions:
            return
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        w = max(self.entry.winfo_width(), 180)

        self._popup = tk.Toplevel(self)
        self._popup.wm_overrideredirect(True)
        self._popup.geometry(f"{w}x{min(len(suggestions)*22, 200)}+{x}+{y}")
        self._popup.attributes('-topmost', True)

        lb = tk.Listbox(self._popup, font=('맑은 고딕', 9),
                        selectbackground='#3498db', activestyle='none',
                        relief=tk.FLAT, bd=1)
        lb.pack(fill=tk.BOTH, expand=True)
        for s in suggestions:
            lb.insert(tk.END, s)

        lb.bind('<ButtonRelease-1>', lambda e: self._pick(lb))
        lb.bind('<Return>',          lambda e: self._pick(lb))
        lb.bind('<Escape>',          lambda e: self._close_popup())

    def _pick(self, lb):
        sel = lb.curselection()
        if sel:
            self.set(lb.get(sel[0]))
        self._close_popup()
        self.entry.focus_set()

    def _focus_popup(self, event=None):
        if self._popup:
            for w in self._popup.winfo_children():
                w.focus_set()
                if w.size() > 0:
                    w.selection_set(0)

    def _close_popup(self, event=None):
        if self._popup:
            self._popup.destroy()
            self._popup = None


class BulkKeywordDialog(tk.Toplevel):
    def __init__(self, parent, on_done=None):
        super().__init__(parent)
        self.title("대표 키워드 일괄 등록")
        self.geometry("800x560")
        self.resizable(True, True)
        self.grab_set()
        self.on_done = on_done
        self._rows   = []   # (product_dict, AutoEntry)

        self._build()
        self._load()

    def _build(self):
        # 상단: 필터
        top = tk.Frame(self, pady=6)
        top.pack(fill=tk.X, padx=10)

        tk.Label(top, text="브랜드 필터:").pack(side=tk.LEFT)
        self.filter_var = tk.StringVar(value='전체')
        self.filter_cb  = ttk.Combobox(top, textvariable=self.filter_var,
                                        width=16, state='readonly')
        self.filter_cb.pack(side=tk.LEFT, padx=6)
        self.filter_cb.bind('<<ComboboxSelected>>', lambda e: self._load())

        tk.Label(top, text="  ※ 2자 이상 입력하면 등록된 키워드 중 유사어가 표시됩니다",
                 fg='#777', font=('맑은 고딕', 8)).pack(side=tk.LEFT)

        # 테이블 헤더
        hdr = tk.Frame(self, bg='#2c3e50')
        hdr.pack(fill=tk.X, padx=10)
        for txt, w in [('브랜드', 90), ('모델명', 90), ('상품명', 260), ('대표 키워드 입력', 200)]:
            tk.Label(hdr, text=txt, bg='#2c3e50', fg='white',
                     width=w//7, anchor='w',
                     font=('맑은 고딕', 9, 'bold')).pack(side=tk.LEFT, padx=4, pady=3)

        # 스크롤 영역
        container = tk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=10)

        canvas = tk.Canvas(container, highlightthickness=0)
        sb = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        self.inner = tk.Frame(canvas)
        self.inner.bind('<Configure>',
                        lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=self.inner, anchor='nw')
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        canvas.bind_all('<MouseWheel>',
                        lambda e: canvas.yview_scroll(-1*(e.delta//120), 'units'))

        # 하단 버튼
        btn_frame = tk.Frame(self, pady=8)
        btn_frame.pack()
        tk.Button(btn_frame, text="일괄 저장", command=self._save,
                  bg='#27ae60', fg='white', relief=tk.FLAT,
                  padx=16, font=('맑은 고딕', 10)).pack(side=tk.LEFT, padx=8)
        tk.Button(btn_frame, text="닫기", command=self.destroy,
                  relief=tk.FLAT, padx=12).pack(side=tk.LEFT)

    def _load(self):
        from database.db_manager import get_naver_products, get_all_brands, get_keywords

        # 브랜드 필터 목록 갱신
        brands = get_all_brands()
        brand_names = ['전체'] + [b['brand_name'] for b in brands]
        self.filter_cb['values'] = brand_names

        f = self.filter_var.get()

        # 기존 행 제거
        for w in self.inner.winfo_children():
            w.destroy()
        self._rows.clear()

        products = get_naver_products()
        for i, p in enumerate(products):
            if f != '전체' and p['brand_name'] != f:
                continue

            # 기존 main 키워드
            existing = next((k['keyword'] for k in get_keywords(p['id'])
                             if k['type'] == 'main'), '')

            bg = '#ffffff' if i % 2 == 0 else '#f5f5f5'
            row = tk.Frame(self.inner, bg=bg)
            row.pack(fill=tk.X)

            tk.Label(row, text=p['brand_name'], bg=bg, width=13,
                     anchor='w', font=('맑은 고딕', 9)).pack(side=tk.LEFT, padx=4)
            tk.Label(row, text=p.get('model_name', ''), bg=bg, width=13,
                     anchor='w', font=('맑은 고딕', 9)).pack(side=tk.LEFT)
            name = p['product_name']
            tk.Label(row, text=name[:30] + ('…' if len(name) > 30 else ''),
                     bg=bg, width=38, anchor='w',
                     font=('맑은 고딕', 9)).pack(side=tk.LEFT)

            ae = _AutoEntry(row, width=24)
            ae.pack(side=tk.LEFT, padx=4, pady=2)
            if existing:
                ae.set(existing)

            self._rows.append((p, ae))

    def _save(self):
        from database.db_manager import get_keywords, add_keyword, delete_keyword

        saved = skipped = 0
        for p, ae in self._rows:
            kw = ae.get()
            if not kw:
                continue
            existing_main = [k for k in get_keywords(p['id']) if k['type'] == 'main']
            if existing_main:
                if existing_main[0]['keyword'] == kw:
                    skipped += 1
                    continue
                delete_keyword(existing_main[0]['id'])
            add_keyword(p['id'], kw, ktype='main', platform='naver')
            saved += 1

        messagebox.showinfo("완료",
            f"저장: {saved}개 / 변경없음: {skipped}개", parent=self)
        if self.on_done:
            self.on_done()
