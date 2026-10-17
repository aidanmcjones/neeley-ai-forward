import { useEffect, useMemo, useState } from "react";
import { useData } from "../lib/data";
import { EmptyState, Panel, ScreenFrame } from "../components";
import { ComparisonTable } from "../components/product/ComparisonTable";
import { ExclusivityStrip } from "../components/product/ExclusivityStrip";
import { LimitsPanel } from "../components/product/LimitsPanel";
import { PriceSeries } from "../components/product/PriceSeries";
import { Segmented, drugName, makerOf } from "../components/product/util";

// Product fine print: one product vs its rivals on label, safety, dosing, exclusivity, pricing and gross-to-net,
// tied to the engine's label-derived findings and a priced-in line.
export default function Product() {
  const { meta, company, ticker, loading, error } = useData();
  const caseSet = meta?.case_sets?.[ticker ?? ""] ?? {};
  const products = Object.keys(caseSet);
  const [sel, setSel] = useState<string | null>(null);

  // Deep link: #/product?p=eliquis
  useEffect(() => {
    const q = window.location.hash.split("?")[1];
    const p = q ? new URLSearchParams(q).get("p") : null;
    setSel(p && products.includes(p) ? p : products[0] ?? null);
  }, [ticker, products.join(",")]); // eslint-disable-line react-hooks/exhaustive-deps

  const product = sel && products.includes(sel) ? sel : products[0];
  const comp = useMemo(() => company?.labels?.comparison?.find((c) => c.product === product), [company, product]);
  const rivals = comp?.rivals ?? caseSet[product ?? ""] ?? [];

  return (
    <ScreenFrame
      title="Product fine print"
      subtitle={product ? <>{drugName(product)} ({ticker}) vs {rivals.map(drugName).join(", ") || "no rivals listed"}: label, safety, dosing, exclusivity, pricing and gross-to-net</> : undefined}
      loading={loading}
      error={error}
    >
      {!products.length || !company ? (
        <EmptyState file="meta.json" message={`No case-set products for ${ticker ?? "this company"} (meta.json · case_sets.${ticker})`} />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-start gap-x-6 gap-y-2">
            <Segmented label="Product" value={product!} onChange={setSel} options={products.map((p) => ({ value: p, label: drugName(p) }))} />
            <div className="text-[12px] text-muted pt-1.5">
              Rivals:{" "}
              {rivals.length ? rivals.map((r, i) => {
                const m = makerOf(company, r);
                return <span key={r}>{i > 0 && ", "}<span className="font-semibold text-fg">{drugName(r)}</span>{m ? ` (${m})` : ""}</span>;
              }) : "none listed"}
              <span className="font-mono text-[10px] ml-2">meta.json · case_sets.{ticker}</span>
            </div>
          </div>

                    <Panel title="Side by side" meta={<span className="font-mono">labels.comparison · source under every cell</span>} bodyClassName="p-0">
              {comp ? <ComparisonTable comp={comp} company={company} /> : (
                <div className="p-4"><EmptyState file={`companies/${ticker}.json · labels.comparison[product=${product}]`} message={`No label comparison exported for ${drugName(product!)}`} /></div>
              )}
            </Panel>
          <LimitsPanel company={company} product={product!} />

          <Panel title="Exclusivity and IRA timeline" meta="2024 to 2032">
            {comp ? <ExclusivityStrip company={company} comp={comp} asOf={meta?.as_of} /> : (
              <EmptyState file={`companies/${ticker}.json · labels.comparison`} message="No exclusivity dates to plot" />
            )}
          </Panel>

          <Panel title="Price series" meta={<span className="font-mono">price_series</span>}>
            <PriceSeries company={company} product={product!} rivals={rivals} />
          </Panel>
        </div>
      )}
    </ScreenFrame>
  );
}
