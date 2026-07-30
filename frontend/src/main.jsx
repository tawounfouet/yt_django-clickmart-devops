import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import * as Sentry from "@sentry/react";
import App from "./App.jsx";
import "./index.css";
import CartProvider from "./Provider/CartProvider.jsx";
import AuthProvider from "./Provider/AuthProvider.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  integrations: [Sentry.browserTracingIntegration()],
  tracesSampleRate: 0.1,
  enabled: import.meta.env.PROD,
});

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ErrorBoundary>
      <AuthProvider>
        <CartProvider>
          <App />
        </CartProvider>
      </AuthProvider>
    </ErrorBoundary>
  </StrictMode>
);
