import { defineCollection, z, reference } from 'astro:content';

// ================================================================================
// CONTENT COLLECTIONS — PILGRIMAGE SITE
// ================================================================================
// These schemas are LOCKED. Do not modify without architectural review.
// Each collection serves a specific purpose in the site's information architecture.
// ================================================================================

// ================================================================================
// HUBS COLLECTION
// ================================================================================
// Purpose: Authority pages that define topics and link downward
// Monetization: NEVER
// Word count target: 2000-3000 words
// ================================================================================
const hubs = defineCollection({
    type: 'content',
    schema: z.object({
        // Required fields
        title: z.string().max(70),
        description: z.string().max(160),
        
        // SEO and metadata
        lastUpdated: z.date().optional(),
        
        // Taxonomy
        topics: z.array(z.string()).optional(),
        
        // Internal linking
        relatedPlaces: z.array(z.string()).optional(),
        relatedRoutes: z.array(z.string()).optional(),
        
        // Image
        image: z.string().optional(),
        imageAlt: z.string().optional(),
        imageCredit: z.string().optional(),
        
        // Publishing state
        draft: z.boolean().default(false),
    }),
});

// ================================================================================
// PLACES COLLECTION
// ================================================================================
// Purpose: Destinations and sacred sites
// Monetization: OPTIONAL — only in "Experiencing This Place Today" section
// Word count target: 1200-2500 words
// ================================================================================
const places = defineCollection({
    type: 'content',
    schema: z.object({
        // Required fields
        title: z.string().max(70),
        description: z.string().max(160),
        
        // Geographic data
        region: z.string(),
        country: z.string(),
        coordinates: z.object({
            lat: z.number(),
            lng: z.number(),
        }).optional(),
        
        // Taxonomy
        faithTraditions: z.array(z.string()).optional(),
        placeType: z.enum([
            'shrine',
            'temple',
            'church',
            'mosque',
            'monastery',
            'natural-site',
            'historical-site',
            'pilgrimage-destination',
            'other'
        ]).optional(),
        
        // Relationships
        parentHub: z.string().optional(),
        relatedRoutes: z.array(z.string()).optional(),
        
        // Monetization flag
        // When true, the "Experiencing This Place Today" section is enabled
        hasExperienceSection: z.boolean().default(false),
        
        // Image
        image: z.string().optional(),
        imageAlt: z.string().optional(),
        imageCredit: z.string().optional(),
        
        // SEO and metadata
        lastUpdated: z.date().optional(),
        
        // Publishing state
        draft: z.boolean().default(false),
    }),
});

// ================================================================================
// ROUTES COLLECTION
// ================================================================================
// Purpose: Pilgrimage routes and paths
// Monetization: OPTIONAL — only in "Modern Pilgrimage Experiences" section
// Word count target: 1200-2500 words
// ================================================================================
const routes = defineCollection({
    type: 'content',
    schema: z.object({
        // Required fields
        title: z.string().max(70),
        description: z.string().max(160),
        
        // Route data
        region: z.string(),
        countries: z.array(z.string()),
        distanceKm: z.number().optional(),
        typicalDurationDays: z.number().optional(),
        
        // Taxonomy
        faithTraditions: z.array(z.string()).optional(),
        difficulty: z.enum(['easy', 'moderate', 'challenging', 'difficult']).optional(),
        
        // Relationships
        parentHub: z.string().optional(),
        placesOnRoute: z.array(z.string()).optional(),
        
        // Monetization flag
        // When true, the "Modern Pilgrimage Experiences" section is enabled
        hasModernSection: z.boolean().default(false),
        
        // Image
        image: z.string().optional(),
        imageAlt: z.string().optional(),
        imageCredit: z.string().optional(),
        
        // SEO and metadata
        lastUpdated: z.date().optional(),
        
        // Publishing state
        draft: z.boolean().default(false),
    }),
});

// ================================================================================
// STORIES COLLECTION
// ================================================================================
// Purpose: People, traditions, cultural narratives
// Monetization: NO by default
// Word count target: 1000-2000 words
// ================================================================================
const stories = defineCollection({
    type: 'content',
    schema: z.object({
        // Required fields
        title: z.string().max(70),
        description: z.string().max(160),
        
        // Story categorization
        storyType: z.enum([
            'historical-figure',
            'tradition',
            'cultural-practice',
            'pilgrimage-account',
            'legend',
            'other'
        ]),
        
        // Taxonomy
        faithTraditions: z.array(z.string()).optional(),
        timePeriod: z.string().optional(),
        
        // Relationships
        parentHub: z.string().optional(),
        relatedPlaces: z.array(z.string()).optional(),
        relatedRoutes: z.array(z.string()).optional(),
        
        // Image
        image: z.string().optional(),
        imageAlt: z.string().optional(),
        imageCredit: z.string().optional(),
        
        // SEO and metadata
        lastUpdated: z.date().optional(),
        
        // Publishing state
        draft: z.boolean().default(false),
    }),
});

// ================================================================================
// CONTEXT COLLECTION
// ================================================================================
// Purpose: Historical and cultural background articles
// Monetization: NEVER
// Word count target: 1000-2000 words
// ================================================================================
const context = defineCollection({
    type: 'content',
    schema: z.object({
        // Required fields
        title: z.string().max(70),
        description: z.string().max(160),
        
        // Context categorization
        contextType: z.enum([
            'historical-background',
            'cultural-overview',
            'religious-context',
            'geographical-context',
            'terminology',
            'other'
        ]),
        
        // Taxonomy
        faithTraditions: z.array(z.string()).optional(),
        regions: z.array(z.string()).optional(),
        
        // Relationships
        parentHub: z.string().optional(),
        
        // Image
        image: z.string().optional(),
        imageAlt: z.string().optional(),
        imageCredit: z.string().optional(),
        
        // SEO and metadata
        lastUpdated: z.date().optional(),
        
        // Publishing state
        draft: z.boolean().default(false),
    }),
});

// ================================================================================
// RESEARCH COLLECTION
// ================================================================================
// Purpose: Biblical archaeology blog posts (imported from WordPress)
// Function: Topical authority / informational SEO arm
// Word count: Varies (800-4000+ words)
// URL structure: /research/[category]/[slug]
// ================================================================================
const research = defineCollection({
    type: 'content',
    schema: z.object({
        // Required fields
        title: z.string(),
        description: z.string().max(160),

        // Categorization — maps to Tier 2 hub
        category: z.enum([
            'biblical-archaeology',
            'scripture',
            'excavations',
            'artifacts',
            'faith',
        ]),

        // Taxonomy
        topics: z.array(z.string()).optional(),

        // Relationships
        parentHub: z.string().optional(),

        // Image
        image: z.string().optional(),
        imageAlt: z.string().optional(),
        imageCredit: z.string().optional(),
        imageWidth: z.number().optional(),
        imageHeight: z.number().optional(),

        // SEO and metadata
        pubDate: z.date().optional(),
        lastUpdated: z.date().optional(),

        // Publishing state
        draft: z.boolean().default(false),
    }),
});

// ================================================================================
// EXPORT COLLECTIONS
// ================================================================================
export const collections = {
    hubs,
    places,
    routes,
    stories,
    context,
    research,
};
