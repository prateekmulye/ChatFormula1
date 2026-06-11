import "@fontsource/spectral/500.css";
import "@fontsource/spectral/600.css";
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/500.css";
import "@/app.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "@/App";
import { fireWakePing } from "@/lib/wake";

// Wake-on-paint (ARCHITECTURE §2): fire-and-forget /up ping at first paint so
// the agent's cold start overlaps with the visitor reading the hero copy.
fireWakePing();

const container = document.getElementById("root");
if (container === null) throw new Error("Missing #root element");

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
