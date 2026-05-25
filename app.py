import json
import uuid
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(page_title="카드 실적 매니저", page_icon="💳", layout="wide")

DATA_FILE = Path(__file__).with_name("cardmanager_data.json")

COMPANY_RULES = {
    "신한카드": {"gift_limit": 1_000_000},
    "삼성카드": {"gift_limit": 1_000_000},
    "카드사 미정": {"gift_limit": 1_000_000},
}

CARD_DB = {
    "RPM": {
        "company": "신한카드",
        "tiers": [
            {"level": 0, "name": "0구간", "min": 0},
            {"level": 1, "name": "1구간", "min": 500_000},
            {"level": 2, "name": "2구간", "min": 1_000_000},
            {"level": 3, "name": "3구간", "min": 1_500_000},
        ],
        "benefits_by_tier": {
            0: ["특별 적립 1.0%", "일반 적립 0.2%"],
            1: ["특별 적립 2.0%", "일반 적립 0.8%"],
            2: ["특별 적립 3.5%", "일반 적립 1.5%"],
            3: ["특별 적립 5.0%", "일반 적립 2.0%"],
        },
        "spend_categories": {
            "일반결제": {"counts_for_tier": True},
            "특별적립 가맹점": {"counts_for_tier": True},
            "상품권": {"counts_for_tier": True, "gift_group": "company"},
            "실적제외": {"counts_for_tier": False},
        },
        "benefit_rules": {
            "무료주차": {"limit": 3, "period": "monthly"},
            "공항라운지": {"limit": 2, "period": "yearly"},
            "발레파킹": {"limit": 3, "period": "monthly"},
        },
        "cashback_pools": {},
    },
    "Deep Eco": {
        "company": "신한카드",
        "tiers": [
            {"level": 0, "name": "실적 미달", "min": 0},
            {"level": 1, "name": "30만 이상", "min": 300_000},
        ],
        "benefits_by_tier": {
            0: ["전월 실적 미달"],
            1: ["통합 캐시백 한도 3만 원", "대중교통/온라인/상품권 5% 캐시백"],
        },
        "spend_categories": {
            "일반결제": {"counts_for_tier": True},
            "5% 캐시백 대상": {
                "counts_for_tier": True,
                "cashback_rate": 0.05,
                "cashback_pool": "eco_cashback",
                "requires_prev_tier": 1,
            },
            "상품권": {
                "counts_for_tier": True,
                "gift_group": "company",
                "cashback_rate": 0.05,
                "cashback_pool": "eco_cashback",
                "requires_prev_tier": 1,
            },
            "실적제외": {"counts_for_tier": False},
        },
        "benefit_rules": {
            "스벅 사이렌오더": {
                "limit": 5,
                "period": "monthly",
                "cashback_per_use": 1_000,
                "cashback_pool": "eco_cashback",
                "requires_prev_tier": 1,
            },
            "만보기 15일 달성": {
                "limit": 1,
                "period": "monthly",
                "cashback_per_use": 5_000,
                "cashback_pool": "walkon_reward",
                "requires_prev_tier": 1,
            },
        },
        "cashback_pools": {
            "eco_cashback": {"name": "통합 캐시백", "monthly_cap": 30_000},
            "walkon_reward": {"name": "만보기 리워드", "monthly_cap": 5_000},
        },
    },
    "taptap": {
        "company": "삼성카드",
        "tiers": [
            {"level": 0, "name": "기본", "min": 0},
