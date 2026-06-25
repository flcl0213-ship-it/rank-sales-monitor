# -*- coding: utf-8 -*-
"""
메인 창 — 탭 구조
  탭1: 네이버 현황 (순위 + 옵션별 판매)
  탭2: 쿠팡 현황 (상품별 판매)
  탭3: 브랜드 관리
  탭4: 상품 관리 (네이버 / 쿠팡 분리)
"""

import tkinter as tk
from tkinter import ttk
import threading
import webbrowser
from datetime import date, timedelta
from collections import defaultdict

from database.db_manager import (
    get_all_brands,
    get_naver_products, get_coupang_products,
    get_keywords,
    get_naver_ranks_for_display, get_sub_ranks_for_display,
    get_coupang_ranks_for_display,
    get_naver_daily_sales, get_coupang_daily_sales,
    get_traffic_columns, update_traffic_column,
    save_traffic_data, get_all_traffic_data,
)
from gui.brand_dialog import BrandDialog
from gui.product_dialog import NaverProductDialog, CoupangProductDialog

DAYS = 7


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.company_var = tk.StringVar(value='전체')
        self.brand_var   = tk.StringVar(value='전체')

        self._build_toolbar()
        self._build_tabs()
        self.refresh_naver()

    # ─── 툴바 ────────────────────────────────────────
    def _build_toolbar(self):
        bar = tk.Frame(self.root, bg='#2c3e50', pady=6)
        bar.pack(fill=tk.X)

        tk.Label(bar, text="회사", bg='#2c3e50', fg='white',
                 font=('맑은 고딕', 10)).pack(side=tk.LEFT, padx=(12, 4))
        self.company_cb = ttk.Combobox(bar, textvariable=self.company_var, width=10, state='readonly')
        self.company_cb.pack(side=tk.LEFT)
        self.company_cb.bind('<<ComboboxSelected>>', self._on_company_change)

        tk.Label(bar, text="브랜드", bg='#2c3e50', fg='white',
                 font=('맑은 고딕', 10)).pack(side=tk.LEFT, padx=(10, 4))
        self.brand_cb = ttk.Combobox(bar, textvariable=self.brand_var, width=14, state='readonly')
        self.brand_cb.pack(side=tk.LEFT)
        self._reload_company_filter()

        tk.Button(bar, text="조회", command=self._refresh_current_tab,
                  bg='#3498db', fg='white', relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=8)
        tk.Button(bar, text="네이버 체크", command=lambda: self._run_check('naver_rank'),
                  bg='#27ae60', fg='white', relief=tk.FLAT, padx=10).pack(side=tk.LEFT)
        tk.Button(bar, text="쿠팡 체크", command=lambda: self._run_check('coupang_rank'),
                  bg='#e67e22', fg='white', relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=4)
        tk.Button(bar, text="인쇄", command=self._print_current,
                  bg='#8e44ad', fg='white', relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=8)

        self.status_lbl = tk.Label(bar, text="", bg='#2c3e50', fg='#aaa',
                                   font=('맑은 고딕', 9))
        self.status_lbl.pack(side=tk.RIGHT, padx=12)

    # ─── 탭 ──────────────────────────────────────────
    def _build_tabs(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.tab_naver    = tk.Frame(self.nb, bg='white')
        self.tab_coupang  = tk.Frame(self.nb, bg='white')
        self.tab_sub      = tk.Frame(self.nb, bg='white')
        self.tab_brands   = tk.Frame(self.nb, bg='white')
        self.tab_products = tk.Frame(self.nb, bg='white')

        self.nb.add(self.tab_naver,    text='  네이버 현황  ')
        self.nb.add(self.tab_coupang,  text='  쿠팡 현황  ')
        self.nb.add(self.tab_sub,      text='  서브 키워드  ')
        self.nb.add(self.tab_brands,   text='  브랜드 관리  ')
        self.nb.add(self.tab_products, text='  상품 관리  ')

        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

        self._build_naver_tab()
        self._build_coupang_tab()
        self._build_sub_tab()
        self._build_brand_tab()
        self._build_product_tab()

    # ─── 네이버 현황 탭 ──────────────────────────────
    def _build_naver_tab(self):
        frame = self.tab_naver
        today = date.today()
        self.naver_date_cols = [
            (today - timedelta(days=i)).strftime('%m/%d').lstrip('0')
            for i in range(DAYS)
        ]

        self.traffic_col_names = get_traffic_columns()  # ['','','','']
        traffic_ids = ('traffic_0', 'traffic_1', 'traffic_2', 'traffic_3')

        cols = ('brand', 'model', 'product', 'link') + tuple(self.naver_date_cols) + ('summary', 'sales', 'compare') + traffic_ids
        self.naver_tree = ttk.Treeview(frame, columns=cols, show='headings', height=25)

        col_widths = {
            'brand': 70, 'model': 80, 'product': 160,
            'link': 40, 'summary': 90, 'sales': 100, 'compare': 55,
            'traffic_0': 70, 'traffic_1': 70, 'traffic_2': 70, 'traffic_3': 70,
        }
        self.naver_tree.heading('brand',   text='브랜드')
        self.naver_tree.heading('model',   text='모델명')
        self.naver_tree.heading('product', text='상품명')
        self.naver_tree.heading('link',    text='링크')
        self.naver_tree.heading('summary', text='순위평균')
        self.naver_tree.heading('sales',   text='판매/전일대비')
        self.naver_tree.heading('compare', text='키워드비교')

        for i, tid in enumerate(traffic_ids):
            name = self.traffic_col_names[i] or f'트래픽{i+1}'
            self.naver_tree.heading(tid, text=name,
                                    command=lambda idx=i: self._rename_traffic_col(idx))

        for col in cols:
            w = col_widths.get(col, 60)
            self.naver_tree.column(col, width=w, minwidth=40, anchor=tk.CENTER)
        self.naver_tree.column('brand',   anchor=tk.W)
        self.naver_tree.column('model',   anchor=tk.W)
        self.naver_tree.column('product', anchor=tk.W)

        for d in self.naver_date_cols:
            self.naver_tree.heading(d, text=d)

        self.naver_tree.tag_configure('rank_row',  background='#eaf4fb')
        self.naver_tree.tag_configure('total_row', background='#ecf0f1',
                                      font=('맑은 고딕', 9, 'bold'))
        self.naver_tree.tag_configure('up',   foreground='#c0392b')
        self.naver_tree.tag_configure('down', foreground='#2980b9')

        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL,   command=self.naver_tree.yview)
        sx = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.naver_tree.xview)
        self.naver_tree.configure(yscrollcommand=sb.set, xscrollcommand=sx.set)
        self.naver_tree.grid(row=0, column=0, sticky='nsew')
        sb.grid(row=0, column=1, sticky='ns')
        sx.grid(row=1, column=0, sticky='ew')
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.naver_tree.bind('<Button-1>',   self._on_naver_click)
        self.naver_tree.bind('<Motion>',     self._on_naver_motion)
        self.naver_tree.bind('<Double-1>',   self._on_traffic_double_click)
        self.naver_tree.tag_configure('flash', background='#f39c12')

    def refresh_naver(self):
        tree = self.naver_tree
        tree.delete(*tree.get_children())

        company_filter = self.company_var.get()
        brand_filter   = self.brand_var.get()
        today          = date.today()
        date_strs      = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(DAYS)]

        rank_rows    = get_naver_ranks_for_display(DAYS)
        sales_rows   = get_naver_daily_sales(DAYS)
        traffic_data = get_all_traffic_data()  # {pid: {col_idx: value}}

        def _match(row):
            if company_filter != '전체' and row.get('company_name') != company_filter:
                return False
            if brand_filter != '전체' and row['brand_name'] != brand_filter:
                return False
            return True

        # 순위 데이터 정리
        rank_data: dict = defaultdict(dict)   # (pid, kid) → date → rank
        product_info: dict = {}
        for r in rank_rows:
            if not _match(r):
                continue
            key = (r['product_id'], r['keyword_id'])
            if r['checked_date']:
                rank_data[key][r['checked_date']] = r['rank']
            product_info[r['product_id']] = r

        # 판매 데이터 정리: pid → option → date → qty
        sales_data: dict = defaultdict(lambda: defaultdict(dict))
        for s in sales_rows:
            if not _match(s):
                continue
            pid = s['product_id']
            opt = s['option_name'] or '(옵션없음)'
            sales_data[pid][opt][s['order_date']] = s['total_qty']

        # 그룹화
        grouped: dict = defaultdict(lambda: defaultdict(list))
        for r in rank_rows:
            if not _match(r):
                continue
            grouped[r['brand_name']][r['product_id']].append(r)

        day_totals = defaultdict(int)

        for brand_name, pid_map in grouped.items():
            for pid, rows in pid_map.items():
                if not rows:
                    continue
                sample = rows[0]
                model_name   = sample.get('model_name', '')
                product_name = sample['product_name']
                url          = sample.get('url_naver', '')
                kid          = sample['keyword_id']

                # 순위 행
                rank_vals = []
                prev_rank = None
                for ds in reversed(date_strs):
                    r = rank_data.get((pid, kid), {}).get(ds)
                    if r is None:
                        rank_vals.insert(0, '-')
                    elif r == 0:
                        rank_vals.insert(0, '100↓')
                    else:
                        if prev_rank is None:
                            rank_vals.insert(0, str(r))
                        elif r < prev_rank:
                            rank_vals.insert(0, f'{r}▲')
                        elif r > prev_rank:
                            rank_vals.insert(0, f'{r}▼')
                        else:
                            rank_vals.insert(0, f'{r}-')
                        prev_rank = r
                    if prev_rank is None and r:
                        prev_rank = r

                valid = [rank_data.get((pid, kid), {}).get(ds, 0) for ds in date_strs]
                valid = [x for x in valid if x and x > 0]
                summary_rank = f"평균 {sum(valid)/len(valid):.1f}위" if valid else "-"

                # 판매 전일대비 계산
                options = sales_data.get(pid, {})
                today_qty = sum(opts.get(date_strs[0], 0) for opts in options.values())
                yest_qty  = sum(opts.get(date_strs[1], 0) for opts in options.values()) if len(date_strs) > 1 else 0
                week_total = sum(
                    sum(opts.get(ds, 0) for opts in options.values())
                    for ds in date_strs
                )
                for ds in date_strs:
                    day_totals[ds] += sum(opts.get(ds, 0) for opts in options.values())

                diff = today_qty - yest_qty
                if diff > 0:
                    sales_txt = f"{today_qty}개 ▲{diff}"
                elif diff < 0:
                    sales_txt = f"{today_qty}개 ▼{abs(diff)}"
                else:
                    sales_txt = f"{today_qty}개"

                t_vals = traffic_data.get(pid, {})
                traffic_vals = tuple(t_vals.get(i, '') or '·' for i in range(4))
                tree.insert('', tk.END,
                            values=(brand_name, model_name, product_name,
                                    '🔗' if url else '') + tuple(rank_vals) + (summary_rank, sales_txt, '🔍비교') + traffic_vals,
                            tags=('rank_row',), iid=f'nrank_{pid}_{kid}')

        # 총합계 행
        total_vals = ('', '', '[ 판매 총합계 ]', '') + tuple(
            str(day_totals.get(ds, 0)) for ds in date_strs
        ) + ('', f"{sum(day_totals.values())}개", '', '', '', '', '')
        tree.insert('', tk.END, values=total_vals, tags=('total_row',))

        self.status_lbl.config(text=f"갱신: {date.today()} | 네이버 {len(product_info)}개 상품")

    # ─── 쿠팡 현황 탭 ────────────────────────────────
    def _build_coupang_tab(self):
        frame = self.tab_coupang
        today = date.today()
        self.coupang_date_cols = [
            (today - timedelta(days=i)).strftime('%m/%d').lstrip('0')
            for i in range(DAYS)
        ]

        cols = ('brand', 'model', 'product', 'keyword', 'link') + tuple(self.coupang_date_cols) + ('summary',)
        self.coupang_tree = ttk.Treeview(frame, columns=cols, show='headings', height=25)

        col_widths = {'brand': 70, 'model': 80, 'product': 200, 'keyword': 130, 'link': 40, 'summary': 70}
        self.coupang_tree.heading('brand',   text='브랜드')
        self.coupang_tree.heading('model',   text='모델명')
        self.coupang_tree.heading('product', text='상품명')
        self.coupang_tree.heading('keyword', text='대표키워드')
        self.coupang_tree.heading('link',    text='링크')
        self.coupang_tree.heading('summary', text='순위평균')

        for col in cols:
            w = col_widths.get(col, 55)
            self.coupang_tree.column(col, width=w, minwidth=30, anchor=tk.CENTER)
        self.coupang_tree.column('brand',   anchor=tk.W)
        self.coupang_tree.column('model',   anchor=tk.W)
        self.coupang_tree.column('product', anchor=tk.W)
        self.coupang_tree.column('keyword', anchor=tk.W)

        for d in self.coupang_date_cols:
            self.coupang_tree.heading(d, text=d)

        self.coupang_tree.tag_configure('rank_row',  background='#fef9e7')
        self.coupang_tree.tag_configure('total_row', background='#ecf0f1',
                                        font=('맑은 고딕', 9, 'bold'))
        self.coupang_tree.tag_configure('up',   foreground='#c0392b')
        self.coupang_tree.tag_configure('down', foreground='#2980b9')

        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL,   command=self.coupang_tree.yview)
        sx = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.coupang_tree.xview)
        self.coupang_tree.configure(yscrollcommand=sb.set, xscrollcommand=sx.set)
        self.coupang_tree.grid(row=0, column=0, sticky='nsew')
        sb.grid(row=0, column=1, sticky='ns')
        sx.grid(row=1, column=0, sticky='ew')
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.coupang_tree.bind('<Double-1>', self._on_coupang_link_click)

    def refresh_coupang(self):
        tree = self.coupang_tree
        tree.delete(*tree.get_children())

        company_filter = self.company_var.get()
        brand_filter   = self.brand_var.get()
        today          = date.today()
        date_strs      = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(DAYS)]

        rank_rows = get_coupang_ranks_for_display(DAYS)

        def _match(row):
            if company_filter != '전체' and row.get('company_name') != company_filter:
                return False
            if brand_filter != '전체' and row['brand_name'] != brand_filter:
                return False
            return True

        # (pid, kid) → date → rank
        rank_data: dict = defaultdict(dict)
        product_info: dict = {}
        for r in rank_rows:
            if not _match(r):
                continue
            key = (r['product_id'], r['keyword_id'])
            if r.get('checked_date') and r.get('rank') is not None:
                rank_data[key][r['checked_date']] = r['rank']
            if key not in product_info:
                product_info[key] = r

        iid_row = 0
        for key, info in product_info.items():
            pid  = info['product_id']
            url  = info.get('url_coupang', '')
            kw   = info.get('keyword', '')

            rank_vals = []
            valid_ranks = []
            for ds in date_strs:
                r = rank_data[key].get(ds)
                if r:
                    rank_vals.append(str(r))
                    valid_ranks.append(r)
                else:
                    rank_vals.append('-')

            avg = f'{sum(valid_ranks)/len(valid_ranks):.1f}위' if valid_ranks else '-'

            tree.insert('', tk.END,
                        values=(info['brand_name'], info.get('model_name', ''),
                                info['product_name'], kw,
                                '🔗' if url else '') + tuple(rank_vals) + (avg,),
                        tags=('rank_row',), iid=f'cpr_{iid_row}_{pid}')
            iid_row += 1

        cnt = len(product_info)
        if cnt == 0:
            tree.insert('', tk.END, values=('쿠팡 대표 키워드를 등록하면 순위가 표시됩니다.', '', '', '', '') + ('-',) * DAYS + ('-',))
        self.status_lbl.config(text=f"갱신: {date.today()} | 쿠팡 {cnt}개 키워드")

    # ─── 서브 키워드 탭 ──────────────────────────────
    def _build_sub_tab(self):
        frame = self.tab_sub
        today = date.today()
        self.sub_date_cols = [
            (today - timedelta(days=i)).strftime('%m/%d').lstrip('0')
            for i in range(DAYS)
        ]
        self._sub_checked   = set()   # 체크된 keyword_id
        self._sub_prod_map  = {}      # label → product dict

        # 상단: 상품 선택
        top = tk.Frame(frame, pady=6)
        top.pack(fill=tk.X, padx=8)
        tk.Label(top, text="상품 선택:", font=('맑은 고딕', 9)).pack(side=tk.LEFT)
        self.sub_prod_var = tk.StringVar()
        self.sub_prod_cb  = ttk.Combobox(top, textvariable=self.sub_prod_var,
                                          width=55, state='readonly')
        self.sub_prod_cb.pack(side=tk.LEFT, padx=6)
        self.sub_prod_cb.bind('<<ComboboxSelected>>', lambda e: self.refresh_sub())
        tk.Label(top, text="※ 서브 키워드 행 클릭으로 비교 선택 (최대 4개)",
                 fg='#888', font=('맑은 고딕', 8)).pack(side=tk.LEFT)

        # 분석 메시지
        self.sub_analysis = tk.Label(frame, text="", fg='#2c3e50',
                                      font=('맑은 고딕', 9, 'bold'), anchor='w',
                                      bg='#eaf4fb', pady=4)
        self.sub_analysis.pack(fill=tk.X, padx=8)

        # 테이블
        cols = ('check', 'type', 'keyword') + tuple(self.sub_date_cols) + ('avg',)
        self.sub_tree = ttk.Treeview(frame, columns=cols, show='headings', height=20)

        self.sub_tree.heading('check',   text='비교')
        self.sub_tree.heading('type',    text='구분')
        self.sub_tree.heading('keyword', text='키워드')
        self.sub_tree.heading('avg',     text='평균순위')
        self.sub_tree.column('check',   width=45,  anchor=tk.CENTER)
        self.sub_tree.column('type',    width=55,  anchor=tk.CENTER)
        self.sub_tree.column('keyword', width=220, anchor=tk.W)
        self.sub_tree.column('avg',     width=70,  anchor=tk.CENTER)
        for d in self.sub_date_cols:
            self.sub_tree.heading(d, text=d)
            self.sub_tree.column(d, width=52, anchor=tk.CENTER)

        self.sub_tree.tag_configure('main_kw',    background='#d6eaf8', font=('맑은 고딕', 9, 'bold'))
        self.sub_tree.tag_configure('checked_kw', background='#d5f5e3')
        self.sub_tree.tag_configure('sub_kw',     background='#ffffff')

        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL,   command=self.sub_tree.yview)
        sx = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.sub_tree.xview)
        self.sub_tree.configure(yscrollcommand=sb.set, xscrollcommand=sx.set)
        self.sub_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=4)
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

        self.sub_tree.bind('<Button-1>', self._on_sub_click)

    def _reload_sub_products(self):
        """서브키워드 탭 상품 목록 갱신"""
        prods = get_naver_products()
        self._sub_prod_map = {}
        for p in prods:
            label = f"{p['brand_name']}  |  {p.get('model_name','')[:12]}  |  {p['product_name'][:30]}"
            self._sub_prod_map[label] = p
        self.sub_prod_cb['values'] = list(self._sub_prod_map.keys())
        if self.sub_prod_var.get() not in self._sub_prod_map:
            first = next(iter(self._sub_prod_map), '')
            self.sub_prod_var.set(first)

    def _on_sub_click(self, event):
        region = self.sub_tree.identify_region(event.x, event.y)
        if region != 'cell':
            return
        iid = self.sub_tree.identify_row(event.y)
        if not iid or iid.startswith('main_'):
            return
        kid = int(iid)
        if kid in self._sub_checked:
            self._sub_checked.discard(kid)
        else:
            if len(self._sub_checked) >= 4:
                from tkinter import messagebox
                messagebox.showinfo("알림", "최대 4개까지 선택할 수 있습니다.", parent=self.root)
                return
            self._sub_checked.add(kid)
        self._redraw_sub()

    def _redraw_sub(self):
        """체크 상태 반영해서 트리 색상 갱신 + 분석"""
        for iid in self.sub_tree.get_children():
            if iid.startswith('main_'):
                continue
            kid = int(iid)
            tag = 'checked_kw' if kid in self._sub_checked else 'sub_kw'
            self.sub_tree.item(iid, tags=(tag,))
            check_txt = '✓' if kid in self._sub_checked else ''
            vals = list(self.sub_tree.item(iid, 'values'))
            vals[0] = check_txt
            self.sub_tree.item(iid, values=vals)
        self._update_sub_analysis()

    def _update_sub_analysis(self):
        """대표 vs 선택 서브키워드 분석 메시지"""
        if not hasattr(self, '_sub_rank_data'):
            self.sub_analysis.config(text="")
            return
        lines = []
        for kw_label, avgs in self._sub_rank_data.items():
            valid = [v for v in avgs if v > 0]
            avg   = sum(valid) / len(valid) if valid else None
            lines.append((kw_label, avg))

        if not lines:
            self.sub_analysis.config(text="")
            return

        main_line = lines[0] if lines else None
        checked_lines = [(lbl, avg) for lbl, avg in lines[1:]
                         if avg is not None]

        msg_parts = []
        if main_line and main_line[1]:
            msg_parts.append(f"대표: 평균 {main_line[1]:.1f}위")
        for lbl, avg in checked_lines:
            diff = ""
            if main_line and main_line[1] and avg:
                d = main_line[1] - avg
                diff = f" (대표 대비 {'▲' if d > 0 else '▼'}{abs(d):.1f})"
            msg_parts.append(f"{lbl[:15]}: 평균 {avg:.1f}위{diff}" if avg else f"{lbl[:15]}: 데이터 없음")

        self.sub_analysis.config(text="  " + "   |   ".join(msg_parts) if msg_parts else "")

    def refresh_sub(self):
        tree = self.sub_tree
        tree.delete(*tree.get_children())
        self._sub_rank_data = {}

        label = self.sub_prod_var.get()
        prod  = self._sub_prod_map.get(label)
        if not prod:
            return

        pid       = prod['id']
        today     = date.today()
        date_strs = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(DAYS)]

        # 키워드 목록 (main + sub)
        all_kws = get_keywords(pid)
        main_kws = [k for k in all_kws if k['type'] == 'main']
        sub_kws  = [k for k in all_kws if k['type'] == 'sub']

        # 순위 데이터
        from database.db_manager import get_conn
        conn = get_conn()
        rows = conn.execute("""
            SELECT keyword_id, rank, checked_date FROM rank_history
            WHERE naver_product_id=? AND checked_date >= date('now', ? || ' days')
            ORDER BY checked_date DESC
        """, (pid, f'-{DAYS}')).fetchall()
        conn.close()

        rank_map = defaultdict(dict)
        for r in rows:
            rank_map[r['keyword_id']][r['checked_date']] = r['rank']

        def _insert_row(kw, tag, iid_prefix):
            kid    = kw['id']
            ranks  = [rank_map[kid].get(ds, 0) for ds in date_strs]
            valid  = [r for r in ranks if r > 0]
            avg    = f"{sum(valid)/len(valid):.1f}" if valid else "-"
            vals   = [str(r) if r > 0 else '-' for r in ranks]
            check  = '★' if tag == 'main_kw' else ''
            iid    = f'{iid_prefix}_{kid}' if tag == 'main_kw' else str(kid)
            tree.insert('', tk.END, iid=iid, tags=(tag,),
                        values=(check, '대표' if tag == 'main_kw' else '서브',
                                kw['keyword']) + tuple(vals) + (avg,))
            self._sub_rank_data[kw['keyword']] = ranks

        for kw in main_kws:
            _insert_row(kw, 'main_kw', 'main')
        for kw in sub_kws:
            _insert_row(kw, 'checked_kw' if kw['id'] in self._sub_checked else 'sub_kw', 'sub')

        self._update_sub_analysis()

    # ─── 브랜드 관리 탭 ──────────────────────────────
    def _build_brand_tab(self):
        frame = self.tab_brands

        btn_frame = tk.Frame(frame, pady=6)
        btn_frame.pack(fill=tk.X, padx=8)
        tk.Button(btn_frame, text="+ 브랜드 추가", command=self._add_brand,
                  bg='#2c3e50', fg='white', relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="수정", command=self._edit_brand,
                  bg='#7f8c8d', fg='white', relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="삭제", command=self._del_brand,
                  bg='#c0392b', fg='white', relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=4)

        cols = ('id', 'company', 'brand', 'naver_id', 'coupang_vendor', 'status')
        self.brand_tree = ttk.Treeview(frame, columns=cols, show='headings', height=20)
        self.brand_tree.heading('id',             text='ID')
        self.brand_tree.heading('company',        text='회사명')
        self.brand_tree.heading('brand',          text='브랜드명')
        self.brand_tree.heading('naver_id',       text='네이버 판매자ID')
        self.brand_tree.heading('coupang_vendor', text='쿠팡 VendorID')
        self.brand_tree.heading('status',         text='상태')
        self.brand_tree.column('id',             width=40)
        self.brand_tree.column('company',        width=120)
        self.brand_tree.column('brand',          width=100)
        self.brand_tree.column('naver_id',       width=150)
        self.brand_tree.column('coupang_vendor', width=120)
        self.brand_tree.column('status',         width=70)

        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.brand_tree.yview)
        self.brand_tree.configure(yscrollcommand=sb.set)
        self.brand_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.refresh_brands()

    def refresh_brands(self):
        tree = self.brand_tree
        tree.delete(*tree.get_children())
        for b in get_all_brands():
            tree.insert('', tk.END, iid=str(b['id']), values=(
                b['id'], b['company_name'], b['brand_name'],
                b['naver_seller_id'], b['coupang_vendor_id'], b['status'],
            ))

    def _add_brand(self):
        BrandDialog(self.root, on_save=lambda d: self._save_brand(d))

    def _edit_brand(self):
        sel = self.brand_tree.selection()
        if not sel:
            return
        bid = int(sel[0])
        brands = {b['id']: b for b in get_all_brands()}
        if bid in brands:
            BrandDialog(self.root, data=brands[bid], on_save=lambda d: self._update_brand(bid, d))

    def _save_brand(self, data):
        from database.db_manager import add_brand
        add_brand(data)
        self.refresh_brands()
        self._reload_brand_filter()

    def _update_brand(self, bid, data):
        from database.db_manager import update_brand
        update_brand(bid, data)
        self.refresh_brands()
        self._reload_brand_filter()

    def _del_brand(self):
        sel = self.brand_tree.selection()
        if not sel:
            return
        from tkinter import messagebox
        if messagebox.askyesno("삭제", "선택한 브랜드를 비활성화 하시겠습니까?"):
            from database.db_manager import delete_brand
            delete_brand(int(sel[0]))
            self.refresh_brands()

    # ─── 상품 관리 탭 ────────────────────────────────
    def _build_product_tab(self):
        frame = self.tab_products

        # 네이버 / 쿠팡 서브탭
        sub_nb = ttk.Notebook(frame)
        sub_nb.pack(fill=tk.BOTH, expand=True)

        self.tab_naver_prod   = tk.Frame(sub_nb, bg='white')
        self.tab_coupang_prod = tk.Frame(sub_nb, bg='white')
        sub_nb.add(self.tab_naver_prod,   text='  네이버 상품  ')
        sub_nb.add(self.tab_coupang_prod, text='  쿠팡 상품  ')

        self._build_naver_product_tab()
        self._build_coupang_product_tab()

    def _build_naver_product_tab(self):
        frame = self.tab_naver_prod

        btn_frame = tk.Frame(frame, pady=6)
        btn_frame.pack(fill=tk.X, padx=8)
        tk.Button(btn_frame, text="+ 상품 추가", command=self._add_naver_product,
                  bg='#2c3e50', fg='white', relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="수정", command=self._edit_naver_product,
                  bg='#7f8c8d', fg='white', relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="키워드 관리", command=self._manage_keywords,
                  bg='#2980b9', fg='white', relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="키워드 일괄등록", command=self._bulk_keywords,
                  bg='#8e44ad', fg='white', relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="엑셀 일괄등록", command=self._import_excel_naver,
                  bg='#27ae60', fg='white', relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=4)

        tree_frame = tk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        cols = ('brand', 'model', 'product', 'url', 'keywords')
        self.naver_prod_tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=20)
        headers = {'brand':'브랜드', 'model':'모델명', 'product':'상품명',
                   'url':'네이버URL', 'keywords':'키워드수'}
        widths  = {'brand':90, 'model':110, 'product':220, 'url':260, 'keywords':70}
        for col in cols:
            self.naver_prod_tree.heading(col, text=headers[col])
            self.naver_prod_tree.column(col, width=widths[col])

        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,   command=self.naver_prod_tree.yview)
        sx = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.naver_prod_tree.xview)
        self.naver_prod_tree.configure(yscrollcommand=sb.set, xscrollcommand=sx.set)
        self.naver_prod_tree.grid(row=0, column=0, sticky='nsew')
        sb.grid(row=0, column=1, sticky='ns')
        sx.grid(row=1, column=0, sticky='ew')
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        self.refresh_naver_products()

    def _build_coupang_product_tab(self):
        frame = self.tab_coupang_prod

        btn_frame = tk.Frame(frame, pady=6)
        btn_frame.pack(fill=tk.X, padx=8)
        tk.Button(btn_frame, text="+ 상품 추가", command=self._add_coupang_product,
                  bg='#e67e22', fg='white', relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="수정", command=self._edit_coupang_product,
                  bg='#7f8c8d', fg='white', relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="키워드 관리", command=self._manage_coupang_keywords,
                  bg='#2980b9', fg='white', relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="키워드 일괄등록", command=self._bulk_coupang_keywords,
                  bg='#8e44ad', fg='white', relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="엑셀 일괄등록", command=self._import_excel,
                  bg='#27ae60', fg='white', relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=4)

        tree_frame = tk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        cols = ('id', 'brand', 'model', 'product', 'coupang_id', 'url')
        self.coupang_prod_tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=20)
        headers = {'id':'ID', 'brand':'브랜드', 'model':'모델명', 'product':'상품명(옵션포함)', 'coupang_id':'쿠팡상품ID', 'url':'쿠팡URL'}
        widths  = {'id':40, 'brand':80, 'model':100, 'product':320, 'coupang_id':100, 'url':220}
        for col in cols:
            self.coupang_prod_tree.heading(col, text=headers[col])
            self.coupang_prod_tree.column(col, width=widths[col])

        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,   command=self.coupang_prod_tree.yview)
        sx = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.coupang_prod_tree.xview)
        self.coupang_prod_tree.configure(yscrollcommand=sb.set, xscrollcommand=sx.set)
        self.coupang_prod_tree.grid(row=0, column=0, sticky='nsew')
        sb.grid(row=0, column=1, sticky='ns')
        sx.grid(row=1, column=0, sticky='ew')
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        self.refresh_coupang_products()

    def refresh_naver_products(self):
        tree = self.naver_prod_tree
        tree.delete(*tree.get_children())
        for p in get_naver_products():
            kws = get_keywords(p['id'])
            url = p['url_naver']
            tree.insert('', tk.END, iid=str(p['id']), values=(
                p['brand_name'], p.get('model_name', ''), p['product_name'],
                url[:55] + '...' if len(url) > 55 else url,
                f"{len(kws)}개",
            ))

    def refresh_coupang_products(self):
        tree = self.coupang_prod_tree
        tree.delete(*tree.get_children())
        for p in get_coupang_products():
            url = p['url_coupang']
            tree.insert('', tk.END, iid=str(p['id']), values=(
                p['id'], p['brand_name'], p.get('model_name', ''), p['product_name'],
                p.get('coupang_product_id', ''),
                url[:50] + '...' if len(url) > 50 else url,
            ))

    def _add_naver_product(self):
        NaverProductDialog(self.root, brands=get_all_brands(), on_save=self._save_naver_product)

    def _edit_naver_product(self):
        sel = self.naver_prod_tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        prods = {p['id']: p for p in get_naver_products()}
        if pid in prods:
            NaverProductDialog(self.root, brands=get_all_brands(), data=prods[pid],
                               on_save=lambda d: self._update_naver_product(pid, d))

    def _save_naver_product(self, data):
        from database.db_manager import add_naver_product
        add_naver_product(data)
        self.refresh_naver_products()

    def _update_naver_product(self, pid, data):
        from database.db_manager import update_naver_product
        update_naver_product(pid, data)
        self.refresh_naver_products()

    def _add_coupang_product(self):
        CoupangProductDialog(self.root, brands=get_all_brands(), on_save=self._save_coupang_product)

    def _edit_coupang_product(self):
        sel = self.coupang_prod_tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        prods = {p['id']: p for p in get_coupang_products()}
        if pid in prods:
            CoupangProductDialog(self.root, brands=get_all_brands(), data=prods[pid],
                                 on_save=lambda d: self._update_coupang_product(pid, d))

    def _save_coupang_product(self, data):
        from database.db_manager import add_coupang_product
        add_coupang_product(data)
        self.refresh_coupang_products()

    def _update_coupang_product(self, pid, data):
        from database.db_manager import update_coupang_product
        update_coupang_product(pid, data)
        self.refresh_coupang_products()

    def _bulk_keywords(self):
        from gui.bulk_keyword_dialog import BulkKeywordDialog
        BulkKeywordDialog(self.root, on_done=self.refresh_naver_products)

    def _manage_keywords(self):
        sel = self.naver_prod_tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        from gui.keyword_dialog import KeywordDialog
        prods = {p['id']: p for p in get_naver_products()}
        KeywordDialog(self.root, product=prods[pid], platform='naver',
                      on_change=self.refresh_naver_products)

    def _bulk_coupang_keywords(self):
        from gui.bulk_keyword_dialog import BulkKeywordDialog
        BulkKeywordDialog(self.root, platform='coupang', on_done=self.refresh_coupang_products)

    def _manage_coupang_keywords(self):
        from tkinter import messagebox
        try:
            sel = self.coupang_prod_tree.selection()
            if not sel:
                messagebox.showinfo("알림", "상품을 먼저 선택하세요.")
                return
            pid = int(sel[0])
            from gui.keyword_dialog import KeywordDialog
            prods = {p['id']: p for p in get_coupang_products()}
            KeywordDialog(self.root, product=prods[pid], platform='coupang',
                          on_change=self.refresh_coupang_products)
        except Exception as e:
            messagebox.showerror("오류", str(e))

    def _import_excel_naver(self):
        from gui.excel_import import ExcelImportDialog
        ExcelImportDialog(self.root, target='naver',
                          on_done=self.refresh_naver_products)

    def _import_excel(self):
        from gui.excel_import import ExcelImportDialog
        ExcelImportDialog(self.root, target='coupang',
                          on_done=self.refresh_coupang_products)

    # ─── 이벤트 ──────────────────────────────────────
    def _on_tab_change(self, event):
        tab = self.nb.index(self.nb.select())
        if tab == 0:
            self.refresh_naver()
        elif tab == 1:
            self.refresh_coupang()
        elif tab == 2:
            self._reload_sub_products()
            self.refresh_sub()
        elif tab == 3:
            self.refresh_brands()

    def _refresh_current_tab(self):
        tab = self.nb.index(self.nb.select())
        if tab == 0:
            self.refresh_naver()
        elif tab == 1:
            self.refresh_coupang()
        elif tab == 2:
            self._reload_sub_products()
            self.refresh_sub()

    def _on_naver_motion(self, event):
        item = self.naver_tree.identify_row(event.y)
        if not item or not item.startswith('nrank_'):
            self.naver_tree.config(cursor='')
            return
        cols     = self.naver_tree['columns']
        col_id   = self.naver_tree.identify_column(event.x)
        col_name = cols[int(col_id[1:]) - 1]
        if col_name in ('compare', 'link'):
            self.naver_tree.config(cursor='hand2')
        else:
            self.naver_tree.config(cursor='')

    def _rename_traffic_col(self, col_index: int):
        from tkinter.simpledialog import askstring
        cur = self.traffic_col_names[col_index]
        new_name = askstring(
            "트래픽현황 컬럼명 변경",
            f"트래픽 {col_index+1}번 컬럼명을 입력하세요:",
            initialvalue=cur,
            parent=self.root
        )
        if new_name is not None:
            self.traffic_col_names[col_index] = new_name
            update_traffic_column(col_index, new_name)
            self.naver_tree.heading(f'traffic_{col_index}',
                                    text=new_name or f'트래픽{col_index+1}')

    def _on_traffic_double_click(self, event):
        region = self.naver_tree.identify_region(event.x, event.y)
        if region != 'cell':
            return
        col_id = self.naver_tree.identify_column(event.x)
        row_id = self.naver_tree.identify_row(event.y)
        if not row_id or not row_id.startswith('nrank_'):
            return
        # 컬럼 인덱스 확인 (traffic_0~3인지)
        col_num = int(col_id.lstrip('#')) - 1
        all_cols = self.naver_tree['columns']
        if col_num < 0 or col_num >= len(all_cols):
            return
        col_name = all_cols[col_num]
        if not col_name.startswith('traffic_'):
            return
        traffic_idx = int(col_name.split('_')[1])

        # product_id 추출 (iid = 'nrank_{pid}_{kid}')
        parts = row_id.split('_')
        pid = int(parts[1])

        # 셀 위치에 Entry 팝업
        bbox = self.naver_tree.bbox(row_id, col_id)
        if not bbox:
            return
        x, y, w, h = bbox
        cur_val = self.naver_tree.set(row_id, col_name)
        if cur_val == '·':
            cur_val = ''
        entry = tk.Entry(self.naver_tree, font=('맑은 고딕', 9),
                         bg='#fffde7', relief=tk.SOLID, bd=1)
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, cur_val)
        entry.select_range(0, tk.END)
        entry.focus_set()

        def _save(e=None):
            val = entry.get().strip()
            entry.destroy()
            self.naver_tree.set(row_id, col_name, val if val else '·')
            save_traffic_data(pid, traffic_idx, val)

        entry.bind('<Return>',    _save)
        entry.bind('<FocusOut>',  _save)
        entry.bind('<Escape>',    lambda e: entry.destroy())

    def _on_naver_click(self, event):
        region = self.naver_tree.identify_region(event.x, event.y)
        if region != 'cell':
            return
        item = self.naver_tree.identify_row(event.y)
        if not item or not item.startswith('nrank_'):
            return
        cols     = self.naver_tree['columns']
        col_id   = self.naver_tree.identify_column(event.x)
        col_name = cols[int(col_id[1:]) - 1]
        pid      = int(item.split('_')[1])
        prods    = {p['id']: p for p in get_naver_products()}

        if col_name == 'link':
            if pid in prods and prods[pid]['url_naver']:
                webbrowser.open(prods[pid]['url_naver'])
        elif col_name == 'compare':
            if pid in prods:
                # 클릭 시 행 깜빡임 효과
                orig_tags = self.naver_tree.item(item, 'tags')
                self.naver_tree.item(item, tags=('flash',))
                self.root.after(180, lambda: self.naver_tree.item(item, tags=orig_tags))
                self.root.after(100, lambda: _open_compare(prods[pid]))

        def _open_compare(prod):
            from gui.keyword_compare_dialog import KeywordCompareDialog
            KeywordCompareDialog(self.root, product=prod)

    def _on_coupang_link_click(self, event):
        region = self.coupang_tree.identify_region(event.x, event.y)
        if region != 'cell':
            return
        col = self.coupang_tree.identify_column(event.x)
        if col != '#4':
            return
        item = self.coupang_tree.identify_row(event.y)
        vals = self.coupang_tree.item(item, 'values')
        if vals and vals[3] == '🔗' and item.startswith('cp_'):
            pid = int(item.split('_')[1])
            prods = {p['id']: p for p in get_coupang_products()}
            if pid in prods and prods[pid]['url_coupang']:
                webbrowser.open(prods[pid]['url_coupang'])

    def _reload_company_filter(self):
        all_brands = get_all_brands()
        companies = ['전체'] + sorted(set(b['company_name'] for b in all_brands if b['company_name']))
        self.company_cb['values'] = companies
        if self.company_var.get() not in companies:
            self.company_var.set('전체')
        self._reload_brand_filter()

    def _reload_brand_filter(self):
        all_brands = get_all_brands()
        company = self.company_var.get()
        if company == '전체':
            brands = ['전체'] + [b['brand_name'] for b in all_brands]
        else:
            brands = ['전체'] + [b['brand_name'] for b in all_brands if b['company_name'] == company]
        self.brand_cb['values'] = brands
        if self.brand_var.get() not in brands:
            self.brand_var.set('전체')

    def _on_company_change(self, event=None):
        self.brand_var.set('전체')
        self._reload_brand_filter()
        self._refresh_current_tab()

    def _print_current(self):
        from tkinter import messagebox
        try:
            tab = self.nb.index(self.nb.select())
            if tab == 0:
                self._print_tree(self.naver_tree,   '네이버 현황',
                                 skip_cols={'link'},   date_start=4)
            elif tab == 1:
                self._print_tree(self.coupang_tree, '쿠팡 현황',
                                 skip_cols={'link'},   date_start=3)
            else:
                messagebox.showinfo("인쇄", "네이버 현황 또는 쿠팡 현황 탭에서만 인쇄할 수 있습니다.")
        except Exception as e:
            messagebox.showerror("인쇄 오류", str(e))

    def _print_tree(self, tree, title: str, skip_cols: set, date_start: int):
        import tempfile, webbrowser
        from datetime import datetime
        from database.db_manager import get_all_brands

        all_cols  = tree['columns']
        skip_cols = skip_cols | {'product'}
        cols      = [c for c in all_cols if c not in skip_cols]
        headers   = [tree.heading(c)['text'] for c in cols]
        col_idx   = {c: i for i, c in enumerate(all_cols)}

        # 브랜드 → 회사 매핑
        brand_to_company = {b['brand_name']: b['company_name'] for b in get_all_brands()}

        # 트리 행을 회사별로 그룹화
        company_filter = self.company_var.get()
        from collections import OrderedDict
        company_rows: dict = OrderedDict()

        for iid in tree.get_children():
            vals = tree.item(iid, 'values')
            tags = tree.item(iid, 'tags')
            row_vals = [vals[col_idx[c]] if col_idx[c] < len(vals) else '' for c in cols]

            if 'total_row' in tags:
                style = 'background:#ecf0f1;font-weight:bold;'
            elif 'rank_row' in tags:
                style = 'background:#eaf4fb;'
            else:
                style = ''

            cells = ''.join(f'<td>{v}</td>' for v in row_vals)
            row_html = f'<tr style="{style}">{cells}</tr>'

            # 회사명 추출 (brand 컬럼 값으로 역추적)
            brand_val = vals[col_idx['brand']] if col_idx.get('brand', -1) < len(vals) else ''
            company   = brand_to_company.get(brand_val, brand_val) if brand_val else '기타'
            if 'total_row' in tags:
                company = '__total__'

            company_rows.setdefault(company, []).append(row_html)

        now          = datetime.now().strftime('%Y-%m-%d %H:%M')
        header_cells = ''.join(f'<th>{h}</th>' for h in headers)

        # 회사별 섹션 생성
        sections = []
        is_first = True
        for company, rows in company_rows.items():
            if company == '__total__':
                continue
            page_break = '' if is_first else 'page-break-before:always;'
            is_first   = False
            sections.append(f"""
<div style="{page_break}">
  <h2>{title} — {company}</h2>
  <div class="info">출력일시: {now}</div>
  <table>
    <thead><tr>{header_cells}</tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</div>""")

        # 총합계 행은 마지막 섹션에 추가
        total_rows = company_rows.get('__total__', [])
        if total_rows and sections:
            last = sections[-1]
            sections[-1] = last.replace('</table>\n</div>', f"{''.join(total_rows)}</table>\n</div>")

        html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ font-family: '맑은 고딕', Arial, sans-serif; font-size: 11px; margin: 12px; }}
  h2 {{ margin-bottom: 4px; font-size: 14px; }}
  .info {{ color: #555; margin-bottom: 8px; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 12px; }}
  th {{ background: #2c3e50; color: white; padding: 5px 8px; text-align: center; }}
  td {{ border: 1px solid #ddd; padding: 4px 7px; text-align: center; white-space: nowrap; }}
  td:nth-child(1), td:nth-child(2) {{ text-align: left; }}
  @media print {{ @page {{ size: landscape; margin: 10mm; }} }}
</style>
</head><body>
{''.join(sections)}
<script>window.onload = function(){{ window.print(); }}</script>
</body></html>"""

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.html',
                                          mode='w', encoding='utf-8')
        tmp.write(html)
        tmp.close()
        webbrowser.open(f'file:///{tmp.name}')

    def _run_check(self, mode: str = 'naver_rank'):
        company = self.company_var.get()
        label_map = {'naver_rank': '네이버', 'coupang_rank': '쿠팡'}
        label = label_map.get(mode, mode)

        def _check():
            self.root.after(0, lambda: self.status_lbl.config(text=f"{label} 체크 중..."))
            try:
                import subprocess, sys
                cmd = [sys.executable, 'checker.py', mode, company]
                subprocess.run(cmd, cwd='D:\\순위판매현황', timeout=1800)
                if mode == 'naver_rank':
                    self.root.after(0, self.refresh_naver)
                else:
                    self.root.after(0, self.refresh_coupang)
                self.root.after(0, lambda: self.status_lbl.config(text=f"{label} 체크 완료"))
            except Exception as e:
                self.root.after(0, lambda e=e: self.status_lbl.config(text=f"오류: {e}"))
        threading.Thread(target=_check, daemon=True).start()
