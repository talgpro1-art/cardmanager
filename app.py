                "다음달 예상": current_tier["name"],
                "다음구간까지": int(max(0, remain)),
                "캐시백": int(card_stats["cashback_total"]),
            }
        )

    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    st.subheader("카드별 현황")
    for company in sorted({info["company"] for info in CARD_DB.values()}):
        company_cards = [name for name, info in CARD_DB.items() if info["company"] == company]
        company_limit = COMPANY_RULES.get(company, {}).get("gift_limit", 0)
        used_gift = company_gifts.get(company, 0)

        with st.expander(f"{company} · 상품권 {money(used_gift)} / {money(company_limit)}", expanded=True):
            if company_limit:
                st.progress(percent(used_gift / company_limit))

            for card_name in company_cards:
                card_info = CARD_DB[card_name]
                card_stats = stats_by_card[card_name]
                prev_tier = prev_context[card_name]["tier"]
                current_tier, next_tier = get_tier(card_info, card_stats["tier_spend"])

                st.markdown(f"#### {card_name}")
                card_cols = st.columns(4)
                card_cols[0].metric("전월 기준", prev_tier["name"], prev_context[card_name]["source"])
                card_cols[1].metric("이번달 실적", money(card_stats["tier_spend"]))
                card_cols[2].metric("다음달 예상", current_tier["name"])
                card_cols[3].metric("예상 캐시백", money(card_stats["cashback_total"]))

                if next_tier:
                    remain = max(0, next_tier["min"] - card_stats["tier_spend"])
                    st.progress(percent(card_stats["tier_spend"] / next_tier["min"]))
                    st.caption(f"다음 구간 {next_tier['name']}까지 {money(remain)}")
                else:
                    st.progress(1.0)

                benefit_cols = st.columns(2)
                with benefit_cols[0]:
                    st.write("이번달 적용 혜택")
                    for benefit in card_info.get("benefits_by_tier", {}).get(prev_tier["level"], []):
                        st.caption(f"- {benefit}")
                with benefit_cols[1]:
                    st.write("다음달 예상 혜택")
                    for benefit in card_info.get("benefits_by_tier", {}).get(current_tier["level"], []):
                        st.caption(f"- {benefit}")

                if card_info.get("cashback_pools"):
                    st.write("캐시백 한도")
                    for pool_key, pool_info in card_info["cashback_pools"].items():
                        cap = pool_info.get("monthly_cap", 0)
                        awarded = card_stats["cashback_awarded"].get(pool_key, 0)
                        st.caption(f"{pool_info['name']}: {money(awarded)} / {money(cap)}")
                        if cap:
                            st.progress(percent(awarded / cap))

                if card_info.get("benefit_rules"):
                    st.write("횟수형 혜택")
                    benefit_status_cols = st.columns(min(3, max(1, len(card_info["benefit_rules"]))))
                    for index, (benefit_name, rule) in enumerate(card_info["benefit_rules"].items()):
                        used = card_stats["benefit_counts"].get(benefit_name, 0)
                        limit = rule.get("limit", 0)
                        period_label = "연간" if rule.get("period") == "yearly" else "월간"
                        with benefit_status_cols[index % len(benefit_status_cols)]:
                            st.caption(f"{benefit_name} · {period_label} {used}/{limit}회")
                            if limit:
                                st.progress(percent(used / limit))

                st.divider()

with tab_input:
    input_cols = st.columns(2)

    with input_cols[0]:
        st.subheader("결제 기록")
        payment_card = st.selectbox("카드", list(CARD_DB), key="payment_card")
        payment_categories = list(CARD_DB[payment_card]["spend_categories"])
        with st.form("payment_form", clear_on_submit=True):
            payment_date = st.date_input("날짜", value=date.today(), key="payment_date")
            category = st.selectbox("분류", payment_categories, key="payment_category")
            amount = st.number_input("금액", min_value=0, step=1_000, key="payment_amount")
            direction_label = st.radio("처리", ["결제 추가", "취소/환불"], horizontal=True)
            memo = st.text_input("메모", key="payment_memo")
            submitted = st.form_submit_button("저장")

        if submitted and amount > 0:
            append_transaction(
                data,
                {
                    "kind": "payment",
                    "date": payment_date.isoformat(),
                    "card": payment_card,
                    "category": category,
                    "amount": amount,
                    "direction": -1 if direction_label == "취소/환불" else 1,
                    "memo": memo,
                },
            )
            st.rerun()

    with input_cols[1]:
        st.subheader("혜택 사용")
        benefit_card = st.selectbox("카드", list(CARD_DB), key="benefit_card")
        benefit_rules = CARD_DB[benefit_card].get("benefit_rules", {})

        if benefit_rules:
            with st.form("benefit_form", clear_on_submit=True):
                benefit_date = st.date_input("날짜", value=date.today(), key="benefit_date")
                benefit_name = st.selectbox("혜택", list(benefit_rules), key="benefit_name")
                benefit_memo = st.text_input("메모", key="benefit_memo")
                benefit_submitted = st.form_submit_button("사용 기록")

            if benefit_submitted:
                append_transaction(
                    data,
                    {
                        "kind": "benefit",
                        "date": benefit_date.isoformat(),
                        "card": benefit_card,
                        "benefit": benefit_name,
                        "amount": 0,
                        "direction": 1,
                        "memo": benefit_memo,
                    },
                )
                st.rerun()
        else:
            st.info("등록된 횟수형 혜택이 없습니다.")

with tab_history:
    st.subheader(f"{selected_month} 거래내역")
    history_df = transaction_frame(month_transactions)

    if history_df.empty:
        st.caption("거래내역이 없습니다.")
    else:
        st.dataframe(history_df, use_container_width=True, hide_index=True)
        delete_id = st.selectbox("삭제할 거래", history_df["ID"].tolist())
        if st.button("선택 거래 삭제", type="secondary"):
            delete_transaction(data, delete_id)
            st.rerun()

with tab_settings:
    st.subheader("초기 전월 실적")
    with st.form("manual_prev_usage_form"):
        updated_prev_usage = {}
        setting_cols = st.columns(3)
        for index, card_name in enumerate(CARD_DB):
            with setting_cols[index % 3]:
                updated_prev_usage[card_name] = st.number_input(
                    card_name,
                    min_value=0,
                    step=10_000,
                    value=int(data["manual_prev_usage"].get(card_name, 0)),
                    key=f"prev_{card_name}",
                )
        if st.form_submit_button("초기값 저장"):
            data["manual_prev_usage"].update(updated_prev_usage)
            save_data(data)
            st.rerun()

    st.subheader("카드 규칙")
    rules_rows = []
    for card_name, card_info in CARD_DB.items():
        rules_rows.append(
            {
                "카드": card_name,
                "카드사": card_info["company"],
                "결제분류": ", ".join(card_info["spend_categories"]),
                "횟수형혜택": ", ".join(card_info.get("benefit_rules", {})) or "-",
            }
        )
    st.dataframe(pd.DataFrame(rules_rows), use_container_width=True, hide_index=True)

    export_json = json.dumps(data, ensure_ascii=False, indent=2)
    st.download_button(
        "데이터 백업",
        export_json,
        file_name=f"cardmanager-{selected_month}.json",
        mime="application/json",
    )
