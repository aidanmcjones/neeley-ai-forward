from agent.needle import predict


def test_forecast_uses_only_history():
    yoys = {f"20{y}Q{q}": 0.05 for y in (23, 24, 25) for q in (1, 2, 3, 4)}
    yoys["2026Q1"] = 0.99          # future value must not leak into a 2025Q4 forecast
    point, lo, hi = predict.forecast(yoys, "2025Q4", 1.4)
    assert abs(point - 0.05) < 1e-9 and lo < point < hi


def test_blind_test_is_out_of_sample_and_cited():
    r = predict.blind_test("JNJ", "2026Q3")
    assert r["prediction"]["made_at"] == "data through 2026Q2 only"
    assert r["answer_key"]["verifier"] == "verified"
    assert "earnings release" in r["answer_key"]["citation"]
    assert abs(r["actual"] - 0.059) < 1e-9
