import { Navigate, Route, Routes } from "react-router-dom";
import { SourceProvider } from "./components/SourceDrawer";
import Chat from "./screens/Chat";

// One page: the Part 1 chat at /. Every other path returns to it.
export default function App() {
  return (
    <SourceProvider>
      <Routes>
        <Route path="/" element={<Chat />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </SourceProvider>
  );
}
