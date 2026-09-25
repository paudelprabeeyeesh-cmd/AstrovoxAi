import { MetadataRoute } from "next";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = "https://astrovox.ai";

  const pages = [
    { url: baseUrl, lastModified: new Date(), changeFrequency: "daily" as const, priority: 1 },
    { url: `${baseUrl}/pricing`, lastModified: new Date(), changeFrequency: "weekly" as const, priority: 0.8 },
  ];

  try {
    const fs = await import("fs");
    const path = await import("path");
    const docsDir = path.join(process.cwd(), "apps", "web", "app", "docs");
    if (fs.existsSync(docsDir)) {
      pages.push({ url: `${baseUrl}/docs`, lastModified: new Date(), changeFrequency: "weekly" as const, priority: 0.7 });
    }
  } catch {
    // ignore
  }

  return pages;
}
