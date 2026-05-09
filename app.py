import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="나만의 카드 실적 마스터", page_icon="💳", layout="wide")

# ----------------------------------------------------------------------
# 1. 카드 마스터 데이터
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
            0: ["🔥 특별 적립 1.0% (정비소, 백화점, 3대마트 등)", "💳 일반 적립 0.2%"],
            1: ["🔥 특별 적립 2.0% (정비소, 백화점, 3대마트 등)", "💳 일반 적립 0.8%"],
            2: ["🔥 특별 적립 3.5% (정비소, 백화점, 3대마트 등)", "💳 일반 적립 1.5%"],
            3: ["🔥 특별 적립 5.0% (정비소, 백화점, 3대마트 등)", "💳 일반 적립 2.0%"]
        },
        "common_benefits": ["🎢 에버랜드/롯데월드 50% 할인", "🌊 캐리비안베이 30% 할인"],
        "benefit_limits": {
            "무료주차": {"limit": 3, "type": "월간"},
            "공항라운지": {"limit": 2, "type": "연간"},
            "발레파킹": {"limit": 3, "type": "월간"}
        }
    },
    "Deep Eco": {
        "company": "신한카드",
        "gift_limit": 1000000,
        "cashback_limit": 30000,     
        "gc_cashback_rate": 0.05,    
        "tiers": [
            {"tier": 0, "name": "실적 미달", "min": 0, "max": 299999}, 
            {"tier": 1, "name": "30만 이상 (혜택 활성)", "min": 300000, "max": float('inf')}
        ],
        "tier_benefits": {
            0: ["❌ 전월 실적 미달 (이번 달 캐시백 없음)"], 
            1: [
                "♻️ [통합 캐시백 한도: 3만 원]",
                "🚌 대중교통/전기차/모빌리티 5% 캐시백",
                "🛒 온라인 구매(쿠팡/11번가/G마켓 등) 5% 캐시백",
                "🎫 상품권 구매 5% 캐시백 (실적 및 한도 포함)"
            ]
        },
        "common_benefits": [
            "☕ 스타벅스 사이렌오더 1회 1천 원 적립 (월 5회, 통합 한도 공유)", # 👈 텍스트 수정
            "🚶 워크온 앱 만보기 15일 달성 5천 원 (통합 한도 별도)"
        ],
        "benefit_limits": {
            # 👈 cashback 값을 1000으로 수정! 이제 한 번 누를 때마다 1,000원씩 오릅니다.
            "스벅 사이렌오더": {"limit": 5, "type": "월간", "cashback": 1000},
            "만보기 15일 달성": {"limit": 1, "type": "월간", "cashback": 0}
        }
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
# 2. 데이터베이스(세션) 초기화
# ----------------------------------------------------------------------
if 'current_usage' not in st.session_state:
    st.session_state.current_usage = {card: 0 for card in CARD_DB.keys()}
if 'last_month_tier' not in st.session_state:
    st.session_state.last_month_tier = {card: 0 for card in CARD_DB.keys()}
if 'is_setup_done' not in st.session_state:
    st.session_state.is_setup_done = {card: False for card in CARD_DB.keys()}

if 'gift_card_usage' not in st.session_state:
    companies = set(info["company"] for info in CARD_DB.values())
    st.session_state.gift_card_usage = {comp: 0 for comp in companies}

# [신규] 카드별 확보한 캐시백 금액 트래킹
if 'cashback_earned' not in st.session_state:
    st.session_state.cashback_earned = {card: 0 for card in CARD_DB.keys()}

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

    # 데이터 리셋
    st.session_state.current_usage = {k: 0 for k in st.session_state.current_usage}
    st.session_state.gift_card_usage = {k: 0 for k in st.session_state.gift_card_usage}
    st.session_state.cashback_earned = {k: 0 for k in st.session_state.cashback_earned}

# ======================================================================
# [ 상단 ] 전체 현황
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
# [ 중단 ] 카드 상세
# ======================================================================
company_dict = {}
for c_name, c_info in CARD_DB.items():
    comp = c_info["company"]
    if comp not in company_dict:
        company_dict[comp] = []
    company_dict[comp].append(c_name)

for comp, cards in company_dict.items():
    st.subheader(f"🏢 {comp}")
    gc_limit = CARD_DB[cards[0]].get("gift_limit", 1000000)
    gc_used = st.session_state.gift_card_usage[comp]
    st.caption(f"**[{comp} 상테크 통합 한도]** {gc_used:,} / {gc_limit:,} 원")
    
    for c_name in cards:
        card = CARD_DB[c_name]
        current_val = st.session_state.current_usage[c_name]
        
        with st.expander(f"💳 {c_name} (현재 실적: {current_val:,} 원)", expanded=False):
            
            if not st.session_state.is_setup_done[c_name]:
                st.warning("⚠️ 이번 달 혜택 계산을 위해 지난달 실적을 먼저 입력해주세요.")
                with st.form(f"setup_{c_name}"):
                    init_usage = st.number_input("지난달 총 실적 (원)", min_value=0, step=10000, key=f"init_in_{c_name}")
                    if st.form_submit_button("초기 세팅 완료"):
                        achieved_tier, _ = get_tier_info(card, init_usage)
                        st.session_state.last_month_tier[c_name] = achieved_tier["tier"]
                        st.session_state.is_setup_done[c_name] = True
                        st.rerun()
            else:
                last_tier_idx = st.session_state.last_month_tier[c_name]
                last_tier_info = card['tiers'][last_tier_idx]
                curr_tier_info, next_tier_info = get_tier_info(card, current_val)
                
                st.info(f"🏆 전월 실적 **{last_tier_info['name']}** 달성! 이번 달 아래 혜택이 적용됩니다.")
                
                if card.get("tier_benefits"):
                    st.write("**🎯 이번 달 적용 포인트/할인율**")
                    for benefit in card["tier_benefits"][last_tier_idx]:
                        st.write(f"✔️ {benefit}")
                        
                if card.get("common_benefits"):
                    st.write("**✨ 공통 혜택**")
                    for benefit in card["common_benefits"]:
                        st.caption(f"- {benefit}")
                        
                # ---------------------------------------------------
                # [신규] 통합 캐시백 한도 게이지 바 표시
                # ---------------------------------------------------
                if "cashback_limit" in card and last_tier_idx > 0:
                    cb_limit = card["cashback_limit"]
                    cb_earned = st.session_state.cashback_earned[c_name]
                    st.write("**💰 통합 캐시백 달성률 (3만 원 한도)**")
                    st.progress(min(cb_earned / cb_limit, 1.0))
                    st.caption(f"확보한 캐시백: **{int(cb_earned):,}원** / {cb_limit:,}원")
                
                if card.get("benefit_limits"):
                    st.write("**🎟️ 횟수 차감형 혜택 관리**")
                    b_cols = st.columns(len(card["benefit_limits"]))
                    for idx, (b_name, b_info) in enumerate(card["benefit_limits"].items()):
                        limit = b_info["limit"]
                        used = st.session_state.benefit_usage[c_name][b_name]
                        b_type = b_info["type"]
                        with b_cols[idx]:
                            with st.container(border=True):
                                st.markdown(f"**{b_name}**")
                                st.caption(f"{b_type} | {used}/{limit}회")
                                st.progress(min(used / limit, 1.0))
                                if st.button("사용하기", key=f"btn_{c_name}_{b_name}", disabled=(used >= limit)):
                                    st.session_state.benefit_usage[c_name][b_name] += 1
                                    
                                    # 버튼 누를 때 스벅 5천원 등 캐시백 금액 자동 합산
                                    if b_info.get("cashback", 0) > 0:
                                        st.session_state.cashback_earned[c_name] += b_info["cashback"]
                                        if "cashback_limit" in card:
                                            st.session_state.cashback_earned[c_name] = min(card["cashback_limit"], st.session_state.cashback_earned[c_name])
                                    st.rerun()
                
                st.markdown("---")
                
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
                
                curr_tier_idx = curr_tier_info['tier']
                if card.get("tier_benefits"):
                    st.success(f"💡 **현재까지 확보한 다음 달 혜택 ({curr_tier_info['name']} 기준)**")
                    for benefit in card["tier_benefits"][curr_tier_idx]:
                        st.caption(f"🎁 {benefit}")
                
                st.markdown("---")
                
                in_col1, in_col2 = st.columns(2)
                with in_col1:
                    with st.form(f"usage_form_{c_name}", clear_on_submit=True):
                        input_amount = st.number_input("일반 결제 추가 (원)", step=10000, value=0, key=f"amt_{c_name}")
                        
                        # [신규] 대중교통/온라인 등 5% 캐시백 대상 결제인지 체크
                        is_cb_target = False
                        if "cashback_limit" in card:
                            is_cb_target = st.checkbox("5% 캐시백 대상(대중교통/온라인 등) 결제", key=f"chk_{c_name}")
                            
                        if st.form_submit_button("합산하기") and input_amount != 0:
                            st.session_state.current_usage[c_name] += input_amount
                            if is_cb_target:
                                earned = input_amount * 0.05
                                st.session_state.cashback_earned[c_name] += earned
                                st.session_state.cashback_earned[c_name] = min(card["cashback_limit"], st.session_state.cashback_earned[c_name])
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
                                
                                # [신규] 상품권 구매 시 5% 캐시백 자동 합산
                                if card.get("gc_cashback_rate", 0) > 0:
                                    earned = gc_amount * card["gc_cashback_rate"]
                                    st.session_state.cashback_earned[c_name] += earned
                                    if "cashback_limit" in card:
                                        st.session_state.cashback_earned[c_name] = min(card["cashback_limit"], st.session_state.cashback_earned[c_name])
                                st.rerun()

# ======================================================================
# [ 하단 ] 월별 마감
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
