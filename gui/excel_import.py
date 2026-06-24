# -*- coding: utf-8 -*-
"""
엑셀 일괄 등록 다이얼로그
엑셀 형식: NO | 회사명 | 브랜드 | 모델명 | 상품명 | 링크 | 비고/상품ID
  - 쿠팡: 7번째 열에 상품ID 입력 시 자동 등록
  - 네이버/쿠팡 각각 별도 파일
  - 회사명·브랜드·모델명은 그룹 첫 행에만 입력, 이후 행은 위 값 이어받음
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Callable


class ExcelImportDialog(tk.Toplevel):
    def __init__(self, parent, target: str = 'naver', on_done: Callable = None):
        """
        target: 'naver' | 'coupang'
        """
        super().__init__(parent)
        target_label = {'naver': '네이버', 'coupang': '쿠팡'}
        self.title(f"엑셀 일괄 등록 — {target_label.get(target, target)}")
        self.geometry("700x520")
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
        plat = '네이버' if self.target == 'naver' else '쿠팡'
        info = (
            f"[{plat}] 엑셀 형식: NO | 회사명 | 브랜드 | 모델명 | 상품명 | 링크 | 비고\n"
            "  • 데이터는 4행부터 시작\n"
            "  • 회사명·브랜드·모델명이 비어 있으면 위 행 값을 이어받음\n"
            "  • 브랜드명이 DB와 다를 경우 아래 매핑 추가"
        )
        tk.Label(self, text=info, justify=tk.LEFT, fg='#555',
                 font=('맑은 고딕', 9), bg='#f8f9fa', relief=tk.GROOVE,
                 padx=10, pady=8).pack(fill=tk.X, padx=12)

        # 브랜드 매핑
        tk.Label(self, text="브랜드 매핑  (엑셀 브랜드명 → DB 브랜드명)",
                 font=('맑은 고딕', 10, 'bold')).pack(anchor='w', padx=12, pady=(8, 2))

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
        tk.Entry(f, textvariable=excel_var, width=22).pack(side=tk.LEFT, padx=4)
        tk.Label(f, text="→ DB:").pack(side=tk.LEFT)
        brands = [b['brand_name'] for b in get_all_brands()]
        cb = ttk.Combobox(f, textvariable=db_var, values=brands, width=18, state='readonly')
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
            wb = openpyxl.load_workbook(path, data_only=True)
        except Exception as e:
            messagebox.showerror("오류", f"파일을 열 수 없습니다:\n{e}", parent=self)
            return None

        mapping    = self._get_mapping()
        records    = []
        cur_company = ''
        cur_brand   = ''
        cur_model   = ''

        ws = wb.active
        for row in ws.iter_rows(min_row=4, values_only=True):
            cols = list(row) + [None] * 8
            no, company, brand, model, product_name, link = cols[0], cols[1], cols[2], cols[3], cols[4], cols[5]
            extra = cols[6]  # 쿠팡: 상품ID / 네이버: 비고

            # 헤더 행 스킵
            if str(no).strip().upper() == 'NO':
                continue

            # 이전 값 이어받기
            if company:
                cur_company = str(company).strip()
            if brand:
                cur_brand = str(brand).strip()
            if model:
                cur_model = str(model).strip()

            if not product_name or not link:
                continue

            db_brand = mapping.get(cur_brand, cur_brand)

            # 쿠팡 상품ID: 숫자형이면 상품ID, 아니면 비고
            coupang_product_id = ''
            if self.target == 'coupang' and extra is not None:
                s = str(extra).strip().replace('.0', '')
                if s.isdigit():
                    coupang_product_id = s

            records.append({
                'platform':           self.target,
                'company_name':       cur_company,
                'brand_name':         db_brand,
                'model_name':         cur_model,
                'product_name':       str(product_name).strip(),
                'url':                str(link).strip(),
                'coupang_product_id': coupang_product_id,
            })

        return records

    def _preview(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state=tk.DISABLED)

        records = self._parse_excel()
        if records is None:
            return

        self._log(f"미리보기: 총 {len(records)}건")
        self._log("-" * 60)
        for r in records[:30]:
            self._log(f"[{r['brand_name']}] {r['model_name']} | {r['product_name'][:50]}")
        if len(records) > 30:
            self._log(f"... 외 {len(records) - 30}건")

    def _run(self):
        records = self._parse_excel()
        if records is None:
            return

        from database.db_manager import (
            get_all_brands, add_brand,
            add_naver_product, add_coupang_product,
            get_naver_products, get_coupang_products,
        )

        brands           = {b['brand_name']: b['id'] for b in get_all_brands()}
        existing_naver   = {p['url_naver']   for p in get_naver_products()   if p['url_naver']}
        existing_coupang = {p['url_coupang'] for p in get_coupang_products() if p['url_coupang']}

        saved = skipped = error = 0
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state=tk.DISABLED)

        for r in records:
            brand_id = brands.get(r['brand_name'])
            if not brand_id:
                # 브랜드 자동 생성 (API 키는 나중에 브랜드 관리에서 입력)
                brand_id = add_brand({
                    'company_name': r['company_name'],
                    'brand_name':   r['brand_name'],
                })
                brands[r['brand_name']] = brand_id
                self._log(f"[브랜드 자동 생성] {r['company_name']} / {r['brand_name']}")

            if self.target == 'naver':
                if r['url'] in existing_naver:
                    skipped += 1
                    continue
                add_naver_product({
                    'brand_id':     brand_id,
                    'model_name':   r['model_name'],
                    'product_name': r['product_name'],
                    'seller':       '',
                    'url_naver':    r['url'],
                })
                existing_naver.add(r['url'])
                saved += 1

            else:  # coupang
                if r['url'] in existing_coupang:
                    skipped += 1
                    continue
                add_coupang_product({
                    'brand_id':           brand_id,
                    'model_name':         r['model_name'],
                    'product_name':       r['product_name'],
                    'url_coupang':        r['url'],
                    'coupang_product_id': r.get('coupang_product_id', ''),
                })
                existing_coupang.add(r['url'])
                saved += 1

        self._log(f"등록 완료: 신규 {saved}건 / 중복 스킵 {skipped}건 / 오류 {error}건")
        if self.on_done:
            self.on_done()
