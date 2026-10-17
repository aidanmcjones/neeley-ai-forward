import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { DataProvider, useData } from "./lib/data";
import { Chrome, PaletteProvider, SampleBanner, SideNav, SourceProvider } from "./components";
import Briefing from "./screens/Briefing";
import Ask from "./screens/Ask";
import Product from "./screens/Product";
import Forces from "./screens/Forces";
import Proof from "./screens/Proof";
import Moat from "./screens/Moat";
import Memo from "./screens/Memo";
import Chat from "./screens/Chat";

function Shell() {
  const { sample } = useData();
  return (
    <div className="app-shell h-screen min-w-[1280px] flex flex-col overflow-hidden">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-[70] focus:m-2 focus:rounded focus:bg-purple-deep focus:px-3 focus:py-1 focus:text-white">
        Skip to content
      </a>
      <Chrome />
      <div className="flex flex-1 min-h-0">
        <SideNav />
        <main id="main" tabIndex={-1} className="relative flex-1 min-w-0 overflow-y-auto overflow-x-hidden px-6 py-5 space-y-4">
          {sample && <SampleBanner />}
          <Outlet />
        </main>
      </div>
    </div>
  );
}

// Old cockpit links (#/ask, #/memo, ...) now live under /cockpit.
function ToCockpit() {
  const { pathname, search } = useLocation();
  return <Navigate to={`/cockpit${pathname}${search}`} replace />;
}

export default function App() {
  return (
    <DataProvider>
      <SourceProvider>
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/cockpit" element={<PaletteProvider><Shell /></PaletteProvider>}>
            <Route index element={<Briefing />} />
            <Route path="ask" element={<Ask />} />
            <Route path="product" element={<Product />} />
            <Route path="forces" element={<Forces />} />
            <Route path="proof" element={<Proof />} />
            <Route path="moat" element={<Moat />} />
            <Route path="memo" element={<Memo />} />
            <Route path="*" element={<Navigate to="/cockpit" replace />} />
          </Route>
          {["/ask", "/product", "/forces", "/proof", "/moat", "/memo"].map((p) => <Route key={p} path={p} element={<ToCockpit />} />)}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </SourceProvider>
    </DataProvider>
  );
}
