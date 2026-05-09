import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="나만의 카드 실적 마스터", page_icon="💳", layout="wide")

# ----------------------------------------------------------------------
# 1. 카드 마스터 데이터 (신규 카드 임시 뼈대 추가)
# ----------------------------------------------------------------------
CARD_DB = {
    # --- 신한카드 ---
    "RPM": {
        "company": "신한카드",
        "gift_limit": 1000000,
        "tiers": [
            {"tier": 0, "name": "0구간", "min": 0, "max": 499999},
            {"tier": 1, "name": "1구간", "min": 500000, "max": 999999},
            {"tier": 2, "name": "2구간", "min": 1000000, "max": 1499999},
            {"tier": 3, "name": "3구간", "min": 1500000, "max": float('inf')}
        ],
        "tier_benefits": {
            0: ["🔥 특별 적립 1.0%", "💳 일반 적립 0.2%"],
            1: ["🔥 특별 적립 2.0%", "💳 일반 적립 0.8%"],
            2: ["🔥 특별 적립 3.5%", "💳 일반 적립 1.5%"],
            3: ["🔥 특별 적립 5.0%", "💳 일반 적립 2.0%"]
        },
        "common_benefits": ["🎢 에버랜드/롯데월드 50% 할인", "🌊 캐리비안베이 30% 할인"],
        "benefit_limits": {
            "무료주차": {"limit": 3, "type": "월간"},
            "공항라운지": {"limit": 2, "type": "연간"},
            "발레파킹": {"limit": 3, "type": "월간"}
        }
    },
    "Deep Oil": {
        "company": "신한카드",
        "gift_limit": 1000000,
        "tiers": [{"tier": 0, "name": "기본", "min": 0, "max": 299999}, {"tier": 1, "name": "1구간", "min": 300000, "max": float('inf')}],
        "tier_benefits": {0: ["혜택 없음"], 1: ["⛽ 주유 10% 결제일 할인 (임시)"]},
        "common_benefits": ["🎬 영화 할인 (임시)"]
    },
    
    # --- 삼성카드 ---
    "taptap": {
        "company": "삼성카드",
        "gift_limit": 1000000,
        "tiers": [{"tier": 0, "name": "기본", "min": 0, "max": 299999}, {"tier": 1, "name": "1구간", "min": 300000, "max": float('inf')}],
        "tier_benefits": {0: ["혜택 없음"], 1: ["☕ 스타벅스 50% 할인 (임시)"]},
        "common_benefits": []
    },
    "iD ON": {
        "company": "삼성카드",
        "gift_limit": 1000000,
        "tiers": [{"tier": 0, "name": "기본", "min": 0, "max": 299999}, {"tier": 1, "name": "1구간", "min": 300000, "max": float('inf')}],
        "tier_benefits": {0: ["혜택 없음"], 1: ["🍱 많이 쓰는 영역 30% 할인 (임시)"]},
        "common_benefits": []
    }
}

# ----------------------------------------------------------------------
# 2. 데이터베이스(세션) 동적 초기화 (카드가 늘어나도 자동 대응)
# ----------------------------------------------------------------------
# 딕셔너리 컴프리헨션으로 DB에 있는 모든 카드에 대해 초기값 세팅
if 'current_usage' not in st.session_state:
    st.session_state.current_usage = {card: 0 for card in CARD_DB.keys()}
if 'last_month_tier' not in st.session_state:
    st.session_state.last_month_tier = {card: 0 for card in CARD_DB.keys()}
if 'is_setup_done' not in st.session_state:
    st.session_state.is_setup_done = {card: False for card in CARD_DB.keys()}

# 상품권은 '카드사' 단위로 통합 관리
if 'gift_card_usage' not in st.session_state:
    companies = set(info["company"] for info in CARD_DB.values())
    st.session_state.gift_card_usage = {comp: 0 for comp in companies}

# 횟수 차감 혜택 트래킹
if 'benefit_usage' not in st.session_state:
    st.session_state.benefit_usage = {}
    for card, info in CARD_DB.items():
        if "benefit_limits" in info:
            st.session_state.benefit_usage[card] = {b_name: 0 for b_name in info["benefit_limits"]}
        else:
            st.session_state.benefit_usage[card] = {}

if 'history_df' not in st.session_state:
    st.session_state.history_df = pd.DataFrame(columns=["YearMonth", "Card", "Total_Usage"])

# ----------------------------------------------------------------------
# 3. 로직 함수
# ----------------------------------------------------------------------
def get_tier_info(card_info, usage):
    current_idx = 0
    for i, t in enumerate(card_info["tiers"]):
        if usage >= t["min"]:
            current_idx = i
    current_tier = card_info["tiers"][current_idx]
    next_tier = card_info["tiers"][current_idx + 1] if current_idx + 1 < len(card_info["tiers"]) else None
    return current_tier, next_tier

def end_of_month_process():
    now = datetime.now().strftime("%Y-%m")
    for card_name, usage in st.session_state.current_usage.items():
        new_row = {"YearMonth": now, "Card": card_name, "Total_Usage": usage}
        st.session_state.history_df = pd.concat([st.session_state.history_df, pd.DataFrame([new_row])], ignore_index=True)
        
        card_info = CARD_DB[card_name]
        achieved_tier, _ = get_tier_info(card_info, usage)
        st.session_state.last_month_tier[card_name] = achieved_tier["tier"]
        
        if "benefit_limits" in card_info:
            for b_name, b_info in card_info["benefit_limits"].items():
                if b_info["type"] == "월간":
                    st.session_state.benefit_usage[card_name][b_name] = 0

    st.session_state.current_usage = {k: 0 for k in st.session_state.current_usage}
    st.session_state.gift_card_usage = {k: 0 for k in st.session_state.gift_card_usage}

