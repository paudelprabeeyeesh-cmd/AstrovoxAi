import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  transpilePackages: [],
  images: { remotePatterns: [] },
  experimental: { serverActions: { bodySizeLimit: '2mb' } },
};
export default nextConfig;
