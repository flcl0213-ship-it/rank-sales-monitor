# -*- coding: utf-8 -*-
"""
DB CRUD 함수 모음
"""

from .models import get_conn
from datetime import date
from typing import List, Dict, Optional


# ════════════════════════════════
# 브랜드
# ════════════════════════════════

def get_all_brands(status='active') -> List[Dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM brands WHERE status=? ORDER BY id", (status,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_brand(data: Dict) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO brands
        (company_name, brand_name, naver_seller_id, naver_client_id, naver_client_secret,
         coupang_vendor_id, coupang_access_key, coupang_secret_key, memo)
        VALUES (:company_name, :brand_name, :naver_seller_id, :naver_client_id, :naver_client_secret,
                :coupang_vendor_id, :coupang_access_key, :coupang_secret_key, :memo)
    """, {
        'company_name':        data.get('company_name', ''),
        'brand_name':          data.get('brand_name', ''),
        'naver_seller_id':     data.get('naver_seller_id', ''),
        'naver_client_id':     data.get('naver_client_id', ''),
        'naver_client_secret': data.get('naver_client_secret', ''),
        'coupang_vendor_id':   data.get('coupang_vendor_id', ''),
        'coupang_access_key':  data.get('coupang_access_key', ''),
        'coupang_secret_key':  data.get('coupang_secret_key', ''),
        'memo':                data.get('memo', ''),
    })
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_brand(brand_id: int, data: Dict):
    conn = get_conn()
    conn.execute("""
        UPDATE brands SET
            company_name=:company_name, brand_name=:brand_name,
            naver_seller_id=:naver_seller_id, naver_client_id=:naver_client_id,
            naver_client_secret=:naver_client_secret, coupang_vendor_id=:coupang_vendor_id,
            coupang_access_key=:coupang_access_key, coupang_secret_key=:coupang_secret_key,
            memo=:memo
        WHERE id=:id
    """, {**data, 'id': brand_id})
    conn.commit()
    conn.close()


def delete_brand(brand_id: int):
    conn = get_conn()
    conn.execute("UPDATE brands SET status='inactive' WHERE id=?", (brand_id,))
    conn.commit()
    conn.close()


# ════════════════════════════════
# 네이버 상품
# ════════════════════════════════

def get_naver_products(brand_id: int = None, status='active') -> List[Dict]:
    conn = get_conn()
    if brand_id:
        rows = conn.execute("""
            SELECT np.*, b.brand_name FROM naver_products np
            JOIN brands b ON np.brand_id = b.id
            WHERE np.brand_id=? AND np.status=? ORDER BY np.id
        """, (brand_id, status)).fetchall()
    else:
        rows = conn.execute("""
            SELECT np.*, b.brand_name FROM naver_products np
            JOIN brands b ON np.brand_id = b.id
            WHERE np.status=? ORDER BY b.id, np.id
        """, (status,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_naver_product(data: Dict) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO naver_products
        (brand_id, model_name, product_name, seller, url_naver, naver_product_id)
        VALUES (:brand_id, :model_name, :product_name, :seller, :url_naver, :naver_product_id)
    """, {
        'brand_id':         data['brand_id'],
        'model_name':       data.get('model_name', ''),
        'product_name':     data.get('product_name', ''),
        'seller':           data.get('seller', ''),
        'url_naver':        data.get('url_naver', ''),
        'naver_product_id': data.get('naver_product_id', ''),
    })
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_naver_product(product_id: int, data: Dict):
    conn = get_conn()
    conn.execute("""
        UPDATE naver_products SET
            model_name=:model_name, product_name=:product_name,
            seller=:seller, url_naver=:url_naver, naver_product_id=:naver_product_id
        WHERE id=:id
    """, {**data, 'id': product_id})
    conn.commit()
    conn.close()


def delete_naver_product(product_id: int):
    conn = get_conn()
    conn.execute("UPDATE naver_products SET status='inactive' WHERE id=?", (product_id,))
    conn.commit()
    conn.close()


# ════════════════════════════════
# 쿠팡 상품
# ════════════════════════════════