# ======================================================================
# [ 상단 ] 전체 카드 실적 현황
# ======================================================================
st.title("💳 나의 카드 실적 대시보드")
st.markdown("---")

total_card_usage = sum(st.session_state.current_usage.values())
total_gift_usage = sum(st.session_state.gift_card_usage.values())

top_col1, top_col2 = st.columns(2)
top_col1.metric("이번 달 총 실적 사용액 (모든 카드)", f"{total_card_usage:,} 원")
top_col2.metric("이번 달 총 상품권 구매액 (상테크)", f"{total_gift_usage:,} 원")

st.markdown("---")

# ======================================================================
# [ 중단 ] 카드사별 카드 리스트 (Tree 구조)
# ======================================================================
# DB를 순회하며 카드사별로 카드를 분류
company_dict = {}
for c_name, c_info in CARD_DB.items():
    comp = c_info["company"]
    if comp not in company_dict:
        company_dict[comp] = []
    company_dict[comp].append(c_name)

# 카드사별로 UI 렌더링
for comp, cards in company_dict.items():
    st.subheader(f"🏢 {comp}")
    
    # 해당 카드사의 상품권 공통 한도 표시
    gc_limit = CARD_DB[cards[0]].get("gift_limit", 1000000)
    gc_used = st.session_state.gift_card_usage[comp]
    st.caption(f"**[{comp} 상테크 통합 한도] {gc_used:,} / {gc_limit:,} 원")
    
    for c_name in cards:
        card = CARD_DB[c_name]
        current_val = st.session_state.current_usage[c_name]
        
        # 카드를 누르면 펼쳐지는 Expander 형태
        with st.expander(f"💳 {c_name} (현재 실적: {current_val:,} 원)", expanded=False):
            
            # 1. 최초 세팅 락(Lock)
            if not st.session_state.is_setup_done[c_name]:
                st.warning("⚠️ 이번 달 혜택 계산을 위해 지난달 실적을 먼저 입력해주세요.")
                with st.form(f"setup_{c_name}"):
                    init_usage = st.number_input("지난달 총 실적 (원)", min_value=0, step=10000, key=f"init_in_{c_name}")
                    if st.form_submit_button("초기 세팅 완료"):
                        achieved_tier, _ = get_tier_info(card, init_usage)
                        st.session_state.last_month_tier[c_name] = achieved_tier["tier"]
                        st.session_state.is_setup_done[c_name] = True
                        st.rerun()
            
            # 2. 메인 대시보드 (세팅 완료 시)
            else:
                last_tier_idx = st.session_state.last_month_tier[c_name]
                curr_tier_info, next_tier_info = get_tier_info(card, current_val)
                
                # 상단 혜택 요약
                st.info(f"🏆 전월 실적 [last_tier_idx]['name']}** 달성! 이번 달 혜택이 적용 중입니다.")
                if card["tier_benefits"]:
                    for benefit in card["tier_benefits"][last_tier_idx]:
                        st.write(f"✔️ {benefit}")
                
                st.markdown("---")
                
                # 실적 게이지
                t_col1, t_col2 = st.columns(2)
                t_col1.metric("현재 도달 구간", curr_tier_info['name'])
                if next_tier_info:
                    target = next_tier_info['min']
                    remain = target - current_val
                    t_col2.metric("다음 구간 목표", f"{target:,} 원", f"- {remain:,} 원 남음", delta_color="inverse")
                    st.progress(min(current_val / target, 1.0))
                else:
                    t_col2.metric("다음 구간 목표", "최고 구간", "MAX", delta_color="off")
                    st.progress(1.0)
                
                st.markdown("---")
                
                # 실적 및 상품권 간편 입력 폼
                in_col1, in_col2 = st.columns(2)
                with in_col1:
                    with st.form(f"usage_form_{c_name}", clear_on_submit=True):
                        input_amount = st.number_input("일반 결제 추가 (원)", step=10000, value=0, key=f"amt_{c_name}")
                        if st.form_submit_button("합산하기") and input_amount != 0:
                            st.session_state.current_usage[c_name] += input_amount
                            st.rerun()
                with in_col2:
                    with st.form(f"gc_form_{c_name}", clear_on_submit=True):
                        gc_amount = st.number_input(f"{comp} 상품권 구매 (원)", step=50000, value=0, key=f"gc_amt_{c_name}")
                        if st.form_submit_button("상품권 실적 추가") and gc_amount != 0:
                            if gc_used + gc_amount > gc_limit:
                                st.error(f"한도 {gc_limit:,}원 초과!")
                            else:
                                st.session_state.gift_card_usage[comp] += gc_amount
                                st.session_state.current_usage[c_name] += gc_amount
                                st.rerun()

# ======================================================================
# [ 하단 ] 월별 히스토리
# ======================================================================
st.markdown("---")
st.subheader("📅 월별 누적 히스토리 및 마감")

if not st.session_state.history_df.empty:
    st.dataframe(st.session_state.history_df, use_container_width=True)
else:
    st.caption("아직 마감된 월별 데이터가 없습니다.")

if st.button("🚨 이번 달 최종 마감하기 (다음 달로 넘어가기)", type="primary"):
    end_of_month_process()
    st.success("월 마감이 완료되었습니다! 모든 실적이 초기화되었습니다.")
    st.rerun()
