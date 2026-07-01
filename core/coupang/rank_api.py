# -*- coding: utf-8 -*-
"""
쿠팡 검색 순위 체크 — CDP (Chrome DevTools Protocol)
별도 Chrome 인스턴스를 --remote-debugging-port=9222 로 기동,
사용자가 최초 1회 쿠팡 방문 후 신뢰 확보 → 이후 자동화.
"""

import re
import time
import random
import subprocess
import sys
import os
import requests as _req
from datetime import datetime
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import RANK_MAX_PAGES

PAGE_SIZE   = 72
PRODUCT_RE  = re.compile(r'/vp/products/(\d+)')
BLOCK_SIGNALS = ['사용권한이 없습니다', 'Access Denied', 'Robot Check']

CDP_PORT     = 9222
CDP_PROFILE  = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'data', 'cdp_chrome'
)
CHROME_EXE   = r'C:\Program Files\Google\Chrome\Application\chrome.exe'

_pw_ctx: dict = {}   # pw, browser, context, page


def _is_cdp_running() -> bool:
    """CDP Chrome 이 이미 실행 중인지 확인"""
    try:
        r = _req.get(f'http://localhost:{CDP_PORT}/json/version', timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def _start_cdp_chrome() -> subprocess.Popen:
    """CDP Chrome 시작 (별도 프로필, 화면에 표시)"""
    os.makedirs(CDP_PROFILE, exist_ok=True)
    return subprocess.Popen([
        CHROME_EXE,
        f'--remote-debugging-port={CDP_PORT}',
        f'--user-data-dir={CDP_PROFILE}',
        '--window-size=1100,750',
        '--window-position=100,50',
        '--lang=ko-KR',
    ])


def _get_page():
    """playwright → CDP 연결된 page 반환"""
    if 'page' not in _pw_ctx:
        from playwright.sync_api import sync_playwright

        if not _is_cdp_running():
            print('[INFO] CDP Chrome 시작 중...')
            _pw_ctx['proc'] = _start_cdp_chrome()
            time.sleep(3)

        pw = sync_playwright().start()
        _pw_ctx['pw'] = pw
        browser = pw.chromium.connect_over_cdp(f'http://localhost:{CDP_PORT}')
        _pw_ctx['browser'] = browser

        # 기존 컨텍스트 재사용 (쿠키 유지)
        if browser.contexts:
            ctx = browser.contexts[0]
        else:
            ctx = browser.new_context(locale='ko-KR')
        _pw_ctx['ctx'] = ctx

        is_new = not os.path.exists(os.path.join(CDP_PROFILE, 'Default'))

        if is_new:
            # 최초: 쿠팡 홈 방문 (신뢰 수립)
            page = ctx.new_page()
            print('[INFO] 최초 실행 — 쿠팡 크롬 창에서 검색을 한 번 해주세요.')
            print('[INFO] 예: 검색창에 "공기청정기필터" 입력 후 Enter')
            page.goto('https://www.coupang.com', wait_until='domcontentloaded', timeout=20000)
            print('[INFO] 30초 대기 중 (이 시간 동안 쿠팡에서 임의 검색하면 더 좋습니다)...')
            time.sleep(30)
            _pw_ctx['page'] = page
        else:
            page = ctx.new_page()
            _pw_ctx['page'] = page

    return _pw_ctx['page']


def _is_blocked(html: str) -> bool:
    if len(html) < 3000:
        return True
    return any(s in html for s in BLOCK_SIGNALS)


def close():
    """세션 정리 (Chrome 프로세스는 유지)"""
    if 'page' in _pw_ctx:
        try:
            _pw_ctx['page'].close()
        except Exception:
            pass
    if 'pw' in _pw_ctx:
        try:
            _pw_ctx['pw'].stop()
        except Exception:
            pass
    _pw_ctx.clear()


class CoupangRankTracker:

    def __init__(self):
        self._fail_count = 0
        self.MAX_FAILS   = 3

    def find_ranks(self, keyword: str, product_ids: list,
                   max_page: int = None, include_ads: bool = False) -> list:
        if max_page is None:
            max_page = RANK_MAX_PAGES

        targets = {str(pid) for pid in product_ids if pid}
        results = {
            str(pid): {
                'product_id': str(pid), 'keyword': keyword,
                'rank': None, 'page': None,
                'found': False, 'is_ad': False,
                'checked_at': datetime.now().isoformat(),
            }
            for pid in product_ids if pid
        }

        organic_total = 0
        encoded_kw    = quote(keyword)

        try:
            page = _get_page()
        except Exception as e:
            print(f'[ERROR] CDP 연결 실패: {e}')
            return list(results.values())

        # 첫 페이지 전: 홈 경유 (검색 URL 직행 패턴 회피)
        try:
            cur = page.url or ''
            if 'coupang.com' not in cur or '/np/search' in cur:
                page.goto('https://www.coupang.com', wait_until='load', timeout=15000)
                time.sleep(random.uniform(1.5, 3.0))
                # 검색창에 키워드 입력 후 엔터
                page.fill('input#headerSearchKeyword', keyword)
                time.sleep(random.uniform(0.5, 1.0))
                page.press('input#headerSearchKeyword', 'Enter')
                time.sleep(random.uniform(2.0, 3.5))
                # 1페이지는 이미 로드됨 → 루프에서 pg=1 스킵용 플래그
                _home_searched = True
            else:
                _home_searched = False
        except Exception:
            _home_searched = False

        for pg in range(1, max_page + 1):
            url = (
                f'https://www.coupang.com/np/search'
                f'?q={encoded_kw}&page={pg}'
                f'&listSize={PAGE_SIZE}&sorter=scoreDesc&channel=user'
            )
            try:
                # pg=1은 홈 검색으로 이미 이동했으면 URL 재방문 생략
                if pg == 1 and _home_searched:
                    pass
                else:
                    try:
                        page.goto(url, wait_until='load', timeout=20000)
                    except Exception:
                        pass

                # 상품 렌더링 완료 대기
                try:
                    page.wait_for_selector('a[href*="/vp/products/"]', timeout=8000)
                except Exception:
                    pass
                time.sleep(random.uniform(2.0, 3.5))

                html = page.content()

                if _is_blocked(html):
                    self._fail_count += 1
                    print(f'[WARN] 차단 (키워드={keyword}, pg={pg})')
                    if self._fail_count >= self.MAX_FAILS:
                        print('[INFO] 차단 지속 — 잠시 대기 후 재시도')
                        time.sleep(random.uniform(30, 60))
                        self._fail_count = 0
                    else:
                        time.sleep(random.uniform(10, 20))
                    break

                self._fail_count = 0

                pids = list(dict.fromkeys(PRODUCT_RE.findall(html)))
                page_organic = 0

                for pid in pids:
                    organic_total += 1
                    page_organic  += 1
                    if pid in targets:
                        results[pid].update({
                            'rank': organic_total, 'page': pg, 'found': True,
                        })
                        targets.discard(pid)

                if not targets:
                    break
                if page_organic < PAGE_SIZE // 2:
                    break

                time.sleep(random.uniform(3.0, 5.0))

            except Exception as e:
                print(f'[ERROR] 페이지 로드 실패 (pg={pg}): {e}')
                break

        return list(results.values())

    def find_rank(self, keyword: str, coupang_product_id: str,
                  max_page: int = None) -> int:
        res = self.find_ranks(keyword, [coupang_product_id], max_page)
        return res[0]['rank'] or 0 if res and res[0]['found'] else 0

    def close(self):
        pass  # Chrome은 유지, close()는 모듈 함수로


# 모듈 수준 싱글턴
_tracker: CoupangRankTracker | None = None


def find_rank(keyword: str, coupang_product_id: str) -> int:
    global _tracker
    if _tracker is None:
        _tracker = CoupangRankTracker()
    return _tracker.find_rank(keyword, coupang_product_id)
