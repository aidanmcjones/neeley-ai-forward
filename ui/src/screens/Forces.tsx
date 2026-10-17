import { useData } from "../lib/data";
import { EmptyState, ScreenFrame } from "../components";
import { GuidancePanel, IraCutCheck } from "../components/forces/Bottom";
import { ForcesCompare, useAllForces } from "../components/forces/ForcesCompare";
import { PricedIn } from "../components/forces/PricedIn";

// Three forces (IRA, MFN, tariffs) across the 10, then the priced-in scorecard and guidance/IRA checks for the selected company.
export default function Forces() {
  const { meta, company, ticker, setTicker, loading, error, source } = useData();
  const rows = useAllForces(meta, source, company);
  return (
    <ScreenFrame
      title="Three forces and priced-in"
      subtitle={<>IRA, most-favored-nation pricing and tariffs across the 10; then what analysts ask {ticker ?? "this company"} about and whether it shows up in the price</>}
      loading={loading}
      error={error}
    >
      <div className="space-y-4">
        <ForcesCompare rows={rows} selected={ticker} onSelect={setTicker} />
        {company ? (
          <>
            <PricedIn company={company} />
            <div className="grid grid-cols-1 min-[1700px]:grid-cols-2 gap-4 items-start">
              <GuidancePanel company={company} />
              <IraCutCheck company={company} />
            </div>
          </>
        ) : (
          <EmptyState file={`companies/${ticker}.json`} message={`Company file for ${ticker ?? "?"} not loaded`} />
        )}
      </div>
    </ScreenFrame>
  );
}