def get_coupang_products(brand_id: int = None, status='active') -> List[Dict]:
    conn = get_conn()
    if brand_id:
        rows = conn.execute("""
            SELECT cp.*, b.brand_name FROM coupang_products cp
            JOIN brands b ON cp.brand_id = b.id
            WHERE cp.brand_id=? AND cp.status=? ORDER BY cp.id
        """, (brand_id, status)).fetchall()
    else:
        rows = conn.execute("""
            SELECT cp.*, b.brand_name FROM coupang_products cp
            JOIN brands b ON cp.brand_id = b.id
            WHERE cp.status=? ORDER BY b.id, cp.id
        """, (status,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_coupang_product(data: Dict) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO coupang_products
        (brand_id, model_name, product_name, url_coupang, coupang_product_id)
        VALUES (:brand_id, :model_name, :product_name, :url_coupang, :coupang_product_id)
    """, {
        'brand_id':           data['brand_id'],
        'model_name':         data.get('model_name', ''),
        'product_name':       data.get('product_name', ''),
        'url_coupang':        data.get('url_coupang', ''),
        'coupang_product_id': data.get('coupang_product_id', ''),
    })
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_coupang_product(product_id: int, data: Dict):
    conn = get_conn()
    conn.execute("""
        UPDATE coupang_products SET
            model_name=:model_name, product_name=:product_name,
            url_coupang=:url_coupang, coupang_product_id=:coupang_product_id
        WHERE id=:id
    """, {**data, 'id': product_id})
    conn.commit()
    conn.close()


def delete_coupang_product(product_id: int):
    conn = get_conn()
    conn.execute("UPDATE coupang_products SET status='inactive' WHERE id=?", (product_id,))
    conn.commit()
    conn.close()


# ════════════════════════════════
# 키워드 (네이버 전용)
# ════════════════════════════════

def get_keywords(product_id: int, platform: str = 'naver') -> List[Dict]:
    conn = get_conn()
    if platform == 'naver':
        rows = conn.execute(
            "SELECT * FROM keywords WHERE naver_product_id=? AND status='active' ORDER BY type DESC, sort_order",
            (product_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM keywords WHERE coupang_product_id=? AND status='active' ORDER BY type DESC, sort_order",
            (product_id,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_keyword(product_id: int, keyword: str, ktype: str = 'sub',
                sort_order: int = 0, platform: str = 'naver') -> int:
    conn = get_conn()
    c = conn.cursor()
    if platform == 'naver':
        c.execute("""
            INSERT INTO keywords (naver_product_id, keyword, type, sort_order)
            VALUES (?, ?, ?, ?)
        """, (product_id, keyword, ktype, sort_order))
    else:
        c.execute("""
            INSERT INTO keywords (coupang_product_id, keyword, type, sort_order)
            VALUES (?, ?, ?, ?)
        """, (product_id, keyword, ktype, sort_order))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id


def delete_keyword(keyword_id: int):
    conn = get_conn()
    conn.execute("UPDATE keywords SET status='inactive' WHERE id=?", (keyword_id,))
    conn.commit()
    conn.close()


# ════════════════════════════════
# 순위 저장 / 조회
# ════════════════════════════════

def save_rank(naver_product_id: int, keyword_id: int, keyword_type: str,
              rank: int, checked_date: date = None):
    if checked_date is None:
        checked_date = date.today()
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO rank_history
        (naver_product_id, keyword_id, keyword_type, rank, checked_date)
        VALUES (?, ?, ?, ?, ?)
    """, (naver_product_id, keyword_id, keyword_type, rank, str(checked_date)))
    conn.commit()
    conn.close()


def get_naver_ranks_for_display(days: int = 7, brand_filter: str = '전체') -> List[Dict]:
    """네이버 현황 탭: 대표 키워드 순위 7일치"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            np.id as product_id, np.model_name, np.product_name,
            np.url_naver, np.seller,
            b.company_name, b.brand_name,
            k.id as keyword_id, k.keyword, k.type as keyword_type,
            rh.rank, rh.checked_date
        FROM naver_products np
        JOIN brands b ON np.brand_id = b.id
        JOIN keywords k ON k.naver_product_id = np.id AND k.type='main' AND k.status='active'
        LEFT JOIN rank_history rh ON rh.naver_product_id = np.id AND rh.keyword_id = k.id
            AND rh.checked_date >= date('now', ? || ' days')
        WHERE np.status='active' AND b.status='active'
        ORDER BY b.id, np.id, rh.checked_date DESC
    """, (f'-{days}',)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_sub_ranks_for_display(days: int = 7) -> List[Dict]:
    """서브 키워드 탭: 서브 키워드 순위 7일치"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            np.id as product_id, np.model_name, np.product_name,
            b.brand_name,
            k.id as keyword_id, k.keyword,
            rh.rank, rh.checked_date
        FROM naver_products np
        JOIN brands b ON np.brand_id = b.id
        JOIN keywords k ON k.naver_product_id = np.id AND k.type='sub' AND k.status='active'
        LEFT JOIN rank_history rh ON rh.naver_product_id = np.id AND rh.keyword_id = k.id
            AND rh.checked_date >= date('now', ? || ' days')
        WHERE np.status='active' AND b.status='active'
        ORDER BY b.id, np.id, k.sort_order, rh.checked_date DESC
    """, (f'-{days}',)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ════════════════════════════════
# 주문 저장 / 집계
# ════════════════════════════════

def save_order(order_id: str, brand_id: int, platform: str,
               quantity: int, revenue: int, order_date: str,
               naver_product_id: int = None, coupang_product_id: int = None,
               option_name: str = '', status: str = '') -> bool:
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO orders
            (order_id, naver_product_id, coupang_product_id, brand_id, platform,
             option_name, quantity, revenue, order_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (order_id, naver_product_id, coupang_product_id, brand_id, platform,
              option_name, quantity, revenue, order_date, status))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_naver_daily_sales(days: int = 7, brand_filter: str = '전체') -> List[Dict]:
    """네이버 일별 판매 — 상품+옵션별"""
    conn = get_conn()
    rows = conn.execute(f"""
        SELECT
            np.id as product_id, np.model_name, np.product_name,
            b.company_name, b.brand_name,
            o.option_name, o.order_date,
            SUM(o.quantity) as total_qty,
            SUM(o.revenue)  as total_revenue
        FROM orders o
        JOIN naver_products np ON o.naver_product_id = np.id
        JOIN brands b ON o.brand_id = b.id
        WHERE o.order_date >= date('now', '-{days} days') AND o.platform='naver'
        GROUP BY o.naver_product_id, o.option_name, o.order_date
        ORDER BY b.id, np.id, o.order_date DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_coupang_daily_sales(days: int = 7, brand_filter: str = '전체') -> List[Dict]:
    """쿠팡 일별 판매 — 상품별"""
    conn = get_conn()
    rows = conn.execute(f"""
        SELECT
            cp.id as product_id, cp.model_name, cp.product_name,
            b.company_name, b.brand_name,
            o.order_date,
            SUM(o.quantity) as total_qty,
            SUM(o.revenue)  as total_revenue
        FROM orders o
        JOIN coupang_products cp ON o.coupang_product_id = cp.id
        JOIN brands b ON o.brand_id = b.id
        WHERE o.order_date >= date('now', '-{days} days') AND o.platform='coupang'
        GROUP BY o.coupang_product_id, o.order_date
        ORDER BY b.id, cp.id, o.order_date DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]
