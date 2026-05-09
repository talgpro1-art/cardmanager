import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="나만의 카드 실적 마스터",
    page_icon="💳",
    layout="wide"
)

# ----------------------------------------------------------------------
# 1. 카드 마스터 데이터 (구조 개선 완료)
# ----------------------------------------------------------------------
CARD_DB = {
    "신한 RPM카드": {
        "company": "신한카드",
        "gift_limit": 1000000,  # 👈 에러가 났던 원인! 상품권 한도 추가
        "tiers": [
            {"tier": 0, "name": "0구간", "min": 0, "max": 499999},
            {"tier": 1, "name": "1구간", "min": 500000, "max": 999999},
            {"tier": 2, "name": "2구간", "min": 1000000, "max": 1499999},
            {"tier": 3, "name": "3구간", "min": 1500000, "max": float('inf')}
        ],
        "tier_benefits": {
            0: ["🔥 특별 적립처 1.0% (정비소, 백화점, 대형마트 등)", "💳 일반 적립처 0.2% (전 가맹점)"],
            1: ["🔥 특별 적립처 2.0% (정비소, 백화점, 대형마트 등)", "💳 일반 적립처 0.8% (전 가맹점)"],
            2: ["🔥 특별 적립처 3.5% (정비소, 백화점, 대형마트 등)", "💳 일반 적립처 1.5% (전 가맹점)"],
            3: ["🔥 특별 적립처 5.0% (정비소, 백화점, 대형마트 등)", "💳 일반 적립처 2.0% (전 가맹점)"]
        },
        "common_benefits": [
            "🎢 놀이공원(에버랜드/롯데월드/서울랜드) 50% 할인 (일 1회, 연 3회)",
            "🌊 캐리비안베이 입장권 30% 할인",
            "🅿️ 전국 무료주차 월 3회",
            "✈️ 해외 공항 라운지 무료 (일본/하와이 연 6회, 기타 연 2회)",
            "🏨 호텔/인천공항 발레파킹 무료 월 3회",
            "☕ 국내 공항 라운지 연 2회 무료"
        ]
    }
}

# ----------------------------------------------------------------------
# 2. 데이터베이스(세션) 초기화
# ----------------------------------------------------------------------
if 'current_usage' not in st.session_state:
    st.session_state.current_usage = {"신한 RPM카드": 0}

if 'gift_card_usage' not in st.session_state:
    st.session_state.gift_card_usage = {"신한카드": 0}

if 'last_month_tier' not in st.session_state:
    st.session_state.last_month_tier = {"신한 RPM카드": 1}

if 'history_df' not in st.session_state:
    st.session_state.history_df = pd.DataFrame(
        columns=["YearMonth", "Card", "Total_Usage"]
    )

# ----------------------------------------------------------------------
# 3. 로직 함수
# ----------------------------------------------------------------------
def get_tier_info(card_info, usage):
    """현재 금액 기준 구간과 다음 구간 반환"""
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
    """월 마감 처리"""
    now = datetime.now().strftime("%Y-%m")

    for card_name, usage in st.session_state.current_usage.items():
        new_row = {
            "YearMonth": now,
            "Card": card_name,
            "Total_Usage": usage
        }
        st.session_state.history_df = pd.concat(
            [st.session_state.history_df, pd.DataFrame([new_row])],
            ignore_index=True
        )

        card_info = CARD_DB[card_name]
        achieved_tier, _ = get_tier_info(card_info, usage)
        st.session_state.last_month_tier[card_name] = achieved_tier["tier"]

    st.session_state.current_usage = {k: 0 for k in st.session_state.current_usage}
    st.session_state.gift_card_usage = {k: 0 for k in st.session_state.gift_card_usage}

# ----------------------------------------------------------------------
# 4. UI 구성
# ----------------------------------------------------------------------
st.title("💳 실적 및 혜택 관리 대시보드")

selected_card_name = st.sidebar.selectbox("관리할 카드 선택", list(CARD_DB.keys()))
card = CARD_DB[selected_card_name]
company = card["company"]

