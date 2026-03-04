import * as Sentry from "@sentry/astro";

Sentry.init({
  dsn: "https://ad97ec4eb918831326bdd111f0ec3b3b@o4508247438655488.ingest.us.sentry.io/4510983740522496",
  integrations: [
    Sentry.browserTracingIntegration(),
    Sentry.replayIntegration(),
  ],
  tracesSampleRate: 0.1,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
});
