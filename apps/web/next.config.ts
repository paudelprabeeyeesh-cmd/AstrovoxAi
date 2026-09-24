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
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
        ],
      },
    ]
  },
  async rewrites() {
    return [
      {
        source: '/sw.js',
        destination: '/sw.js',
      },
    ]
  },
};

export default nextConfig;