# ----------------------------------------------------------------------
# [최상단] 전월 혜택 표시 (동적 UI 적용)
# ----------------------------------------------------------------------
last_tier_idx = st.session_state.last_month_tier[selected_card_name]
last_tier_info = card["tiers"][last_tier_idx]

st.info(
    f"🏆 **전월 실적 달성 안내:** "
    f"지난달 **{last_tier_info['name']}** 달성으로 "
    f"이번 달은 아래 혜택이 적용됩니다."
)

# 구간별 변동 혜택 (딕셔너리에서 가져옴)
st.write("🎯 **[이번 달 적용 포인트/할인율]**")
for benefit in card["tier_benefits"][last_tier_idx]:
    st.success(benefit)

# 공통 프리미엄 혜택
with st.expander("✨ 프리미엄 공통 혜택 (라운지, 주차, 테마파크 등) 보기"):
    for benefit in card["common_benefits"]:
        st.write(f"- {benefit}")

st.markdown("---")

# ----------------------------------------------------------------------
# [중단] 이번 달 실적 현황
# ----------------------------------------------------------------------
st.subheader("📊 이번 달 실적 충족 현황")

current_val = st.session_state.current_usage[selected_card_name]
curr_tier_info, next_tier_info = get_tier_info(card, current_val)

col1, col2, col3 = st.columns(3)

col1.metric("현재 사용액", f"{current_val:,} 원")
col2.metric("현재 도달 구간", curr_tier_info['name'])

if next_tier_info:
    target_amt = next_tier_info['min']
    remain_amt = target_amt - current_val
    col3.metric("다음 구간 목표", f"{target_amt:,} 원", f"- {remain_amt:,} 원 남음", delta_color="inverse")
    st.progress(min(current_val / target_amt, 1.0))
else:
    col3.metric("다음 구간 목표", "최고 구간", "MAX 달성", delta_color="off")
    st.progress(1.0)

# ----------------------------------------------------------------------
# [하단] 실적 및 상품권 입력
# ----------------------------------------------------------------------
st.markdown("---")
col_in1, col_in2 = st.columns(2)

# 일반 사용액 입력
with col_in1:
    st.subheader("📝 간편 실적 입력")
    st.caption("숫자만 입력하세요. (마이너스 입력 시 실적 차감)")
    with st.form("usage_form", clear_on_submit=True):
        input_amount = st.number_input("결제 금액", step=10000, value=0)
        submitted = st.form_submit_button("실적 합산하기")
        
        if submitted and input_amount != 0:
            st.session_state.current_usage[selected_card_name] += input_amount
            st.rerun()

# 상품권 입력
with col_in2:
    st.subheader("🎫 상품권(상테크) 입력")
    gc_used = st.session_state.gift_card_usage[company]
    
    # DB에 gift_limit이 없으면 기본값 100만원으로 처리 (KeyError 방지)
    gc_limit = card.get("gift_limit", 1000000) 

    st.caption(f"{company} 통합 한도: {gc_used:,} / {gc_limit:,} 원")
    with st.form("gift_card_form", clear_on_submit=True):
        gc_amount = st.number_input("상품권 구매액", step=50000, value=0)
        gc_submitted = st.form_submit_button("상품권 실적 추가")
        
        if gc_submitted and gc_amount != 0:
            if gc_used + gc_amount > gc_limit:
                st.error(f"⚠️ {company} 통합 상품권 한도({gc_limit:,}원)를 초과합니다!")
            else:
                st.session_state.gift_card_usage[company] += gc_amount
                # 상품권도 실적 인정
                st.session_state.current_usage[selected_card_name] += gc_amount
                st.rerun()

# ----------------------------------------------------------------------
# 사이드바 (월 마감)
# ----------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("월별 누적 사용액")

if not st.session_state.history_df.empty:
    st.sidebar.dataframe(st.session_state.history_df, hide_index=True)
else:
    st.sidebar.caption("아직 마감된 데이터가 없습니다.")

st.sidebar.markdown("---")
if st.sidebar.button("🚨 [테스트용] 월 마감하기"):
    end_of_month_process()
    st.sidebar.success("마감 완료! 새로운 달이 시작되었습니다.")
    st.rerun()
