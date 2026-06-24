# -*- coding: utf-8 -*-
"""
네이버 검색광고 API — 키워드 추천 + 검색량 조회
searchad.naver.com 에서 발급받은 키 사용
"""

import hmac
import hashlib
import base64
import time
import requests
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import NAVER_AD_CUSTOMER_ID, NAVER_AD_ACCESS_KEY, NAVER_AD_SECRET_KEY

BASE_URL = "https://api.naver.com"


def _sign(timestamp: str, method: str, path: str) -> str:
    msg = f"{timestamp}.{method}.{path}"
    sig = hmac.new(NAVER_AD_SECRET_KEY.encode(), msg.encode(), hashlib.sha256).digest()
    return base64.b64encode(sig).decode()


def _headers(method: str, path: str) -> dict:
    ts = str(int(time.time() * 1000))
    return {
        "X-Timestamp":  ts,
        "X-API-KEY":    NAVER_AD_ACCESS_KEY,
        "X-Customer":   NAVER_AD_CUSTOMER_ID,
        "X-Signature":  _sign(ts, method, path),
        "Content-Type": "application/json",
    }


def get_related_keywords(seed_keyword: str, top_n: int = 100):
    """
    씨앗 키워드로 연관 키워드 + 월간 검색량 반환.

    Returns:
        [{'keyword': str, 'pc': int, 'mobile': int, 'total': int, 'competition': str}, ...]
        total 기준 내림차순 정렬
    """
    path = "/keywordstool"
    params = {"hintKeywords": seed_keyword, "showDetail": "1"}
    try:
        resp = requests.get(
            BASE_URL + path,
            headers=_headers("GET", path),
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        raw = resp.json().get("keywordList", [])

        result = []
        for item in raw:
            pc  = item.get("monthlyPcQcCnt", 0)
            mob = item.get("monthlyMobileQcCnt", 0)
            # "< 10" 같은 문자열 처리
            try: pc  = int(pc)
            except: pc = 0
            try: mob = int(mob)
            except: mob = 0

            comp_map = {"낮음": "낮음", "보통": "보통", "높음": "높음",
                        "low": "낮음", "mid": "보통", "high": "높음"}
            comp = comp_map.get(str(item.get("compIdx", "")), str(item.get("compIdx", "-")))

            result.append({
                "keyword":     item.get("relKeyword", ""),
                "pc":          pc,
                "mobile":      mob,
                "total":       pc + mob,
                "competition": comp,
            })

        result.sort(key=lambda x: x["total"], reverse=True)
        return result[:top_n]

    except Exception as e:
        print(f"[ERROR] 검색광고 API 오류: {e}")
        return []


def get_search_volume(keywords: list) -> dict:
    """
    키워드 리스트의 월간 검색량 반환.

    Returns:
        {keyword: {'pc': int, 'mobile': int, 'total': int}, ...}
    """
    if not keywords:
        return {}
    path = "/keywordstool"
    # API는 한 번에 최대 5개 씨앗 키워드
    result = {}
    for i in range(0, len(keywords), 5):
        batch = keywords[i:i+5]
        params = {"hintKeywords": "|".join(batch), "showDetail": "1"}
        try:
            resp = requests.get(
                BASE_URL + path,
                headers=_headers("GET", path),
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            for item in resp.json().get("keywordList", []):
                kw  = item.get("relKeyword", "")
                pc  = item.get("monthlyPcQcCnt", 0)
                mob = item.get("monthlyMobileQcCnt", 0)
                try: pc  = int(pc)
                except: pc = 0
                try: mob = int(mob)
                except: mob = 0
                if kw in batch:
                    result[kw] = {"pc": pc, "mobile": mob, "total": pc + mob}
        except Exception as e:
            print(f"[ERROR] 검색량 조회 오류: {e}")
    return result
