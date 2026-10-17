import type { Company } from "../../lib/types";
import type { Exhibit } from "../../lib/retrieve";
import { exhibitTitle } from "../../lib/exhibits";
import { TimelineExhibit } from "./TimelineExhibit";
import { HeadToHeadExhibit } from "./HeadToHeadExhibit";
import { PriceExhibit } from "./PriceExhibit";
import { PeerExhibit } from "./PeerExhibit";

// Render one exhibit {kind, ref} (also usable by the Memo screen for pinned exhibits).
export function ExhibitView({ exhibit, company, asOf }: { exhibit: Exhibit; company: Company; asOf?: string }) {
  const title = exhibit.title ?? exhibitTitle(exhibit, company);
  switch (exhibit.kind) {
    case "timeline": return <TimelineExhibit company={company} target={exhibit.ref} title={title} asOf={asOf} />;
    case "h2h": return <HeadToHeadExhibit company={company} target={exhibit.ref} title={title} />;
    case "price": return <PriceExhibit company={company} target={exhibit.ref} title={title} />;
    case "peer": return <PeerExhibit company={company} target={exhibit.ref} title={title} />;
    default: return null;
  }
}
