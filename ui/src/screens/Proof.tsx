import { useData } from "../lib/data";
import { ScreenFrame } from "../components";
import { AiCaughtPanel, VerifierPanel } from "../components/proof/Verifier";
import { BacktestPanel } from "../components/proof/Backtest";
import { BlindPanel, CalibrationPanel, LimitsPanel, SealedPanel } from "../components/proof/Forecasts";

// Proof: the responsible-AI screen. AI reads; code checks; humans see what was held back.
export default function Proof() {
  const { meta, league, company, proof, ticker, setTicker, loading, error } = useData({ proof: true });
  return (
    <ScreenFrame
      title="Proof: does it hold up?"
      subtitle="Every claim is checked by code against the printed page, every model mistake we caught is logged, and every limit is stated."
      loading={loading} error={error}
    >
      <VerifierPanel meta={meta} league={league} rules={proof?.verifier_rules ?? meta?.verifier_rules ?? []} />
      <AiCaughtPanel company={company} ticker={ticker} league={league} aiWrong={proof?.ai_wrong ?? []} onPick={setTicker} />
      <BacktestPanel hitRates={proof?.backtest?.hit_rates} gate2={proof?.backtest?.gate2_md} />
      <div className="grid grid-cols-1 gap-4">
        <CalibrationPanel cal={proof?.calibration} />
        <BlindPanel blind={proof?.blind} />
      </div>
      <SealedPanel sealed={proof?.sealed} />
      <LimitsPanel limits={proof?.limits ?? meta?.limits ?? []} noSource={meta?.moat?.no_source ?? []} />
    </ScreenFrame>
  );
}
