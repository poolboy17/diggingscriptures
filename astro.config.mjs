import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';
import sitemap from '@astrojs/sitemap';
import sentry from '@sentry/astro';

// ================================================================================
// ASTRO CONFIGURATION — PILGRIMAGE SITE
// ================================================================================
// MODE: Static Site Generation (SSG) ONLY
// NO SSR, NO APIs, NO CMS, NO Databases
// ================================================================================

export default defineConfig({
    // Static output mode - no server required
    output: 'static',
    
    // Vite plugins
    vite: {
        plugins: [tailwindcss()]
    },
    
    // Integrations
    integrations: [
        react(),
        sitemap(),
        sentry({
            dsn: 'https://ad97ec4eb918831326bdd111f0ec3b3b@o4508247438655488.ingest.us.sentry.io/4510983740522496',
            org: 'none-4o0',
            project: 'diggingscriptures',
            authToken: process.env.SENTRY_AUTH_TOKEN,
            sourceMapsUploadOptions: {
                project: 'diggingscriptures',
                authToken: process.env.SENTRY_AUTH_TOKEN,
            },
        }),
    ],
    
    // Build configuration
    build: {
        // Inline stylesheets for performance
        inlineStylesheets: 'auto'
    },
    
    // Site configuration
    site: 'https://diggingscriptures.com',
    
    // Trailing slashes for clean URLs
    trailingSlash: 'never'
});
