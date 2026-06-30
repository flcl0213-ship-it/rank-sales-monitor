# -*- coding: utf-8 -*-
"""
순위 체크 + 판매 수집 실행기
"""

import time
import random
from datetime import date, timedelta
from database.db_manager import (
    get_all_brands, get_naver_products, get_coupang_products,
    get_keywords, save_rank, save_order,
)
from core.naver.rank_api import find_rank as naver_rank
from core.naver.sales_api import get_orders as naver_orders
from core.coupang.rank_api import find_rank as coupang_rank
from core.coupang.sales_api import get_orders as coupang_orders


def run_rank_check(company_filter='전체'):
    """네이버 전체 상품 × 전체 키워드 순위 체크"""
    print(f"\n[순위 체크 시작] naver {date.today()} (회사={company_filter})")
    all_products = get_naver_products()
    if company_filter != '전체':
        company_brand_ids = {b['id'] for b in get_all_brands() if b['company_name'] == company_filter}
        products = [p for p in all_products if p.get('brand_id') in company_brand_ids]
    else:
        products = all_products
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
                keyword_id=kw['id'],
                keyword_type=kw['type'],
                rank=rank,
                checked_date=today,
                naver_product_id=p['id'],
            )
            print(f"  [{kw['type']}] {p['product_name']} / '{kw['keyword']}' → {rank}위")
            checked += 1

    print(f"[순위 체크 완료] {checked}건")


def run_coupang_rank_check(company_filter='전체'):
    """쿠팡 순위 체크 — 같은 키워드는 한 번 검색으로 여러 상품 동시 매칭"""
    from core.coupang.rank_api import CoupangRankTracker

    print(f"\n[쿠팡 순위 체크 시작] {date.today()} (회사={company_filter})")
    all_products = get_coupang_products()
    if company_filter != '전체':
        company_brand_ids = {b['id'] for b in get_all_brands() if b['company_name'] == company_filter}
        products = [p for p in all_products if p.get('brand_id') in company_brand_ids]
    else:
        products = all_products

    today = date.today()

    # 키워드별 (kw_row, product_row) 그룹핑
    keyword_map: dict[str, list] = {}
    for p in products:
        if not p.get('coupang_product_id'):
            continue
        for kw in get_keywords(p['id'], platform='coupang'):
            if kw['type'] != 'main':
                continue
            keyword_map.setdefault(kw['keyword'], []).append((kw, p))

    if not keyword_map:
        print('[INFO] 체크할 쿠팡 키워드 없음')
        return

    tracker = CoupangRankTracker()
    checked = 0

    try:
        for keyword, pairs in keyword_map.items():
            product_ids = [p['coupang_product_id'] for _, p in pairs]
            rank_results = tracker.find_ranks(keyword, product_ids)
            rank_map = {r['product_id']: r['rank'] for r in rank_results if r['found']}

            for kw, p in pairs:
                pid_str = str(p['coupang_product_id'])
                rank = rank_map.get(pid_str) or 0
                save_rank(
                    keyword_id=kw['id'],
                    keyword_type=kw['type'],
                    rank=rank,
                    checked_date=today,
                    coupang_product_id=p['id'],
                )
                print(f"  [{kw['type']}] {p['product_name'][:30]} / '{keyword}' → {rank}위")
                checked += 1

            time.sleep(random.uniform(2.0, 4.0))  # 키워드 간 딜레이
    finally:
        tracker.close()

    print(f"[쿠팡 순위 체크 완료] {checked}건")


def run_naver_sales():
    """네이버 판매 수집 — 같은 API 키는 1회만 호출, 회사 전체 상품 대상 매칭"""
    print(f"\n[네이버 판매 수집 시작] {date.today()}")
    brands     = get_all_brands()
    naver_prods = get_naver_products()
    saved = skipped = 0

    today     = date.today()
    yesterday = today - timedelta(days=1)

    # 같은 API 키를 가진 브랜드를 그룹핑 (스마트스토어 1개 = 1회만 호출)
    key_to_brands = {}
    for brand in brands:
        if not brand['naver_client_id']:
            continue
        key = (brand['naver_client_id'], brand['naver_client_secret'])
        key_to_brands.setdefault(key, []).append(brand)

    for (client_id, client_secret), brand_group in key_to_brands.items():
        # 이 API 키로 등록된 모든 브랜드의 상품 맵
        brand_ids = {b['id'] for b in brand_group}
        prod_map  = {p['product_name'].strip(): p
                     for p in naver_prods if p['brand_id'] in brand_ids}

        company = brand_group[0]['company_name']
        orders = (naver_orders(client_id, client_secret, yesterday) +
                  naver_orders(client_id, client_secret, today))
        print(f"  [{company}] 주문 {len(orders)}건 수집")

        for o in orders:
            matched = None
            for pname, prod in prod_map.items():
                if pname in o['product_name'] or o['product_name'] in pname:
                    matched = prod
                    break

            brand_id = matched['brand_id'] if matched else brand_group[0]['id']
            ok = save_order(
                order_id=o['order_id'],
                brand_id=brand_id,
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

    company = sys.argv[2] if len(sys.argv) > 2 else '전체'

    if mode == 'rank':
        run_rank_check(company)
        run_coupang_rank_check(company)
    elif mode == 'naver_rank':
        run_rank_check(company)
        run_naver_sales()
    elif mode == 'coupang_rank':
        run_coupang_rank_check(company)
    elif mode == 'naver_sales':
        run_naver_sales()
    elif mode == 'coupang_sales':
        run_coupang_sales()
    elif mode == 'all':
        run_rank_check(company)
        run_coupang_rank_check(company)
        run_naver_sales()
        # run_coupang_sales()  # 쿠팡 Wing API IP 제한으로 비활성화
    else:
        print("사용법: python checker.py [rank|naver_rank|coupang_rank|naver_sales|coupang_sales|all]")
