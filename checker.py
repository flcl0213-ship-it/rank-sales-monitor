# -*- coding: utf-8 -*-
"""
순위 체크 + 판매 수집 실행기
"""

from datetime import date
from database.db_manager import (
    get_all_brands, get_naver_products, get_coupang_products,
    get_keywords, save_rank, save_order,
)
from core.naver.rank_api import find_rank as naver_rank
from core.naver.sales_api import get_orders as naver_orders
from core.coupang.sales_api import get_orders as coupang_orders


def run_rank_check():
    """네이버 전체 상품 × 전체 키워드 순위 체크"""
    print(f"\n[순위 체크 시작] naver {date.today()}")
    products = get_naver_products()
    today = date.today()
    checked = 0

    for p in products:
        keywords = get_keywords(p['id'])
        for kw in keywords:
            rank = naver_rank(
                keyword=kw['keyword'],
                product_name=p['product_name'],
                seller_name=p.get('seller', ''),
                url_naver=p.get('url_naver', ''),
            )
            save_rank(
                naver_product_id=p['id'],
                keyword_id=kw['id'],
                keyword_type=kw['type'],
                rank=rank,
                checked_date=today,
            )
            print(f"  [{kw['type']}] {p['product_name']} / '{kw['keyword']}' → {rank}위")
            checked += 1

    print(f"[순위 체크 완료] {checked}건")


def run_naver_sales():
    """네이버 판매 수집 — 옵션명 포함"""
    print(f"\n[네이버 판매 수집 시작] {date.today()}")
    brands = get_all_brands()
    naver_prods = get_naver_products()
    name_map = {p['product_name'].strip(): p for p in naver_prods}
    saved = skipped = 0

    for brand in brands:
        if not brand['naver_client_id']:
            continue
        orders = naver_orders(brand['naver_client_id'], brand['naver_client_secret'])

        for o in orders:
            matched = None
            for pname, prod in name_map.items():
                if pname in o['product_name'] or o['product_name'] in pname:
                    if prod['brand_id'] == brand['id']:
                        matched = prod
                        break

            ok = save_order(
                order_id=o['order_id'],
                brand_id=brand['id'],
                platform='naver',
                naver_product_id=matched['id'] if matched else None,
                option_name=o.get('option_name', ''),
                quantity=o['quantity'],
                revenue=o['revenue'],
                order_date=o['order_date'],
                status=o.get('status', ''),
            )
            if ok:
                saved += 1
            else:
                skipped += 1

    print(f"[네이버 판매 수집 완료] 신규 {saved}건 / 중복 스킵 {skipped}건")


def run_coupang_sales():
    """쿠팡 판매 수집"""
    print(f"\n[쿠팡 판매 수집 시작] {date.today()}")
    brands = get_all_brands()
    coupang_prods = get_coupang_products()
    name_map = {p['product_name'].strip(): p for p in coupang_prods}
    saved = skipped = 0

    for brand in brands:
        if not brand['coupang_vendor_id']:
            continue
        orders = coupang_orders(
            brand['coupang_vendor_id'],
            brand['coupang_access_key'],
            brand['coupang_secret_key'],
        )

        for o in orders:
            matched = None
            for pname, prod in name_map.items():
                if pname in o['product_name'] or o['product_name'] in pname:
                    if prod['brand_id'] == brand['id']:
                        matched = prod
                        break

            ok = save_order(
                order_id=o['order_id'],
                brand_id=brand['id'],
                platform='coupang',
                coupang_product_id=matched['id'] if matched else None,
                quantity=o['quantity'],
                revenue=o['revenue'],
                order_date=o['order_date'],
                status=o.get('status', ''),
            )
            if ok:
                saved += 1
            else:
                skipped += 1

    print(f"[쿠팡 판매 수집 완료] 신규 {saved}건 / 중복 스킵 {skipped}건")


if __name__ == '__main__':
    import sys
    from database.models import init_db
    init_db()

    mode = sys.argv[1] if len(sys.argv) > 1 else 'rank'

    if mode == 'rank':
        run_rank_check()
    elif mode == 'naver_sales':
        run_naver_sales()
    elif mode == 'coupang_sales':
        run_coupang_sales()
    elif mode == 'all':
        run_rank_check()
        run_naver_sales()
        run_coupang_sales()
    else:
        print("사용법: python checker.py [rank|naver_sales|coupang_sales|all]")
