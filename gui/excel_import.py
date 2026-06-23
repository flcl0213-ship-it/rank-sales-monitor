# -*- coding: utf-8 -*-
"""
엑셀 일괄 등록 다이얼로그
엑셀 형식: NO | 브랜드 | 네이버모델명 | 네이버링크 | 쿠팡모델명 | 쿠팡상품명 | 쿠팡링크 | 비고
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Callable


class ExcelImportDialog(tk.Toplevel):
    def __init__(self, parent, target: str = 'both', on_done: Callable = None):
        """
        target: 'naver' | 'coupang' | 'both'
        """
        super().__init__(parent)
        target_label = {'naver': '네이버', 'coupang': '쿠팡', 'both': '전체'}
        self.title(f"엑셀 일괄 등록 — {target_label.get(target, '전체')}")
        self.geometry("700x500")
        self.resizable(True, True)
        self.grab_set()
        self.target    = target
        self.on_done   = on_done
        self.file_path = tk.StringVar()

        self._build()

    def _build(self):
        # 파일 선택
        file_frame = tk.Frame(self, pady=8)
        file_frame.pack(fill=tk.X, padx=12)

        tk.Label(file_frame, text="엑셀 파일:", width=10, anchor='e').pack(side=tk.LEFT)
        tk.Entry(file_frame, textvariable=self.file_path, width=50).pack(side=tk.LEFT, padx=4)
        tk.Button(file_frame, text="찾아보기", command=self._browse,
                  bg='#7f8c8d', fg='white', relief=tk.FLAT, padx=8).pack(side=tk.LEFT)

        # 안내
        info = (
            "엑셀 형식 안내:\n"
            "  • 헤더 행: NO | 브랜드 | 네이버(모델명, 링크) | 쿠팡(모델명, 상품명, 링크) | 비고\n"
            "  • 브랜드 열: 비어있으면 위 행의 브랜드를 이어받음\n"
            "  • 네이버 링크가 있으면 → 네이버 상품으로 등록\n"
            "  • 쿠팡 링크가 있으면 → 쿠팡 상품으로 등록\n"
            "  • 브랜드명은 브랜드 관리에 등록된 이름과 일치해야 합니다\n"
            "    (예: 웅테크삼성 → 인생필터 브랜드명으로 매핑 필요)\n"
        )
        tk.Label(self, text=info, justify=tk.LEFT, fg='#555',
                 font=('맑은 고딕', 9), bg='#f8f9fa', relief=tk.GROOVE,
                 padx=10, pady=8).pack(fill=tk.X, padx=12)

        # 브랜드 매핑 섹션
        map_lbl = tk.Label(self, text="엑셀 브랜드명 → DB 브랜드명 매핑",
                           font=('맑은 고딕', 10, 'bold'))
        map_lbl.pack(anchor='w', padx=12, pady=(8, 2))

        self.map_frame = tk.Frame(self)
        self.map_frame.pack(fill=tk.X, padx=12)
        self.mappings: list = []
        tk.Button(self, text="+ 매핑 추가", command=self._add_mapping,
                  bg='#2c3e50', fg='white', relief=tk.FLAT, padx=8).pack(anchor='w', padx=12, pady=4)

        # 로그
        self.log_text = tk.Text(self, height=8, font=('Consolas', 9), state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        # 실행 버튼
        btn_frame = tk.Frame(self, pady=8)
        btn_frame.pack()
        tk.Button(btn_frame, text="미리보기", command=self._preview,
                  bg='#3498db', fg='white', relief=tk.FLAT, padx=12).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="등록 실행", command=self._run,
                  bg='#27ae60', fg='white', relief=tk.FLAT, padx=12).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="닫기", command=self.destroy,
                  relief=tk.FLAT, padx=12).pack(side=tk.LEFT, padx=6)

        # 기본 매핑 자동 추가
        self._add_mapping('웅테크 삼성', '인생필터')
        self._add_mapping('웅테크엘지', '인생필터')
        self._add_mapping('웅테크위닉스', '인생필터')

    def _browse(self):
        path = filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if path:
            self.file_path.set(path)

    def _add_mapping(self, excel_brand='', db_brand=''):
        from database.db_manager import get_all_brands
        row = len(self.mappings)
        f = tk.Frame(self.map_frame)
        f.grid(row=row, column=0, sticky='w', pady=2)

        excel_var = tk.StringVar(value=excel_brand)
        db_var    = tk.StringVar(value=db_brand)

        tk.Label(f, text="엑셀:", width=5).pack(side=tk.LEFT)
        tk.Entry(f, textvariable=excel_var, width=20).pack(side=tk.LEFT, padx=4)
        tk.Label(f, text="→ DB:").pack(side=tk.LEFT)
        brands = [b['brand_name'] for b in get_all_brands()]
        cb = ttk.Combobox(f, textvariable=db_var, values=brands, width=16, state='readonly')
        cb.pack(side=tk.LEFT, padx=4)

        self.mappings.append((excel_var, db_var))

    def _get_mapping(self) -> dict:
        return {ev.get().strip(): dv.get().strip()
                for ev, dv in self.mappings if ev.get().strip()}

    def _log(self, msg: str):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + '\n')
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _parse_excel(self):
        import openpyxl
        path = self.file_path.get()
        if not path:
            messagebox.showwarning("오류", "엑셀 파일을 선택하세요.", parent=self)
            return None

        try:
            wb = openpyxl.load_workbook(path)
        except Exception as e:
            messagebox.showerror("오류", f"파일을 열 수 없습니다:\n{e}", parent=self)
            return None

        mapping = self._get_mapping()
        records = []
        cur_brand = ''

        for ws in wb.worksheets:
            for row in ws.iter_rows(min_row=5, values_only=True):
                no, brand, n_model, n_link, c_model, c_name, c_link, *_ = list(row) + [None]*8

                if brand:
                    cur_brand = str(brand).strip()

                db_brand = mapping.get(cur_brand, cur_brand)

                if n_link:
                    records.append({
                        'platform':   'naver',
                        'brand_name': db_brand,
                        'model_name': str(n_model).strip() if n_model else '',
                        'product_name': str(n_model).strip() if n_model else '',
                        'url':        str(n_link).strip(),
                    })

                if c_link and c_name:
                    records.append({
                        'platform':     'coupang',
                        'brand_name':   db_brand,
                        'model_name':   str(c_model).strip() if c_model else '',
                        'product_name': str(c_name).strip(),
                        'url':          str(c_link).strip(),
                    })

        return records

    def _filter(self, records):
        if self.target == 'both':
            return records
        return [r for r in records if r['platform'] == self.target]

    def _preview(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state=tk.DISABLED)

        records = self._parse_excel()
        if records is None:
            return

        records = self._filter(records)
        naver_cnt   = sum(1 for r in records if r['platform'] == 'naver')
        coupang_cnt = sum(1 for r in records if r['platform'] == 'coupang')
        self._log(f"미리보기: 총 {len(records)}건 (네이버 {naver_cnt}건, 쿠팡 {coupang_cnt}건)")
        self._log("-" * 60)
        for r in records[:20]:
            self._log(f"[{r['platform']}] {r['brand_name']} | {r['model_name']} | {r['product_name'][:40]}")
        if len(records) > 20:
            self._log(f"... 외 {len(records)-20}건")

    def _run(self):
        records = self._parse_excel()
        if records is None:
            return
        records = self._filter(records)

        from database.db_manager import (
            get_all_brands, add_naver_product, add_coupang_product,
            get_naver_products, get_coupang_products,
        )

        brands = {b['brand_name']: b['id'] for b in get_all_brands()}
        existing_naver   = {p['url_naver'] for p in get_naver_products() if p['url_naver']}
        existing_coupang = {p['url_coupang'] for p in get_coupang_products() if p['url_coupang']}

        saved = skipped = error = 0
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state=tk.DISABLED)

        for r in records:
            brand_id = brands.get(r['brand_name'])
            if not brand_id:
                self._log(f"[SKIP] 브랜드 없음: {r['brand_name']}")
                error += 1
                continue

            if r['platform'] == 'naver':
                if r['url'] in existing_naver:
                    skipped += 1
                    continue
                add_naver_product({
                    'brand_id':     brand_id,
                    'model_name':   r['model_name'],
                    'product_name': r['product_name'],
                    'url_naver':    r['url'],
                })
                existing_naver.add(r['url'])
                saved += 1

            else:
                if r['url'] in existing_coupang:
                    skipped += 1
                    continue
                add_coupang_product({
                    'brand_id':     brand_id,
                    'model_name':   r['model_name'],
                    'product_name': r['product_name'],
                    'url_coupang':  r['url'],
                })
                existing_coupang.add(r['url'])
                saved += 1

        self._log(f"등록 완료: 신규 {saved}건 / 중복 스킵 {skipped}건 / 오류 {error}건")
        if self.on_done:
            self.on_done()
