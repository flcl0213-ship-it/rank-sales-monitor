# -*- coding: utf-8 -*-
"""
DB 테이블 생성 및 초기화
"""

import sqlite3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    # 브랜드 (회사)
    c.execute("""
    CREATE TABLE IF NOT EXISTS brands (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name        TEXT NOT NULL,
        brand_name          TEXT NOT NULL,
        naver_seller_id     TEXT DEFAULT '',
        naver_client_id     TEXT DEFAULT '',
        naver_client_secret TEXT DEFAULT '',
        coupang_vendor_id   TEXT DEFAULT '',
        coupang_access_key  TEXT DEFAULT '',
        coupang_secret_key  TEXT DEFAULT '',
        status              TEXT DEFAULT 'active',
        memo                TEXT DEFAULT '',
        created_at          DATETIME DEFAULT (datetime('now','localtime'))
    )""")

    # 네이버 상품 (순위 체크 + 판매 기준)
    c.execute("""
    CREATE TABLE IF NOT EXISTS naver_products (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_id         INTEGER NOT NULL REFERENCES brands(id),
        model_name       TEXT DEFAULT '',
        product_name     TEXT NOT NULL,
        seller           TEXT DEFAULT '',
        url_naver        TEXT DEFAULT '',
        naver_product_id TEXT DEFAULT '',
        status           TEXT DEFAULT 'active',
        created_at       DATETIME DEFAULT (datetime('now','localtime'))
    )""")

    # 쿠팡 상품 (옵션 포함된 전체 상품명)
    c.execute("""
    CREATE TABLE IF NOT EXISTS coupang_products (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_id            INTEGER NOT NULL REFERENCES brands(id),
        model_name          TEXT DEFAULT '',
        product_name        TEXT NOT NULL,
        url_coupang         TEXT DEFAULT '',
        coupang_product_id  TEXT DEFAULT '',
        status              TEXT DEFAULT 'active',
        created_at          DATETIME DEFAULT (datetime('now','localtime'))
    )""")

    # 키워드 (네이버 또는 쿠팡 상품에 연결)
    c.execute("""
    CREATE TABLE IF NOT EXISTS keywords (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        naver_product_id    INTEGER REFERENCES naver_products(id),
        coupang_product_id  INTEGER REFERENCES coupang_products(id),
        keyword             TEXT NOT NULL,
        type                TEXT DEFAULT 'sub',   -- main(대표) / sub(서브)
        sort_order          INTEGER DEFAULT 0,
        status              TEXT DEFAULT 'active'
    )""")

    # 순위 기록 (네이버 + 쿠팡 공통) — 기존 테이블이면 _migrate_rank_history가 컬럼 추가
    c.execute("""
    CREATE TABLE IF NOT EXISTS rank_history (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        naver_product_id    INTEGER REFERENCES naver_products(id),
        coupang_product_id  INTEGER REFERENCES coupang_products(id),
        keyword_id          INTEGER NOT NULL REFERENCES keywords(id),
        keyword_type        TEXT DEFAULT 'sub',
        rank                INTEGER DEFAULT 0,
        checked_date        DATE NOT NULL,
        checked_at          DATETIME DEFAULT (datetime('now','localtime')),
        UNIQUE(naver_product_id, keyword_id, checked_date)
    )""")
    conn.commit()

    _migrate_rank_history(conn)  # 기존 DB: coupang_product_id 컬럼 + 인덱스 추가

    c.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_rank_coupang
    ON rank_history(coupang_product_id, keyword_id, checked_date)
    WHERE coupang_product_id IS NOT NULL""")
    c.execute("""
    CREATE INDEX IF NOT EXISTS idx_rank_product_date
    ON rank_history(naver_product_id, checked_date)""")

    # 주문 (네이버/쿠팡 공통)
    c.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id            TEXT NOT NULL UNIQUE,
        naver_product_id    INTEGER REFERENCES naver_products(id),
        coupang_product_id  INTEGER REFERENCES coupang_products(id),
        brand_id            INTEGER REFERENCES brands(id),
        platform            TEXT NOT NULL,
        option_name         TEXT DEFAULT '',   -- 네이버 옵션명
        quantity            INTEGER DEFAULT 1,
        revenue             INTEGER DEFAULT 0,
        order_date          DATE NOT NULL,
        status              TEXT DEFAULT '',
        created_at          DATETIME DEFAULT (datetime('now','localtime'))
    )""")
    c.execute("""
    CREATE INDEX IF NOT EXISTS idx_orders_date
    ON orders(order_date, platform)""")

    # 트래픽현황 컬럼명 (사용자 정의 4개)
    c.execute("""
    CREATE TABLE IF NOT EXISTS traffic_columns (
        col_index INTEGER PRIMARY KEY,
        col_name  TEXT DEFAULT ''
    )""")
    for i in range(4):
        c.execute("INSERT OR IGNORE INTO traffic_columns VALUES (?, '')", (i,))

    # 트래픽현황 데이터 (상품별 × 컬럼별)
    c.execute("""
    CREATE TABLE IF NOT EXISTS traffic_data (
        naver_product_id INTEGER NOT NULL REFERENCES naver_products(id),
        col_index        INTEGER NOT NULL,
        value            TEXT DEFAULT '',
        PRIMARY KEY (naver_product_id, col_index)
    )""")

    conn.commit()
    conn.close()
    print(f"DB 초기화 완료: {DB_PATH}")


def _migrate_rank_history(conn):
    """기존 rank_history에 coupang_product_id 컬럼 추가 (마이그레이션)"""
    cols = {c[1] for c in conn.execute('PRAGMA table_info(rank_history)').fetchall()}
    if 'coupang_product_id' in cols:
        return

    conn.executescript("""
        ALTER TABLE rank_history RENAME TO _rank_history_old;

        CREATE TABLE rank_history (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            naver_product_id    INTEGER REFERENCES naver_products(id),
            coupang_product_id  INTEGER REFERENCES coupang_products(id),
            keyword_id          INTEGER NOT NULL REFERENCES keywords(id),
            keyword_type        TEXT DEFAULT 'sub',
            rank                INTEGER DEFAULT 0,
            checked_date        DATE NOT NULL,
            checked_at          DATETIME DEFAULT (datetime('now','localtime')),
            UNIQUE(naver_product_id, keyword_id, checked_date)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_rank_coupang
        ON rank_history(coupang_product_id, keyword_id, checked_date)
        WHERE coupang_product_id IS NOT NULL;

        CREATE INDEX IF NOT EXISTS idx_rank_product_date
        ON rank_history(naver_product_id, checked_date);

        INSERT INTO rank_history
            (id, naver_product_id, keyword_id, keyword_type, rank, checked_date, checked_at)
        SELECT id, naver_product_id, keyword_id, keyword_type, rank, checked_date, checked_at
        FROM _rank_history_old;

        DROP TABLE _rank_history_old;
    """)
    print("DB 마이그레이션 완료: rank_history + coupang_product_id")


if __name__ == '__main__':
    init_db()
