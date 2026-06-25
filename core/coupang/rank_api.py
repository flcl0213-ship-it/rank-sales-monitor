# -*- coding: utf-8 -*-
"""
쿠팡 검색 순위 체크 — playwright 기반 (Akamai 봇 차단 우회)
쿠팡 Open API 없이 검색 결과 페이지에서 상품 순위 추출
"""

import re
import time
import random
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import RANK_MAX_PAGES

PAGE_SIZE = 36
_PRODUCT_RE = re.compile(r'/vp/products/(\d+)')

# playwright 인스턴스를 모듈 수준에서 재사용
_playwright_ctx = {}


def _get_browser():
    """실제 Chrome 브라우저 + stealth (Akamai 우회)"""
    if 'browser' not in _playwright_ctx:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        _playwright_ctx['pw'] = pw
        _playwright_ctx['browser'] = pw.chromium.launch(
            channel='chrome',
            headless=False,
            args=[
                '--lang=ko-KR',
                '--disable-blink-features=AutomationControlled',
                '--window-position=-32000,-32000',  # 화면 밖으로
            ],
        )
        _playwright_ctx['ctx'] = _playwright_ctx['browser'].new_context(
            locale='ko-KR',
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/125.0.0.0 Safari/537.36'
            ),
            viewport={'width': 1280, 'height': 900},
        )
        try:
            from playwright_stealth import Stealth
            _playwright_ctx['stealth'] = Stealth()
        except ImportError:
            _playwright_ctx['stealth'] = None
    return _playwright_ctx['ctx']


def close():
    """사용 후 브라우저 종료"""
    if 'browser' in _playwright_ctx:
        try:
            _playwright_ctx['browser'].close()
            _playwright_ctx['pw'].stop()
        except Exception:
            pass
        _playwright_ctx.clear()


def find_rank(keyword: str, coupang_product_id: str) -> int:
    """
    쿠팡 검색 결과에서 coupang_product_id의 순위 반환.
    RANK_MAX_PAGES 페이지(기본 5 × 36 = 180위) 내에 없으면 0 반환.
    """
    if not coupang_product_id:
        return 0

    target = str(coupang_product_id).strip()

    try:
        ctx    = _get_browser()
        stealth = _playwright_ctx.get('stealth')
        page   = ctx.new_page()
        if stealth:
            stealth.apply_stealth_sync(page)

        for pg in range(1, RANK_MAX_PAGES + 1):
            url = (
                f'https://www.coupang.com/np/search'
                f'?q={keyword}&channel=user&sorter=scoreDesc'
                f'&listSize={PAGE_SIZE}&page={pg}'
            )
            try:
                resp = page.goto(url, wait_until='domcontentloaded', timeout=20000)
                if resp and resp.status == 403:
                    print(f'[WARN] 쿠팡 403 차단 (키워드={keyword})')
                    page.close()
                    return 0

                try:
                    page.wait_for_selector('li.search-product', timeout=5000)
                except Exception:
                    pass

                html = page.content()
                ids = _PRODUCT_RE.findall(html)
                seen, unique = set(), []
                for pid in ids:
                    if pid not in seen:
                        seen.add(pid)
                        unique.append(pid)

                for idx, pid in enumerate(unique):
                    if pid == target:
                        page.close()
                        return (pg - 1) * PAGE_SIZE + idx + 1

                if len(unique) < PAGE_SIZE:
                    break

                time.sleep(random.uniform(1.5, 3.0))

            except Exception as e:
                print(f'[ERROR] 쿠팡 순위 페이지 로드 실패: {e}')
                break

        page.close()

    except Exception as e:
        print(f'[ERROR] 쿠팡 순위 조회 실패: {e}')

    return 0
