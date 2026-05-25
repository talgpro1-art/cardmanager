import json
import uuid
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title='카드 실적 매니저', page_icon='💳', layout='wide')

DATA_FILE = Path(__file__).with_name('cardmanager_data.json')

COMPANY_RULES = {
    '신한카드': {'gift_limit': 1_000_000},
}

LIFESTYLE_DISCOUNT_TIERS = [
    {'min_usage': 300_000, 'rate': 0.10, 'cap': 10_000},
    {'min_usage': 500_000, 'rate': 0.10, 'cap': 20_000},
]

CARD_DB = {
    'RPM': {
        'company': '신한카드',
        'tiers': [
            {'level': 0, 'name': '0구간', 'min': 0},
            {'level': 1, 'name': '1구간', 'min': 500_000},
            {'level': 2, 'name': '2구간', 'min': 1_000_000},
            {'level': 3, 'name': '3구간', 'min': 1_500_000},
        ],
        'benefits_by_tier': {
            0: ['특별 적립 1.0%', '일반 적립 0.2%'],
            1: ['특별 적립 2.0%', '일반 적립 0.8%'],
            2: ['특별 적립 3.5%', '일반 적립 1.5%'],
            3: ['특별 적립 5.0%', '일반 적립 2.0%'],
        },
        'spend_categories': {
            '일반결제': {'counts_for_tier': True},
            '특별적립 가맹점': {'counts_for_tier': True},
            '상품권': {'counts_for_tier': True, 'gift_group': 'company'},
            '실적제외': {'counts_for_tier': False},
        },
        'benefit_rules': {
            '무료주차': {'limit': 3, 'period': 'monthly'},
            '공항라운지': {'limit': 2, 'period': 'yearly'},
            '발레파킹': {'limit': 3, 'period': 'monthly'},
        },
        'cashback_pools': {},
    },
    'Deep Eco': {
        'company': '신한카드',
        'tiers': [
            {'level': 0, 'name': '실적 미달', 'min': 0},
            {'level': 1, 'name': '30만 이상', 'min': 300_000},
        ],
        'benefits_by_tier': {
            0: ['전월 실적 미달'],
            1: ['통합 캐시백 한도 3만 원', '대중교통/온라인/상품권 5% 캐시백'],
        },
        'spend_categories': {
            '일반결제': {'counts_for_tier': True},
            '5% 캐시백 대상': {
                'counts_for_tier': True,
                'cashback_rate': 0.05,
                'cashback_pool': 'eco_cashback',
                'requires_prev_tier': 1,
            },
            '상품권': {
                'counts_for_tier': True,
                'gift_group': 'company',
                'cashback_rate': 0.05,
                'cashback_pool': 'eco_cashback',
                'requires_prev_tier': 1,
            },
            '실적제외': {'counts_for_tier': False},
        },
        'benefit_rules': {
            '스벅 사이렌오더': {
                'limit': 5,
                'period': 'monthly',
                'cashback_per_use': 1_000,
                'cashback_pool': 'eco_cashback',
                'requires_prev_tier': 1,
            },
            '만보기 15일 달성': {
                'limit': 1,
                'period': 'monthly',
                'cashback_per_use': 5_000,
                'cashback_pool': 'walkon_reward',
                'requires_prev_tier': 1,
            },
        },
        'cashback_pools': {
            'eco_cashback': {'name': '통합 캐시백', 'monthly_cap': 30_000},
            'walkon_reward': {'name': '만보기 리워드', 'monthly_cap': 5_000},
        },
    },
    '더모아': {
        'company': '신한카드',
        'tiers': [
            {'level': 0, 'name': '실적 미달', 'min': 0},
            {'level': 1, 'name': '30만 이상', 'min': 300_000},
        ],
        'benefits_by_tier': {
            0: ['전월 실적 미달'],
            1: ['5천 원 이상 결제 시 1천 원 미만 금액 포인트 적립', '더블적립처(배민/요기요/해외결제)는 2배 적립'],
        },
        'spend_categories': {
            '일반결제': {
                'counts_for_tier': True,
                'more_point_multiplier': 1,
                'more_point_pool': 'more_points',
                'more_point_min': 5_000,
                'requires_prev_tier': 1,
            },
            '더블적립처': {
                'counts_for_tier': True,
                'more_point_multiplier': 2,
                'more_point_pool': 'more_points',
                'more_point_min': 5_000,
                'requires_prev_tier': 1,
            },
            '실적제외': {'counts_for_tier': False},
        },
        'benefit_rules': {},
        'cashback_pools': {
            'more_points': {'name': '다음달 예상 포인트', 'monthly_cap': None},
        },
    },
    '신한 EV': {
        'company': '신한카드',
        'tiers': [
            {'level': 0, 'name': '실적 미달', 'min': 0},
            {'level': 1, 'name': '30만 이상', 'min': 300_000},
            {'level': 2, 'name': '50만 이상', 'min': 500_000},
            {'level': 3, 'name': '60만 이상', 'min': 600_000},
        ],
        'benefits_by_tier': {
            0: ['전월 실적 미달'],
            1: ['전기차 충전 30% 할인(2만 원 한도)', '생활할인 10%(1만 원 한도)'],
            2: ['전기차 충전 30% 할인(2만 원 한도)', '생활할인 10%(2만 원 한도)'],
            3: ['전기차 충전 50% 할인(2만 원 한도)', '생활할인 10%(2만 원 한도)'],
        },
        'spend_categories': {
            '일반결제': {'counts_for_tier': True},
            '전기차충전': {
                'counts_for_tier': True,
                'discount_pool': 'ev_charging',
                'discount_tiers': [
                    {'min_usage': 300_000, 'rate': 0.30, 'cap': 20_000},
                    {'min_usage': 600_000, 'rate': 0.50, 'cap': 20_000},
                ],
            },
            '생활할인-편의점': {'counts_for_tier': True, 'discount_pool': 'ev_lifestyle', 'discount_tiers': LIFESTYLE_DISCOUNT_TIERS},
            '생활할인-병원/약국': {'counts_for_tier': True, 'discount_pool': 'ev_lifestyle', 'discount_tiers': LIFESTYLE_DISCOUNT_TIERS},
            '생활할인-3대마트(주말)': {
                'counts_for_tier': True,
                'discount_pool': 'ev_lifestyle',
                'discount_tiers': LIFESTYLE_DISCOUNT_TIERS,
                'category_monthly_cap': 5_000,
            },
            '생활할인-지하철': {'counts_for_tier': True, 'discount_pool': 'ev_lifestyle', 'discount_tiers': LIFESTYLE_DISCOUNT_TIERS},
            '생활할인-택시': {'counts_for_tier': True, 'discount_pool': 'ev_lifestyle', 'discount_tiers': LIFESTYLE_DISCOUNT_TIERS},
            '생활할인-커피': {'counts_for_tier': True, 'discount_pool': 'ev_lifestyle', 'discount_tiers': LIFESTYLE_DISCOUNT_TIERS},
            '실적제외': {'counts_for_tier': False},
        },
        'benefit_rules': {},
        'cashback_pools': {
            'ev_charging': {'name': '전기차 충전 할인', 'monthly_cap': None},
            'ev_lifestyle': {'name': '생활할인', 'monthly_cap': None},
        },
    },
}


