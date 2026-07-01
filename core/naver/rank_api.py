# -*- coding: utf-8 -*-
"""
네이버 쇼핑 검색 API — 키워드별 내 상품 순위 조회
"""

import requests
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import NAVER_SEARCH_CLIENT_ID, NAVER_SEARCH_CLIENT_SECRET, RANK_MAX_PAGES


def find_rank(keyword: str, product_name: str, seller_name: str = '',
              url_naver: str = '', naver_product_id: str = '') -> int:
    """
    네이버 쇼핑에서 키워드 검색 후 내 상품 순위 반환.

    Returns:
        순위 (1~200). 0 = 200위 밖 또는 오류.
    """
    if not NAVER_SEARCH_CLIENT_ID:
        print("[WARN] 네이버 검색 API 키가 설정되지 않았습니다.")
        return 0

    headers = {
        "X-Naver-Client-Id":     NAVER_SEARCH_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_SEARCH_CLIENT_SECRET,
    }

    display = 100  # 한 번에 최대 100개
    for page in range(RANK_MAX_PAGES):
        start = page * display + 1
        params = {
            "query":   keyword,
            "display": display,
            "start":   start,
            "sort":    "sim",  # 정확도순
        }
        try:
            resp = requests.get(
                "https://openapi.naver.com/v1/search/shop.json",
                headers=headers,
                params=params,
                timeout=10,
            )
            if resp.status_code != 200:
                print(f"[ERROR] 네이버 API 오류: {resp.status_code} {resp.text[:200]}")
                break

            data = resp.json()
            items = data.get("items", [])
            if not items:
                break

            for idx, item in enumerate(items):
                rank = start + idx
                if _is_match(item, product_name, seller_name, url_naver, naver_product_id):
                    return rank

        except Exception as e:
            print(f"[ERROR] 네이버 순위 조회 실패: {e}")
            break

    return 0


def _is_match(item: dict, product_name: str, seller_name: str,
              url_naver: str = '', naver_product_id: str = '') -> bool:
    """네이버 API 응답 item 과 내 상품이 일치하는지 확인"""
    title   = item.get("title", "").replace("<b>", "").replace("</b>", "").lower()
    mall    = item.get("mallName", "").lower()
    link    = item.get("link", "")
    prod_id = item.get("productId", "")

    # naver_product_id → link에 포함 여부 (가장 정확)
    if naver_product_id and naver_product_id in link:
        return True

    # 기존 URL 매칭 (fallback)
    if url_naver and (prod_id in url_naver or url_naver.rstrip('/') in link):
        return True

    # 상품명 + 판매자 매칭 (최후 수단)
    name_ok   = product_name.lower() in title or title in product_name.lower()
    seller_ok = not seller_name or seller_name.lower() in mall or mall in seller_name.lower()

    return name_ok and seller_ok
