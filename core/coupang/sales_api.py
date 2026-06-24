# -*- coding: utf-8 -*-
"""
쿠팡 Wing API — 주문 조회 (판매 현황)
판매 기준: 주문 생성일 (order_date)
"""

import requests
import hashlib
import hmac
import urllib.parse
from datetime import date, datetime, timedelta
from typing import List, Dict


def _sign(method: str, path: str, query: str,
          access_key: str, secret_key: str) -> dict:
    """쿠팡 API HMAC-SHA256 서명 생성"""
    datetime_str = datetime.utcnow().strftime("%y%m%dT%H%M%SZ")
    message = f"{datetime_str}{method}{path}{query}"
    signature = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
    return {
        "Authorization": (
            f"CEA algorithm=HmacSHA256, access-key={access_key}, "
            f"signed-date={datetime_str}, signature={signature}"
        ),
        "Content-Type": "application/json;charset=UTF-8",
    }


def get_orders(vendor_id: str, access_key: str, secret_key: str,
               from_date: date = None, to_date: date = None) -> List[Dict]:
    """
    쿠팡 주문 조회.

    Returns:
        [{'order_id': str, 'product_name': str, 'quantity': int,
          'revenue': int, 'order_date': str, 'status': str}, ...]
    """
    if not vendor_id or not access_key or not secret_key:
        print("[WARN] 쿠팡 API 키 없음 — 판매 조회 건너뜀")
        return []

    if from_date is None:
        from_date = date.today() - timedelta(days=1)
    if to_date is None:
        to_date = date.today()

    try:
        path  = f"/v2/providers/openapi/apis/api/v4/vendors/{vendor_id}/ordersheets"
        query = (
            f"createdAtFrom={from_date.isoformat()}T00:00:00"
            f"&createdAtTo={to_date.isoformat()}T23:59:59"
            f"&status=ACCEPT"
        )
        headers = _sign("GET", path, query, access_key, secret_key)
        resp = requests.get(
            f"https://api-gateway.coupang.com{path}?{query}",
            headers=headers,
            timeout=30,
        )
        if not resp.ok:
            print(f"[ERROR] 쿠팡 응답: {resp.status_code} {resp.text[:300]}")
        resp.raise_for_status()

        raw = resp.json().get("data", {}).get("content", [])
        result = []
        for sheet in raw:
            for item in sheet.get("orderedItems", []):
                result.append({
                    "order_id":     str(sheet.get("orderId", "")),
                    "product_name": item.get("productName", ""),
                    "quantity":     item.get("shippingCount", 1),
                    "revenue":      int(item.get("orderPrice", 0)),
                    "order_date":   sheet.get("orderedAt", "")[:10],
                    "status":       sheet.get("status", ""),
                })
        return result

    except Exception as e:
        print(f"[ERROR] 쿠팡 주문 조회 실패: {e}")
        return []
