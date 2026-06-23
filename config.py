# -*- coding: utf-8 -*-
"""
설정 파일 — API 키와 경로를 여기에 입력합니다.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOG_DIR  = os.path.join(DATA_DIR, 'logs')
DB_PATH  = os.path.join(DATA_DIR, 'monitor.db')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR,  exist_ok=True)

# ─────────────────────────────────────────────
# ① 네이버 검색 API (순위 체크용) — 공통 1개
# developers.naver.com → 애플리케이션 등록 → 검색 API
# ─────────────────────────────────────────────
NAVER_SEARCH_CLIENT_ID     = ""   # 여기에 입력
NAVER_SEARCH_CLIENT_SECRET = ""   # 여기에 입력

# ─────────────────────────────────────────────
# ② 브랜드별 API 키 목록
#    네이버 커머스 API : sell.smartstore.naver.com → 판매자정보 → API관리
#    쿠팡 Wing API    : wing.coupang.com → 마이페이지 → 오픈API관리
# ─────────────────────────────────────────────
BRAND_API_KEYS = [
    # 예시 형식 (실제 키 받으면 아래처럼 추가)
    # {
    #     "brand_name": "삼성",
    #     "naver_client_id": "",
    #     "naver_client_secret": "",
    #     "coupang_access_key": "",
    #     "coupang_secret_key": "",
    #     "coupang_vendor_id": "",
    # },
]

# ─────────────────────────────────────────────
# 스케줄 설정
# ─────────────────────────────────────────────
RANK_CHECK_HOUR    = 9   # 순위 체크 시간 (오전 9시)
SALES_CHECK_MORNING = 9  # 판매 체크 오전
SALES_CHECK_EVENING = 18 # 판매 체크 오후

# 순위 체크 최대 페이지 (한 페이지 = 40개 상품)
RANK_MAX_PAGES = 5  # 최대 200위까지 탐색
