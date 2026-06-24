# -*- coding: utf-8 -*-
"""
네이버 커머스 API — 주문 조회 (판매 현황)
판매 기준: 주문 생성일 (order_date)
"""

import requests
import time
import base64
import bcrypt
from datetime import date, datetime, timedelta, timezone
from typing import List, Dict

KST = timezone(timedelta(hours=9))
CUTOFF_HOUR   = 15
CUTOFF_MINUTE = 40


def _cutoff_utc(d: date, offset_days: int = 0) -> str:
    """d + offset_days 일의 15:40 KST → UTC ISO 문자열"""
    target = d + timedelta(days=offset_days)
    dt_kst = datetime(target.year, target.month, target.day,
                      CUTOFF_HOUR, CUTOFF_MINUTE, 0, tzinfo=KST)
    dt_utc = dt_kst.astimezone(timezone.utc)
    return dt_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z')


def _get_token(client_id: str, client_secret: str) -> str:
    """네이버 커머스 API 액세스 토큰 발급"""
    timestamp = str(int(time.time() * 1000))
    password  = f"{client_id}_{timestamp}"
    hashed    = bcrypt.hashpw(password.encode('utf-8'), client_secret.encode('utf-8'))
    signature = base64.b64encode(hashed).decode('utf-8')

    resp = requests.post(
        "https://api.commerce.naver.com/external/v1/oauth2/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_id":          client_id,
            "timestamp":          timestamp,
            "client_secret_sign": signature,
            "grant_type":         "client_credentials",
            "type":               "SELF",
        },
        timeout=10,
    )
    if not resp.ok:
        print(f"[ERROR] 토큰 발급 실패 {resp.status_code}: {resp.text[:200]}")

    resp.raise_for_status()
    return resp.json()["access_token"]


def get_orders(client_id: str, client_secret: str,
               target_date: date = None) -> List[Dict]:
    """
    네이버 스마트스토어 주문 조회.
    수집 범위: target_date-1일 15:40 KST ~ target_date 15:40 KST (24시간)

    Returns:
        [{'order_id': str, 'product_name': str, 'quantity': int,
          'revenue': int, 'order_date': str, 'status': str}, ...]
    """
    if not client_id or not client_secret:
        print("[WARN] 네이버 커머스 API 키 없음 — 판매 조회 건너뜀")
        return []

    if target_date is None:
        target_date = date.today()

    from_str = _cutoff_utc(target_date, -1)  # 전일 15:40 KST
    to_str   = _cutoff_utc(target_date,  0)  # 당일 15:40 KST
    print(f"  [네이버] 조회 범위: {from_str} ~ {to_str}")

    try:
        token = _get_token(client_id, client_secret)
        headers = {"Authorization": f"Bearer {token}"}

        resp = requests.get(
            "https://api.commerce.naver.com/external/v1/pay-order/seller/product-orders",
            headers=headers,
            params={"from": from_str, "to": to_str},
            timeout=30,
        )
        resp.raise_for_status()
        contents = resp.json().get("data", {}).get("contents", [])

        result = []
        for item in contents:
            c  = item.get("content", {})
            po = c.get("productOrder", {})
            o  = c.get("order", {})
            # 영업일 기준 날짜: target_date (15:40 컷오프 기준)
            result.append({
                "order_id":     po.get("productOrderId", ""),
                "product_name": po.get("productName", ""),
                "quantity":     int(po.get("quantity", 1)),
                "revenue":      int(po.get("totalPaymentAmount", 0)),
                "order_date":   target_date.isoformat(),
                "status":       po.get("productOrderStatus", ""),
            })
        return result

    except Exception as e:
        print(f"[ERROR] 네이버 주문 조회 실패: {e}")
        return []
