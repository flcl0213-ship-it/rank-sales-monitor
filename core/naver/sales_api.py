# -*- coding: utf-8 -*-
"""
네이버 커머스 API — 주문 조회 (판매 현황)
판매 기준: 주문 생성일 (order_date)
"""

import requests
import hashlib
import hmac
import time
import base64
from datetime import date, timedelta
from typing import List, Dict


def _get_token(client_id: str, client_secret: str) -> str:
    """네이버 커머스 API 액세스 토큰 발급"""
    timestamp = str(int(time.time() * 1000))
    pwd       = f"{client_id}_{timestamp}"
    hashed    = hmac.new(client_secret.encode(), pwd.encode(), hashlib.sha256).digest()
    signature = base64.b64encode(hashed).decode()

    resp = requests.post(
        "https://api.commerce.naver.com/external/v1/oauth2/token",
        data={
            "client_id":     client_id,
            "timestamp":     timestamp,
            "client_secret_sign": signature,
            "grant_type":    "client_credentials",
            "type":          "SELF",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_orders(client_id: str, client_secret: str,
               from_date: date = None, to_date: date = None) -> List[Dict]:
    """
    네이버 스마트스토어 주문 조회.

    Returns:
        [{'order_id': str, 'product_name': str, 'quantity': int,
          'revenue': int, 'order_date': str, 'status': str}, ...]
    """
    if not client_id or not client_secret:
        print("[WARN] 네이버 커머스 API 키 없음 — 판매 조회 건너뜀")
        return []

    if from_date is None:
        from_date = date.today() - timedelta(days=1)
    if to_date is None:
        to_date = date.today()

    try:
        token = _get_token(client_id, client_secret)
        headers = {"Authorization": f"Bearer {token}"}

        resp = requests.get(
            "https://api.commerce.naver.com/external/v1/pay-order/seller/orders/query-by-time",
            headers=headers,
            params={
                "from": from_date.isoformat() + "T00:00:00.000Z",
                "to":   to_date.isoformat()   + "T23:59:59.000Z",
                "orderStatus": "",  # 전체 상태
            },
            timeout=30,
        )
        resp.raise_for_status()
        raw_orders = resp.json().get("data", [])

        result = []
        for o in raw_orders:
            # 네이버 주문 구조에서 필요한 필드 추출
            product_orders = o.get("productOrderInfos", [])
            for po in product_orders:
                result.append({
                    "order_id":     po.get("productOrderId", ""),
                    "product_name": po.get("productName", ""),
                    "option_name":  po.get("optionContent", ""),
                    "quantity":     po.get("quantity", 1),
                    "revenue":      int(po.get("unitPrice", 0)) * int(po.get("quantity", 1)),
                    "order_date":   o.get("paymentDate", "")[:10],
                    "status":       po.get("productOrderStatus", ""),
                })
        return result

    except Exception as e:
        print(f"[ERROR] 네이버 주문 조회 실패: {e}")
        return []
