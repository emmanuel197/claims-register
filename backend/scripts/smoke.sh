#!/usr/bin/env bash
# End-to-end smoke test against a running API (local or hosted).
#
#   ./scripts/smoke.sh                       # http://localhost:8000
#   ./scripts/smoke.sh https://your-api.onrender.com
#
# Exercises every endpoint and checks the totals-row identities with jq.
set -o errexit -o pipefail

API="${1:-http://localhost:8000}/api"
pass() { printf '  PASS  %s\n' "$1"; }
fail() { printf '  FAIL  %s\n' "$1"; exit 1; }
check() { [ "$1" = "$2" ] && pass "$3 ($1)" || fail "$3 — expected $2, got $1"; }

echo "Smoke-testing $API"

check "$(curl -sS "$API/health/" | jq -r .status)" "ok" "health"
check "$(curl -sS "$API/meta/" | jq '.currencies | length')" "4" "meta lists 4 currencies"

echo "-- register a claim"
CLAIM=$(curl -sS -X POST "$API/claims/" -H 'Content-Type: application/json' -d '{
  "policy_number": "SMOKE-'"$(date +%s)"'", "insured_name": "Smoke Test",
  "loss_date": "2026-06-01", "date_notified": "2026-06-02", "loss_nature": "motor",
  "currency": "GHS", "estimated_loss_amount": "10000.00"}')
ID=$(echo "$CLAIM" | jq -r .id)
check "$(echo "$CLAIM" | jq -r .status)" "reserved" "new claim is reserved"
check "$(echo "$CLAIM" | jq -r .outstanding_balance)" "null" "no balance before approval"

echo "-- approve"
APPROVED=$(curl -sS -X PATCH "$API/claims/$ID/" -H 'Content-Type: application/json' -d '{"approved_amount": "9120.00"}')
check "$(echo "$APPROVED" | jq -r .status)" "settled_outstanding" "approved claim is settled_outstanding"

echo "-- cross-currency payment: 500 USD @ 15.20 = 7600.00 GHS"
PAY=$(curl -sS -X POST "$API/claims/$ID/payments/" -H 'Content-Type: application/json' -d '{
  "payment_date": "2026-06-10", "amount": "500.00", "currency": "USD", "exchange_rate": "15.20"}')
check "$(echo "$PAY" | jq -r .payment.amount_in_claim_currency)" "7600.00" "converted amount"
check "$(echo "$PAY" | jq -r .claim.outstanding_balance)" "1520.00" "balance after USD payment"

echo "-- same-currency payment settles exactly"
PAY2=$(curl -sS -X POST "$API/claims/$ID/payments/" -H 'Content-Type: application/json' -d '{
  "payment_date": "2026-06-20", "amount": "1520.00", "currency": "GHS"}')
check "$(echo "$PAY2" | jq -r .claim.status)" "settled_paid" "zero balance is settled_paid"
check "$(echo "$PAY2" | jq -r .claim.outstanding_balance)" "0.00" "balance is 0.00"

echo "-- validation"
check "$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$API/claims/$ID/payments/" -H 'Content-Type: application/json' \
  -d '{"payment_date":"2026-06-20","amount":"1.00","currency":"USD"}')" "400" "missing rate rejected"
check "$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$API/claims/$ID/payments/" -H 'Content-Type: application/json' \
  -d '{"payment_date":"2026-06-20","amount":"1.00","currency":"GHS","exchange_rate":"2"}')" "400" "same-currency rate != 1 rejected"

echo "-- list + totals identities per currency"
LIST=$(curl -sS "$API/claims/")
COUNT=$(echo "$LIST" | jq .count)
[ "$COUNT" -ge 15 ] && pass "list has >= 15 claims ($COUNT)" || fail "list has only $COUNT claims"
check "$(echo "$LIST" | jq -r '.results | length')" "$COUNT" "results length matches count"

echo "$LIST" | jq -r '
  .totals.by_claim_currency[] as $t
  | [.results[] | select(.currency == $t.currency)] as $rows
  | ($rows | map(.total_paid | tonumber) | add) as $paid
  | ($rows | map(.outstanding_balance | select(. != null) | tonumber) | add // 0) as $out
  | ($t.total_paid | tonumber) as $tpaid
  | ($t.outstanding_balance | tonumber) as $tout
  | (($t.approved_amount|tonumber) - ($t.paid_on_settled|tonumber)) as $ident
  | if ($paid == $tpaid and $out == $tout and ($ident*100|round) == ($tout*100|round))
    then "  PASS  \($t.currency): rows sum to footer (paid \($t.total_paid), outstanding \($t.outstanding_balance))"
    else "  FAIL  \($t.currency): rows paid=\($paid) footer=\($tpaid); rows out=\($out) footer=\($tout); approved-paid_on_settled=\($ident)" end'

echo "$LIST" | grep -q FAIL && exit 1

echo "-- filters follow the footer"
F=$(curl -sS "$API/claims/?status=settled_paid&currency=GHS")
check "$(echo "$F" | jq '[.totals.by_claim_currency[].currency] | join(",")')" '"GHS"' "filtered totals only include GHS"
check "$(echo "$F" | jq '.totals.by_claim_currency[0].claims == .count')" "true" "footer claim count equals filtered count"

echo "All smoke checks passed."
