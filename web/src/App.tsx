import { ApolloProvider } from "@apollo/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";

import { Shell } from "@/components/layout/shell";
import { apolloClient } from "@/lib/apollo";
import { AboutPage } from "@/routes/about-page";
import { CalendarPage } from "@/routes/calendar-page";
import { ChatPage } from "@/routes/chat-page";
import { DriversPage } from "@/routes/drivers-page";
import { StandingsPage } from "@/routes/standings-page";

export function App() {
  return (
    <ApolloProvider client={apolloClient}>
      <BrowserRouter>
        <Shell>
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/standings" element={<StandingsPage />} />
            <Route path="/calendar" element={<CalendarPage />} />
            <Route path="/drivers" element={<DriversPage />} />
            <Route path="/about" element={<AboutPage />} />
          </Routes>
        </Shell>
        <Toaster
          theme="dark"
          position="bottom-right"
          toastOptions={{
            style: {
              background: "var(--color-surface-2)",
              border: "1px solid var(--color-hairline-2)",
              color: "var(--color-text)",
            },
          }}
        />
      </BrowserRouter>
    </ApolloProvider>
  );
}