def default_data():
    return {
        'transactions': [],
        'manual_prev_usage': {card_name: 0 for card_name in CARD_DB},
        'updated_at': datetime.now().isoformat(timespec='seconds'),
    }


def ensure_data_shape(data):
    shaped = deepcopy(default_data())
    if isinstance(data, dict):
        if isinstance(data.get('transactions'), list):
            shaped['transactions'] = data['transactions']
        if isinstance(data.get('manual_prev_usage'), dict):
            shaped['manual_prev_usage'].update(data['manual_prev_usage'])
    for card_name in CARD_DB:
        shaped['manual_prev_usage'].setdefault(card_name, 0)
    return shaped


def load_data():
    if not DATA_FILE.exists():
        return default_data()
    try:
        with DATA_FILE.open('r', encoding='utf-8') as file:
            return ensure_data_shape(json.load(file))
    except Exception:
        return default_data()


def save_data(data):
    data['updated_at'] = datetime.now().isoformat(timespec='seconds')
    try:
        with DATA_FILE.open('w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
    except OSError:
        st.warning('현재 환경에서는 파일 저장이 제한될 수 있습니다. 세션 중에는 계속 사용할 수 있습니다.')


def money(value):
    return f'{int(round(value)):,} 원'


def ratio(value):
    return max(0.0, min(float(value), 1.0))


def month_key(value):
    if isinstance(value, date):
        return value.strftime('%Y-%m')
    return str(value)[:7]


def previous_month_key(key):
    year, month = [int(part) for part in key.split('-')]
    if month == 1:
        return f'{year - 1}-12'
    return f'{year}-{month - 1:02d}'


def next_month_key(key):
    year, month = [int(part) for part in key.split('-')]
    if month == 12:
        return f'{year + 1}-01'
    return f'{year}-{month + 1:02d}'


def period_key(tx_date, period):
    return str(tx_date)[:4] if period == 'yearly' else str(tx_date)[:7]


def get_tier(card_info, usage):
    current_tier = card_info['tiers'][0]
    next_tier = None
    for tier in sorted(card_info['tiers'], key=lambda item: item['min']):
        if usage >= tier['min']:
            current_tier = tier
        elif next_tier is None:
            next_tier = tier
    return current_tier, next_tier


def get_discount_tier(discount_tiers, prev_usage):
    matched = None
    for tier in sorted(discount_tiers, key=lambda item: item['min_usage']):
        if prev_usage >= tier['min_usage']:
            matched = tier
    return matched


def tier_spend_for_month(data, key, card_name):
    card_info = CARD_DB[card_name]
    total = 0
    found = False
    for tx in data['transactions']:
        if tx.get('kind') != 'payment':
            continue
        if tx.get('card') != card_name or month_key(tx.get('date', '')) != key:
            continue
        found = True
        rule = card_info['spend_categories'].get(tx.get('category'), {})
        amount = tx.get('amount', 0) * tx.get('direction', 1)
        if rule.get('counts_for_tier', True):
            total += amount
    return max(0, total), found


def previous_usage(data, key, card_name):
    prev_key = previous_month_key(key)
    usage, found = tier_spend_for_month(data, prev_key, card_name)
    if found:
        return usage, f'{prev_key} 거래'
    return data['manual_prev_usage'].get(card_name, 0), '초기값'


def empty_stats():
    return {
        'gross_spend': 0,
        'tier_spend': 0,
        'gift_spend': 0,
        'benefit_counts': {},
        'benefit_raw': {},
        'benefit_awarded': {},
        'benefit_total': 0,
        'payment_count': 0,
        'pool_caps': {},
        'category_discount_raw': {},
    }


def add_benefit(stats, pool_key, amount):
    if not pool_key or amount == 0:
        return
    stats['benefit_raw'][pool_key] = stats['benefit_raw'].get(pool_key, 0) + amount


def calculate_month(data, key):
    stats_by_card = {card_name: empty_stats() for card_name in CARD_DB}
    prev_context = {}
    for card_name, card_info in CARD_DB.items():
        usage, source = previous_usage(data, key, card_name)
        tier, _ = get_tier(card_info, usage)
        prev_context[card_name] = {'usage': usage, 'source': source, 'tier': tier}

    month_transactions = [
        tx for tx in data['transactions']
        if month_key(tx.get('date', '')) == key and tx.get('card') in CARD_DB
    ]

    for tx in month_transactions:
        if tx.get('kind') != 'payment':
            continue
        card_name = tx['card']
        card_info = CARD_DB[card_name]
        category = tx.get('category')
        rule = card_info['spend_categories'].get(category, {})
        direction = tx.get('direction', 1)
        base_amount = tx.get('amount', 0)
        signed_amount = base_amount * direction
        stats = stats_by_card[card_name]
        prev_usage_value = prev_context[card_name]['usage']
        prev_level = prev_context[card_name]['tier']['level']
        required_tier = rule.get('requires_prev_tier', 0)

        stats['payment_count'] += 1
        stats['gross_spend'] += signed_amount
        if rule.get('counts_for_tier', True):
            stats['tier_spend'] += signed_amount
        if rule.get('gift_group'):
            stats['gift_spend'] += signed_amount

        if prev_level >= required_tier and rule.get('cashback_rate'):
            add_benefit(stats, rule.get('cashback_pool'), signed_amount * rule['cashback_rate'])

        if prev_level >= required_tier and rule.get('more_point_multiplier'):
            if base_amount >= rule.get('more_point_min', 5_000):
                points = (base_amount % 1_000) * rule['more_point_multiplier'] * direction
                add_benefit(stats, rule.get('more_point_pool'), points)

        if rule.get('discount_tiers'):
            discount_tier = get_discount_tier(rule['discount_tiers'], prev_usage_value)
            if discount_tier:
                discount_amount = base_amount * discount_tier['rate'] * direction
                category_cap = rule.get('category_monthly_cap')
                if category_cap is not None:
                    category_key = f'{card_name}:{category}'
                    used_for_category = stats['category_discount_raw'].get(category_key, 0)
                    if discount_amount >= 0:
                        available = max(0, category_cap - used_for_category)
                        discount_amount = min(discount_amount, available)
                    else:
                        discount_amount = max(discount_amount, -used_for_category)
                    stats['category_discount_raw'][category_key] = used_for_category + discount_amount
                add_benefit(stats, rule.get('discount_pool'), discount_amount)
                if discount_tier.get('cap') is not None:
                    stats['pool_caps'][rule['discount_pool']] = discount_tier['cap']

    for card_name, card_info in CARD_DB.items():
        stats = stats_by_card[card_name]
        prev_level = prev_context[card_name]['tier']['level']
        for benefit_name, rule in card_info.get('benefit_rules', {}).items():
            period = rule.get('period', 'monthly')
            target_period = key[:4] if period == 'yearly' else key
            matching = [
                tx for tx in data['transactions']
                if tx.get('kind') == 'benefit'
                and tx.get('card') == card_name
                and tx.get('benefit') == benefit_name
                and period_key(tx.get('date', ''), period) == target_period
            ]
            matching.sort(key=lambda item: (item.get('date', ''), item.get('created_at', '')))
            stats['benefit_counts'][benefit_name] = len(matching)
            for index, tx in enumerate(matching, start=1):
                if month_key(tx.get('date', '')) != key:
                    continue
                if index > rule.get('limit', 0):
                    continue
                if prev_level < rule.get('requires_prev_tier', 0):
                    continue
                add_benefit(stats, rule.get('cashback_pool'), rule.get('cashback_per_use', 0))

        for pool_key, raw_amount in stats['benefit_raw'].items():
            pool_info = card_info.get('cashback_pools', {}).get(pool_key, {})
            cap = stats['pool_caps'].get(pool_key, pool_info.get('monthly_cap'))
            awarded = max(0, raw_amount)
            if cap is not None:
                awarded = min(awarded, cap)
            stats['benefit_awarded'][pool_key] = awarded
            stats['benefit_total'] += awarded

        stats['gross_spend'] = max(0, stats['gross_spend'])
        stats['tier_spend'] = max(0, stats['tier_spend'])
        stats['gift_spend'] = max(0, stats['gift_spend'])

    return stats_by_card, prev_context, month_transactions


def gift_usage_by_company(stats_by_card):
    usage = {company: 0 for company in COMPANY_RULES}
    for card_name, stats in stats_by_card.items():
        company = CARD_DB[card_name]['company']
        usage.setdefault(company, 0)
        usage[company] += stats['gift_spend']
    return usage


def available_months(data):
    today_key = date.today().strftime('%Y-%m')
    months = {today_key, previous_month_key(today_key), next_month_key(today_key)}
    for tx in data['transactions']:
        if tx.get('date'):
            months.add(month_key(tx['date']))
    return sorted(months, reverse=True)


def append_transaction(data, transaction):
    tx = {'id': uuid.uuid4().hex[:8], 'created_at': datetime.now().isoformat(timespec='seconds')}
    tx.update(transaction)
    data['transactions'].append(tx)
    save_data(data)


def delete_transaction(data, tx_id):
    data['transactions'] = [tx for tx in data['transactions'] if tx.get('id') != tx_id]
    save_data(data)


def transaction_frame(transactions):
    rows = []
    for tx in sorted(transactions, key=lambda item: item.get('date', ''), reverse=True):
        amount = tx.get('amount', 0) * tx.get('direction', 1)
        rows.append({
            'ID': tx.get('id'),
            '날짜': tx.get('date'),
            '카드': tx.get('card'),
            '종류': '결제' if tx.get('kind') == 'payment' else '혜택',
            '분류': tx.get('category') or tx.get('benefit'),
            '금액': amount if tx.get('kind') == 'payment' else '',
            '메모': tx.get('memo', ''),
        })
    return pd.DataFrame(rows)


if 'app_data' not in st.session_state:
    st.session_state.app_data = load_data()

data = st.session_state.app_data
selected_month = st.sidebar.selectbox('조회 월', available_months(data))
stats_by_card, prev_context, month_transactions = calculate_month(data, selected_month)
company_gifts = gift_usage_by_company(stats_by_card)

st.title('카드 실적 매니저')

total_tier_spend = sum(item['tier_spend'] for item in stats_by_card.values())
total_gift_spend = sum(company_gifts.values())
total_benefit = sum(item['benefit_total'] for item in stats_by_card.values())
total_payments = sum(item['payment_count'] for item in stats_by_card.values())

summary_cols = st.columns(4)
summary_cols[0].metric('실적 인정액', money(total_tier_spend))
summary_cols[1].metric('상품권', money(total_gift_spend))
summary_cols[2].metric('예상 혜택금액', money(total_benefit))
summary_cols[3].metric('결제 건수', f'{total_payments:,}건')

tab_dashboard, tab_input, tab_history, tab_settings = st.tabs(['대시보드', '입력', '거래내역', '설정'])

with tab_dashboard:
    table_rows = []
    for card_name, card_info in CARD_DB.items():
        stats = stats_by_card[card_name]
        current_tier, next_tier = get_tier(card_info, stats['tier_spend'])
        prev_tier = prev_context[card_name]['tier']
        remain = next_tier['min'] - stats['tier_spend'] if next_tier else 0
        table_rows.append({
            '카드': card_name,
            '카드사': card_info['company'],
            '이번달 적용': prev_tier['name'],
            '이번달 실적': int(stats['tier_spend']),
            '다음달 예상': current_tier['name'],
            '다음구간까지': int(max(0, remain)),
            '혜택금액': int(stats['benefit_total']),
        })
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    st.subheader('카드별 현황')
    for company in sorted({info['company'] for info in CARD_DB.values()}):
        company_cards = [name for name, info in CARD_DB.items() if info['company'] == company]
        company_limit = COMPANY_RULES.get(company, {}).get('gift_limit', 0)
        used_gift = company_gifts.get(company, 0)
        with st.expander(f'{company} · 상품권 {money(used_gift)} / {money(company_limit)}', expanded=True):
            if company_limit:
                st.progress(ratio(used_gift / company_limit))
            for card_name in company_cards:
                card_info = CARD_DB[card_name]
                stats = stats_by_card[card_name]
                prev_tier = prev_context[card_name]['tier']
                current_tier, next_tier = get_tier(card_info, stats['tier_spend'])
                st.markdown(f'#### {card_name}')
                cols = st.columns(4)
                cols[0].metric('전월 기준', prev_tier['name'], prev_context[card_name]['source'])
                cols[1].metric('이번달 실적', money(stats['tier_spend']))
                cols[2].metric('다음달 예상', current_tier['name'])
                cols[3].metric('예상 혜택금액', money(stats['benefit_total']))
                if next_tier:
                    remain = max(0, next_tier['min'] - stats['tier_spend'])
                    st.progress(ratio(stats['tier_spend'] / next_tier['min']))
                    st.caption(f'다음 구간 {next_tier["name"]}까지 {money(remain)}')
                else:
                    st.progress(1.0)

                benefit_cols = st.columns(2)
                with benefit_cols[0]:
                    st.write('이번달 적용 혜택')
                    for benefit in card_info.get('benefits_by_tier', {}).get(prev_tier['level'], []):
                        st.caption(f'- {benefit}')
                with benefit_cols[1]:
                    st.write('다음달 예상 혜택')
                    for benefit in card_info.get('benefits_by_tier', {}).get(current_tier['level'], []):
                        st.caption(f'- {benefit}')

                if card_info.get('cashback_pools'):
                    st.write('혜택/포인트 한도')
                    for pool_key, pool_info in card_info['cashback_pools'].items():
                        awarded = stats['benefit_awarded'].get(pool_key, 0)
                        cap = stats['pool_caps'].get(pool_key, pool_info.get('monthly_cap'))
                        if cap is None:
                            st.caption(f'{pool_info["name"]}: {money(awarded)}')
                        else:
                            st.caption(f'{pool_info["name"]}: {money(awarded)} / {money(cap)}')
                            st.progress(ratio(awarded / cap))

                if card_info.get('benefit_rules'):
                    st.write('횟수형 혜택')
                    status_cols = st.columns(min(3, max(1, len(card_info['benefit_rules']))))
                    for index, (benefit_name, rule) in enumerate(card_info['benefit_rules'].items()):
                        used = stats['benefit_counts'].get(benefit_name, 0)
                        limit = rule.get('limit', 0)
                        period_label = '연간' if rule.get('period') == 'yearly' else '월간'
                        with status_cols[index % len(status_cols)]:
                            st.caption(f'{benefit_name} · {period_label} {used}/{limit}회')
                            if limit:
                                st.progress(ratio(used / limit))
                st.divider()

with tab_input:
    input_cols = st.columns(2)
    with input_cols[0]:
        st.subheader('결제 기록')
        payment_card = st.selectbox('카드', list(CARD_DB), key='payment_card')
        categories = list(CARD_DB[payment_card]['spend_categories'])
        with st.form('payment_form', clear_on_submit=True):
            payment_date = st.date_input('날짜', value=date.today(), key='payment_date')
            category = st.selectbox('분류', categories, key='payment_category')
            amount = st.number_input('금액', min_value=0, step=1_000, key='payment_amount')
            direction_label = st.radio('처리', ['결제 추가', '취소/환불'], horizontal=True)
            memo = st.text_input('메모', key='payment_memo')
            submitted = st.form_submit_button('저장')
        if submitted and amount > 0:
            append_transaction(data, {
                'kind': 'payment',
                'date': payment_date.isoformat(),
                'card': payment_card,
                'category': category,
                'amount': amount,
                'direction': -1 if direction_label == '취소/환불' else 1,
                'memo': memo,
            })
            st.rerun()

    with input_cols[1]:
        st.subheader('혜택 사용')
        benefit_card = st.selectbox('카드', list(CARD_DB), key='benefit_card')
        benefit_rules = CARD_DB[benefit_card].get('benefit_rules', {})
        if benefit_rules:
            with st.form('benefit_form', clear_on_submit=True):
                benefit_date = st.date_input('날짜', value=date.today(), key='benefit_date')
                benefit_name = st.selectbox('혜택', list(benefit_rules), key='benefit_name')
                benefit_memo = st.text_input('메모', key='benefit_memo')
                benefit_submitted = st.form_submit_button('사용 기록')
            if benefit_submitted:
                append_transaction(data, {
                    'kind': 'benefit',
                    'date': benefit_date.isoformat(),
                    'card': benefit_card,
                    'benefit': benefit_name,
                    'amount': 0,
                    'direction': 1,
                    'memo': benefit_memo,
                })
                st.rerun()
        else:
            st.info('등록된 횟수형 혜택이 없습니다.')

with tab_history:
    st.subheader(f'{selected_month} 거래내역')
    history_df = transaction_frame(month_transactions)
    if history_df.empty:
        st.caption('거래내역이 없습니다.')
    else:
        st.dataframe(history_df, use_container_width=True, hide_index=True)
        delete_id = st.selectbox('삭제할 거래', history_df['ID'].tolist())
        if st.button('선택 거래 삭제', type='secondary'):
            delete_transaction(data, delete_id)
            st.rerun()

with tab_settings:
    st.subheader('초기 전월 실적')
    with st.form('manual_prev_usage_form'):
        updated_prev_usage = {}
        setting_cols = st.columns(3)
        for index, card_name in enumerate(CARD_DB):
            with setting_cols[index % 3]:
                updated_prev_usage[card_name] = st.number_input(
                    card_name,
                    min_value=0,
                    step=10_000,
                    value=int(data['manual_prev_usage'].get(card_name, 0)),
                    key=f'prev_{card_name}',
                )
        if st.form_submit_button('초기값 저장'):
            data['manual_prev_usage'].update(updated_prev_usage)
            save_data(data)
            st.rerun()

    st.subheader('카드 규칙')
    rules_rows = []
    for card_name, card_info in CARD_DB.items():
        rules_rows.append({
            '카드': card_name,
            '카드사': card_info['company'],
            '결제분류': ', '.join(card_info['spend_categories']),
            '횟수형혜택': ', '.join(card_info.get('benefit_rules', {})) or '-',
        })
    st.dataframe(pd.DataFrame(rules_rows), use_container_width=True, hide_index=True)

    export_json = json.dumps(data, ensure_ascii=False, indent=2)
    st.download_button('데이터 백업', export_json, file_name=f'cardmanager-{selected_month}.json', mime='application/json')
