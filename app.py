import streamlit as st
import pandas as pd
from datetime import datetime

# ----------------------------------------------------------------------
# 페이지 설정
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="카드 실적 통합 대시보드",
    page_icon="💳",
    layout="wide"
)

# ----------------------------------------------------------------------
# 카드 마스터 데이터
# ----------------------------------------------------------------------
CARD_DB = {
    "신한 RPM카드": {
        "company": "신한카드",
        "gift_limit": 1000000,
        "tiers": [
            {"tier": 0, "name": "0구간", "min": 0, "max": 499999},
            {"tier": 1, "name": "1구간", "min": 500000, "max": 999999},
            {"tier": 2, "name": "2구간", "min": 1000000, "max": 1499999},
            {"tier": 3, "name": "3구간", "min": 1500000, "max": float('inf')}
        ],
        "reward_special": [1.0, 2.0, 3.5, 5.0],
        "reward_general": [0.2, 0.8, 1.5, 2.0],
    },

    "삼성 taptap O": {
        "company": "삼성카드",
        "gift_limit": 500000,
        "tiers": [
            {"tier": 0, "name": "0구간", "min": 0, "max": 299999},
            {"tier": 1, "name": "1구간", "min": 300000, "max": 699999},
            {"tier": 2, "name": "2구간", "min": 700000, "max": 999999},
            {"tier": 3, "name": "3구간", "min": 1000000, "max": float('inf')}
        ],
        "reward_special": [1.0, 2.0, 3.0, 4.0],
        "reward_general": [0.5, 1.0, 1.5, 2.0],
    }
}

# ----------------------------------------------------------------------
# 세션 초기화
# ----------------------------------------------------------------------
if 'current_usage' not in st.session_state:
    st.session_state.current_usage = {
        card_name: 0 for card_name in CARD_DB.keys()
    }

if 'gift_card_usage' not in st.session_state:

    companies = {}

    for card in CARD_DB.values():
        companies[card["company"]] = 0

    st.session_state.gift_card_usage = companies

if 'last_month_tier' not in st.session_state:
    st.session_state.last_month_tier = {
        card_name: 1 for card_name in CARD_DB.keys()
    }

if 'history_df' not in st.session_state:
    st.session_state.history_df = pd.DataFrame(
        columns=["YearMonth", "Card", "Total_Usage"]
    )

# ----------------------------------------------------------------------
# 함수
# ----------------------------------------------------------------------
def get_tier_info(card_info, usage):

    current_idx = 0

    for i, t in enumerate(card_info["tiers"]):
        if usage >= t["min"]:
            current_idx = i

    current_tier = card_info["tiers"][current_idx]

    next_tier = (
        card_info["tiers"][current_idx + 1]
        if current_idx + 1 < len(card_info["tiers"])
        else None
    )

    return current_tier, next_tier


def end_of_month_process():

    now = datetime.now().strftime("%Y-%m")

    for card_name, usage in st.session_state.current_usage.items():

        new_row = {
            "YearMonth": now,
            "Card": card_name,
            "Total_Usage": usage
        }

        st.session_state.history_df = pd.concat(
            [
                st.session_state.history_df,
                pd.DataFrame([new_row])
            ],
            ignore_index=True
        )

        card_info = CARD_DB[card_name]

        achieved_tier, _ = get_tier_info(card_info, usage)

        st.session_state.last_month_tier[card_name] = achieved_tier["tier"]

    st.session_state.current_usage = {
        k: 0 for k in st.session_state.current_usage
    }

    st.session_state.gift_card_usage = {
        k: 0 for k in st.session_state.gift_card_usage
    }

# ----------------------------------------------------------------------
# 타이틀
# ----------------------------------------------------------------------
st.title("💳 카드 실적 통합 대시보드")

# ----------------------------------------------------------------------
# 상단 통합 현황
# ----------------------------------------------------------------------
st.subheader("📈 전체 카드 실적 현황")

summary_cols = st.columns(len(CARD_DB))

