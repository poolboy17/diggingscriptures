import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';

export async function GET(context: APIContext) {
  const posts = (await getCollection('research', ({ data }) => !data.draft))
    .sort((a, b) => {
      const da = a.data.pubDate ?? a.data.lastUpdated ?? new Date(0);
      const db = b.data.pubDate ?? b.data.lastUpdated ?? new Date(0);
      return new Date(db).getTime() - new Date(da).getTime();
    })
    .slice(0, 50);

  return rss({
    title: 'Digging Scriptures — Where Scripture Meets Science',
    description: 'Biblical archaeology, scripture analysis, and ancient world discoveries.',
    site: context.site!,
    items: posts.map((p) => ({
      title: p.data.title,
      pubDate: p.data.pubDate ?? p.data.lastUpdated,
      description: p.data.description,
      link: `/research/${p.data.category}/${p.id}/`,
    })),
  });
}
