"""SEO title/description optimizer — fixes short titles, thin descriptions, missing keywords."""
import os, re, sys, io, yaml
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'content')

OPTIMIZED = {
    # === HUBS ===
    'hubs/buddhist-pilgrimage-paths': {
        'title': "Buddhist Pilgrimage Paths: Sacred Sites of the Buddha",
        'desc': "Explore the sacred journeys of Buddhism, from the four great sites of the Buddha's life to temple circuits and meditation paths across Asia and beyond.",
    },
    'hubs/christian-pilgrimage-traditions': {
        'title': "Christian Pilgrimage Traditions: Holy Land to Camino",
        'desc': "A scholarly exploration of Christian pilgrimage practices from early Holy Land journeys and medieval routes to the diverse sacred travel traditions of today.",
    },
    'hubs/faith-based-journeys': {
        'title': "Faith-Based Journeys: Pilgrimage Across World Religions",