for idx, (card_name, card) in enumerate(CARD_DB.items()):

    usage = st.session_state.current_usage[card_name]

    curr_tier, next_tier = get_tier_info(card, usage)

    company = card["company"]

    gc_used = st.session_state.gift_card_usage[company]
    gc_limit = card["gift_limit"]

    with summary_cols[idx]:

        st.markdown(f"### 💳 {card_name}")

        st.metric(
            "현재 실적",
            f"{usage:,}원"
        )

        st.caption(f"현재 구간: {curr_tier['name']}")

        # 실적 진행률
        if next_tier:

            progress = usage / next_tier['min']

            st.progress(min(progress, 1.0))

            remain = next_tier['min'] - usage

            st.caption(
                f"다음 구간까지 {remain:,}원"
            )

        else:

            st.progress(1.0)

            st.caption("최고 구간 달성")

        st.markdown("#### 🎫 상품권 한도")

        gc_progress = gc_used / gc_limit

        st.progress(min(gc_progress, 1.0))

        st.caption(
            f"{gc_used:,} / {gc_limit:,} 원"
        )

st.markdown("---")

# ----------------------------------------------------------------------
# 카드사 그룹핑
# ----------------------------------------------------------------------
companies = {}

for card_name, card_info in CARD_DB.items():

    company = card_info["company"]

    if company not in companies:
        companies[company] = []

    companies[company].append(card_name)

# ----------------------------------------------------------------------
# 카드사별 렌더링
# ----------------------------------------------------------------------
for company, card_list in companies.items():

    st.header(f"🏦 {company}")

    for card_name in card_list:

        card = CARD_DB[card_name]

        usage = st.session_state.current_usage[card_name]

        curr_tier, next_tier = get_tier_info(card, usage)

        last_tier_idx = st.session_state.last_month_tier[card_name]

        special_rate = card["reward_special"][last_tier_idx]
        general_rate = card["reward_general"][last_tier_idx]

        with st.expander(f"💳 {card_name}", expanded=True):

            # 혜택 안내
            st.info(
                f"🏆 전월 {card['tiers'][last_tier_idx]['name']} 달성\n\n"
                f"🔥 특별 적립 {special_rate}% / "
                f"💳 일반 적립 {general_rate}%"
            )

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "현재 사용액",
                f"{usage:,} 원"
            )

            col2.metric(
                "현재 구간",
                curr_tier['name']
            )

            if next_tier:

                remain_amt = next_tier['min'] - usage

                col3.metric(
                    "다음 구간까지",
                    f"{remain_amt:,} 원"
                )

                st.progress(
                    min(usage / next_tier['min'], 1.0)
                )

            else:

                col3.metric(
                    "다음 구간",
                    "최고 구간"
                )

                st.progress(1.0)

            st.markdown("---")

            # 입력 영역
            input_col1, input_col2 = st.columns(2)

            # 일반 실적
            with input_col1:

                st.subheader("📝 일반 실적 입력")

                with st.form(
                    f"usage_form_{card_name}",
                    clear_on_submit=True
                ):

                    input_amount = st.number_input(
                        "결제 금액",
                        step=10000,
                        value=0,
                        key=f"usage_{card_name}"
                    )

                    submitted = st.form_submit_button(
                        "실적 합산"
                    )

                    if submitted and input_amount != 0:

                        st.session_state.current_usage[card_name] += input_amount

                        st.rerun()

            # 상품권
            with input_col2:

                st.subheader("🎫 상품권 입력")

                gc_used = st.session_state.gift_card_usage[company]

                gc_limit = card["gift_limit"]

                st.caption(
                    f"{company} 통합 한도: "
                    f"{gc_used:,} / {gc_limit:,} 원"
                )

                with st.form(
                    f"gift_form_{card_name}",
                    clear_on_submit=True
                ):

                    gc_amount = st.number_input(
                        "상품권 구매액",
                        step=50000,
                        value=0,
                        key=f"gift_{card_name}"
                    )

                    gc_submit = st.form_submit_button(
                        "상품권 추가"
                    )

                    if gc_submit and gc_amount != 0:

                        if gc_used + gc_amount > gc_limit:

                            st.error(
                                "⚠️ 상품권 통합 한도 초과"
                            )

                        else:

                            st.session_state.gift_card_usage[company] += gc_amount

                            st.session_state.current_usage[card_name] += gc_amount

                            st.rerun()

    st.markdown("---")

# ----------------------------------------------------------------------
# 사이드바
# ----------------------------------------------------------------------
st.sidebar.header("🗂 월별 히스토리")

if not st.session_state.history_df.empty:

    st.sidebar.dataframe(
        st.session_state.history_df,
        hide_index=True
    )

else:

    st.sidebar.caption(
        "아직 마감된 데이터가 없습니다."
    )

st.sidebar.markdown("---")

if st.sidebar.button("🚨 [테스트용] 월 마감하기"):

    end_of_month_process()

    st.sidebar.success(
        "월 마감 완료!"
    )

    st.rerun()
