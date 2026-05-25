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
    '삼성카드': {'gift_limit': 1_000_000},
    '카드사 미정': {'gift_limit': 1_000_000},
}

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
    'taptap': {
        'company': '삼성카드',
        'tiers': [
            {'level': 0, 'name': '기본', 'min': 0},
            {'level': 1, 'name': '30만 이상', 'min': 300_000},
        ],
        'benefits_by_tier': {0: ['혜택 없음'], 1: ['스타벅스 50% 할인']},
        'spend_categories': {
            '일반결제': {'counts_for_tier': True},
            '커피/선택혜택': {'counts_for_tier': True},
            '상품권': {'counts_for_tier': True, 'gift_group': 'company'},
            '실적제외': {'counts_for_tier': False},
        },
        'benefit_rules': {
            '스타벅스 할인': {'limit': 6, 'period': 'monthly', 'requires_prev_tier': 1},
        },
        'cashback_pools': {},
    },
    'iD ON': {
        'company': '삼성카드',
        'tiers': [
            {'level': 0, 'name': '기본', 'min': 0},
            {'level': 1, 'name': '30만 이상', 'min': 300_000},
        ],
        'benefits_by_tier': {0: ['혜택 없음'], 1: ['많이 쓰는 영역 30% 할인']},
        'spend_categories': {
            '일반결제': {'counts_for_tier': True},
            '많이 쓰는 영역': {'counts_for_tier': True},
            '상품권': {'counts_for_tier': True, 'gift_group': 'company'},
            '실적제외': {'counts_for_tier': False},
        },
        'benefit_rules': {},
        'cashback_pools': {},
    },
    '카드5': {
        'company': '카드사 미정',
        'tiers': [
            {'level': 0, 'name': '기본', 'min': 0},
            {'level': 1, 'name': '30만 이상', 'min': 300_000},
        ],
        'benefits_by_tier': {0: ['혜택 없음'], 1: ['카드 혜택 입력 예정']},
        'spend_categories': {
            '일반결제': {'counts_for_tier': True},
            '상품권': {'counts_for_tier': True, 'gift_group': 'company'},
            '실적제외': {'counts_for_tier': False},
        },
        'benefit_rules': {},
        'cashback_pools': {},
    },
    '카드6': {
        'company': '카드사 미정',
        'tiers': [
            {'level': 0, 'name': '기본', 'min': 0},
            {'level': 1, 'name': '30만 이상', 'min': 300_000},
        ],
        'benefits_by_tier': {0: ['혜택 없음'], 1: ['카드 혜택 입력 예정']},
        'spend_categories': {
            '일반결제': {'counts_for_tier': True},
            '상품권': {'counts_for_tier': True, 'gift_group': 'company'},
            '실적제외': {'counts_for_tier': False},
        },
        'benefit_rules': {},
        'cashback_pools': {},
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
        for key in shaped:
            if key in data:
                shaped[key] = data[key]
    if not isinstance(shaped.get('transactions'), list):
        shaped['transactions'] = []
    if not isinstance(shaped.get('manual_prev_usage'), dict):
        shaped['manual_prev_usage'] = {}
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


def clamp_ratio(value):
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
    if period == 'yearly':
        return str(tx_date)[:4]
    return str(tx_date)[:7]


def get_tier(card_info, usage):
    tiers = sorted(card_info['tiers'], key=lambda item: item['min'])
    current_tier = tiers[0]
    next_tier = None
    for tier in tiers:
        if usage >= tier['min']:
            current_tier = tier
        elif next_tier is None:
            next_tier = tier
    return current_tier, next_tier


def get_tier_spend_for_month(data, key, card_name):
    total = 0
    found_payment = False
    card_info = CARD_DB[card_name]
    for tx in data['transactions']:
        if tx.get('kind') != 'payment':
            continue
        if tx.get('card') != card_name or month_key(tx.get('date', '')) != key:
            continue
        found_payment = True
        rule = card_info['spend_categories'].get(tx.get('category'), {})
        amount = tx.get('amount', 0) * tx.get('direction', 1)
        if rule.get('counts_for_tier', True):
            total += amount
    return max(0, total), found_payment


def get_prev_usage_source(data, key, card_name):
    prev_key = previous_month_key(key)
    prev_usage, found_prev_payment = get_tier_spend_for_month(data, prev_key, card_name)
    if found_prev_payment:
        return prev_usage, f'{prev_key} 거래'
    return data['manual_prev_usage'].get(card_name, 0), '초기값'


def empty_stats():
    return {
        'gross_spend': 0,
        'tier_spend': 0,
        'excluded_spend': 0,
        'gift_spend': 0,
        'cashback_raw': {},
        'cashback_awarded': {},
        'cashback_total': 0,
        'benefit_counts': {},
        'payment_count': 0,
        'benefit_count': 0,
    }


def add_cashback(stats, pool_key, amount):
    if not pool_key or amount == 0:
        return
    stats['cashback_raw'][pool_key] = stats['cashback_raw'].get(pool_key, 0) + amount


def calculate_month(data, key):
    stats_by_card = {card_name: empty_stats() for card_name in CARD_DB}
    prev_context = {}
    for card_name, card_info in CARD_DB.items():
        prev_usage, source = get_prev_usage_source(data, key, card_name)
        prev_tier, _ = get_tier(card_info, prev_usage)
        prev_context[card_name] = {'usage': prev_usage, 'source': source, 'tier': prev_tier}

    month_transactions = [
        tx for tx in data['transactions']
        if month_key(tx.get('date', '')) == key and tx.get('card') in CARD_DB
    ]

    for tx in month_transactions:
        if tx.get('kind') != 'payment':
            continue
        card_name = tx['card']
        card_info = CARD_DB[card_name]
        rule = card_info['spend_categories'].get(tx.get('category'), {})
        amount = tx.get('amount', 0) * tx.get('direction', 1)
        stats = stats_by_card[card_name]
        stats['payment_count'] += 1
        stats['gross_spend'] += amount
        if rule.get('counts_for_tier', True):
            stats['tier_spend'] += amount
        else:
            stats['excluded_spend'] += amount
        if rule.get('gift_group'):
            stats['gift_spend'] += amount
        if prev_context[card_name]['tier']['level'] >= rule.get('requires_prev_tier', 0):
            if rule.get('cashback_rate'):
                add_cashback(stats, rule.get('cashback_pool'), amount * rule['cashback_rate'])

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
                stats['benefit_count'] += 1
                add_cashback(stats, rule.get('cashback_pool'), rule.get('cashback_per_use', 0))

        for pool_key, raw_amount in stats['cashback_raw'].items():
            pool_info = card_info.get('cashback_pools', {}).get(pool_key, {})
            cap = pool_info.get('monthly_cap')
            awarded = max(0, raw_amount)
            if cap is not None:
                awarded = min(awarded, cap)
            stats['cashback_awarded'][pool_key] = awarded
            stats['cashback_total'] += awarded
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
    tx = {
        'id': uuid.uuid4().hex[:8],
        'created_at': datetime.now().isoformat(timespec='seconds'),
    }
    tx.update(transaction)
    data['transactions'].append(tx)
    save_data(data)


def delete_transaction(data, tx_id):
    data['transactions'] = [tx for tx in data['transactions'] if tx.get('id') != tx_id]
    save_data(data)


def transaction_frame(transactions):
    rows = []
    sorted_txs = sorted(transactions, key=lambda item: item.get('date', ''), reverse=True)
    for tx in sorted_txs:
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

summary_cols = st.columns(4)
summary_cols[0].metric('실적 인정액', money(sum(item['tier_spend'] for item in stats_by_card.values())))
summary_cols[1].metric('상품권', money(sum(company_gifts.values())))
summary_cols[2].metric('예상 캐시백', money(sum(item['cashback_total'] for item in stats_by_card.values())))
summary_cols[3].metric('결제 건수', f'{sum(item["payment_count"] for item in stats_by_card.values()):,}건')

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
            '캐시백': int(stats['cashback_total']),
        })
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    st.subheader('카드별 현황')
    for company in sorted({info['company'] for info in CARD_DB.values()}):
        company_cards = [name for name, info in CARD_DB.items() if info['company'] == company]
        company_limit = COMPANY_RULES.get(company, {}).get('gift_limit', 0)
        used_gift = company_gifts.get(company, 0)
        with st.expander(f'{company} · 상품권 {money(used_gift)} / {money(company_limit)}', expanded=True):
            if company_limit:
                st.progress(clamp_ratio(used_gift / company_limit))
            for card_name in company_cards:
                card_info = CARD_DB[card_name]
                stats = stats_by_card[card_name]
                prev_tier = prev_context[card_name]['tier']
                current_tier, next_tier = get_tier(card_info, stats['tier_spend'])
                st.markdown(f'#### {card_name}')
                card_cols = st.columns(4)
                card_cols[0].metric('전월 기준', prev_tier['name'], prev_context[card_name]['source'])
                card_cols[1].metric('이번달 실적', money(stats['tier_spend']))
                card_cols[2].metric('다음달 예상', current_tier['name'])
                card_cols[3].metric('예상 캐시백', money(stats['cashback_total']))
                if next_tier:
                    remain = max(0, next_tier['min'] - stats['tier_spend'])
                    st.progress(clamp_ratio(stats['tier_spend'] / next_tier['min']))
                    st.caption(f'다음 구간 {next_tier["name"]}까지 {money(remain)}')
                else:
                    st.progress(1.0)

                col_a, col_b = st.columns(2)
                with col_a:
                    st.write('이번달 적용 혜택')
                    for benefit in card_info.get('benefits_by_tier', {}).get(prev_tier['level'], []):
                        st.caption(f'- {benefit}')
                with col_b:
                    st.write('다음달 예상 혜택')
                    for benefit in card_info.get('benefits_by_tier', {}).get(current_tier['level'], []):
                        st.caption(f'- {benefit}')

                if card_info.get('cashback_pools'):
                    st.write('캐시백 한도')
                    for pool_key, pool_info in card_info['cashback_pools'].items():
                        cap = pool_info.get('monthly_cap', 0)
                        awarded = stats['cashback_awarded'].get(pool_key, 0)
                        st.caption(f'{pool_info["name"]}: {money(awarded)} / {money(cap)}')
                        if cap:
                            st.progress(clamp_ratio(awarded / cap))

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
                                st.progress(clamp_ratio(used / limit))
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
