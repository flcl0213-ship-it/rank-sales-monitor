# -*- coding: utf-8 -*-
"""키워드 비교 팝업 — 네이버현황 탭에서 호출"""

import tkinter as tk
from tkinter import ttk
from datetime import date, timedelta
from collections import defaultdict

DAYS = 7


class KeywordCompareDialog(tk.Toplevel):
    def __init__(self, parent, product: dict):
        super().__init__(parent)
        pid   = product['id']
        title = f"키워드 비교  —  {product['brand_name']}  |  {product.get('model_name','')}"
        self.title(title)
        self.geometry("860x460")
        self.resizable(True, True)
        self._checked = set()   # 선택된 sub keyword_id

        today = date.today()
        self._date_strs  = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(DAYS)]
        self._date_labels = [(today - timedelta(days=i)).strftime('%m/%d').lstrip('0') for i in range(DAYS)]

        self._build()
        self._load(pid)

    def _build(self):
        # 안내
        tk.Label(self, text="※ 서브 키워드 행을 클릭하면 비교 선택 (최대 4개 / 초록색 강조)",
                 fg='#666', font=('맑은 고딕', 8)).pack(anchor='w', padx=10, pady=(6, 2))

        # 분석 바
        self.analysis_lbl = tk.Label(self, text="", bg='#eaf4fb', fg='#1a5276',
                                      font=('맑은 고딕', 9, 'bold'), anchor='w', pady=5)
        self.analysis_lbl.pack(fill=tk.X, padx=10)

        # 트리
        cols = ('check', 'type', 'keyword') + tuple(self._date_labels) + ('avg',)
        self.tree = ttk.Treeview(self, columns=cols, show='headings', height=16)

        self.tree.heading('check',   text='비교')
        self.tree.heading('type',    text='구분')
        self.tree.heading('keyword', text='키워드')
        self.tree.heading('avg',     text='평균순위')
        self.tree.column('check',   width=45,  anchor=tk.CENTER)
        self.tree.column('type',    width=55,  anchor=tk.CENTER)
        self.tree.column('keyword', width=230, anchor=tk.W)
        self.tree.column('avg',     width=70,  anchor=tk.CENTER)
        for d in self._date_labels:
            self.tree.heading(d, text=d)
            self.tree.column(d, width=52, anchor=tk.CENTER)

        self.tree.tag_configure('main_kw',    background='#d6eaf8', font=('맑은 고딕', 9, 'bold'))
        self.tree.tag_configure('checked_kw', background='#d5f5e3')
        self.tree.tag_configure('sub_kw',     background='#ffffff')

        sb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=6)
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=6, padx=(0, 6))

        self.tree.bind('<Button-1>', self._on_click)

    def _load(self, pid: int):
        from database.db_manager import get_keywords, get_conn

        all_kws   = get_keywords(pid, 'naver')
        main_kws  = [k for k in all_kws if k['type'] == 'main']
        sub_kws   = [k for k in all_kws if k['type'] == 'sub']

        conn = get_conn()
        rows = conn.execute("""
            SELECT keyword_id, rank, checked_date FROM rank_history
            WHERE naver_product_id=? AND checked_date >= date('now', ? || ' days')
        """, (pid, f'-{DAYS}')).fetchall()
        conn.close()

        rank_map = defaultdict(dict)
        for r in rows:
            rank_map[r['keyword_id']][r['checked_date']] = r['rank']

        self._rank_map = rank_map
        self._main_kws = main_kws
        self._sub_kws  = sub_kws
        self._redraw()

    def _redraw(self):
        self.tree.delete(*self.tree.get_children())
        self._kw_avgs = {}

        def _insert(kw, tag):
            kid   = kw['id']
            ranks = [self._rank_map[kid].get(ds, 0) for ds in self._date_strs]
            valid = [r for r in ranks if r > 0]
            avg   = sum(valid) / len(valid) if valid else None
            self._kw_avgs[kid] = (kw['keyword'], avg)

            vals  = [str(r) if r > 0 else '-' for r in ranks]
            avg_s = f"{avg:.1f}" if avg else "-"
            check = '★' if tag == 'main_kw' else ('✓' if kid in self._checked else '')
            iid   = f'main_{kid}' if tag == 'main_kw' else str(kid)
            self.tree.insert('', tk.END, iid=iid, tags=(tag,),
                             values=(check, '대표' if tag=='main_kw' else '서브',
                                     kw['keyword']) + tuple(vals) + (avg_s,))

        for kw in self._main_kws:
            _insert(kw, 'main_kw')
        for kw in self._sub_kws:
            tag = 'checked_kw' if kw['id'] in self._checked else 'sub_kw'
            _insert(kw, tag)

        self._update_analysis()

    def _on_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != 'cell':
            return
        iid = self.tree.identify_row(event.y)
        if not iid or iid.startswith('main_'):
            return
        kid = int(iid)
        if kid in self._checked:
            self._checked.discard(kid)
        else:
            if len(self._checked) >= 4:
                return
            self._checked.add(kid)
        self._redraw()

    def _update_analysis(self):
        parts = []
        # 대표 키워드 평균
        for kid, (kw_name, avg) in self._kw_avgs.items():
            iid = f'main_{kid}'
            if self.tree.exists(iid):
                parts.append(('★ 대표', kw_name, avg))
        # 선택된 서브
        for kid in self._checked:
            if kid in self._kw_avgs:
                kw_name, avg = self._kw_avgs[kid]
                parts.append(('서브', kw_name, avg))

        if not parts:
            self.analysis_lbl.config(text="")
            return

        main_avg = parts[0][2] if parts else None
        msgs = []
        for i, (gtype, name, avg) in enumerate(parts):
            if avg is None:
                msgs.append(f"{name[:12]}: 데이터 없음")
            elif i == 0:
                msgs.append(f"★ 대표 [{name[:15]}] 평균 {avg:.1f}위")
            else:
                diff_txt = ""
                if main_avg:
                    d = avg - main_avg
                    diff_txt = f"  (대표보다 {'▼' if d > 0 else '▲'}{abs(d):.1f}위)"
                msgs.append(f"[{name[:15]}] 평균 {avg:.1f}위{diff_txt}")

        self.analysis_lbl.config(text="   " + "     |     ".join(msgs))
