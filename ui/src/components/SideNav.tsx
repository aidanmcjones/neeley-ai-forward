import { NavLink } from "react-router-dom";

export const ROUTES = [
  { to: "/cockpit", label: "Briefing", end: true },
  { to: "/cockpit/ask", label: "Ask" },
  { to: "/cockpit/product", label: "Product" },
  { to: "/cockpit/forces", label: "Forces" },
  { to: "/cockpit/proof", label: "Proof" },
  { to: "/cockpit/moat", label: "Data moat" },
  { to: "/cockpit/memo", label: "Memo" },
] as const;

// Left nav, 220px. Plain links: Tab/Enter work natively; aria-current marks the active route.
export function SideNav() {
  return (
    <nav data-sidenav aria-label="Screens" className="no-print w-[220px] shrink-0 border-r border-line bg-surface flex flex-col">
      <ul className="py-3 space-y-0.5">
        {ROUTES.map((r) => (
          <li key={r.to}>
            <NavLink
              to={r.to}
              end={"end" in r ? r.end : false}
              className={({ isActive }) =>
                `mx-2 flex items-center rounded-md px-3 py-2 text-sm font-semibold ${
                  isActive ? "bg-purple dark:bg-purple-deep text-white" : "text-fg hover:bg-surface-2"
                }`
              }
            >
              {r.label}
            </NavLink>
          </li>
        ))}
      </ul>
      <div className="mt-auto px-5 py-4 text-[11px] text-muted space-y-1">
        <NavLink to="/" className="block font-semibold text-purple hover:underline">← Back to chat</NavLink>
        <div>Built by TCU Neeley students</div>
      </div>
    </nav>
  );
}
