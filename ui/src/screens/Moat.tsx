import { useData } from "../lib/data";
import { ScreenFrame } from "../components";
import { CoverageMatrix } from "../components/moat/CoverageMatrix";
import { Architecture } from "../components/moat/Architecture";
import { CorpusTrust, MoatTiles, OnboardingCard, PipelineStrip, TablesInventory } from "../components/moat/Sections";

// Data moat: what we built this weekend and where the data lives.
export default function Moat() {
  const { meta, loading, error } = useData();
  return (
    <ScreenFrame
      title="Data moat"
      subtitle="What we built this weekend and where the data lives. Every number traces to a printed page."
      loading={loading} error={error}
    >
      <MoatTiles meta={meta} />
      <CoverageMatrix meta={meta} />
      <PipelineStrip meta={meta} />
      <TablesInventory meta={meta} />
      <CorpusTrust meta={meta} />
      <OnboardingCard meta={meta} />
      <Architecture />
    </ScreenFrame>
  );
}
