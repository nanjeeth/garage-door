import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Dashboard from "./components/Dashboard";
import "./App.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchInterval: 5000 } },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="app">
        <header className="app-header">
          <h1>🏠 Home Watch</h1>
          <span className="subtitle">Garage Door Controller</span>
        </header>
        <Dashboard />
      </div>
    </QueryClientProvider>
  );
}
