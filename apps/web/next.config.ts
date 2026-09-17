import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@astrovox/ui"],
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "astrovox.ai",
      },
      {
        protocol: "https",
        hostname: "*.astrovox.ai",
      },
    ],
  },
  experimental: {
    serverActions: { bodySizeLimit: "2mb" },
  },
};

export default nextConfig;
