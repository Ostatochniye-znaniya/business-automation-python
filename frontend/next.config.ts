import type { NextConfig } from "next";

const backend = (process.env.BACKEND_URL || "http://127.0.0.1:8001").replace(
  /\/$/,
  "",
);
const config: NextConfig = {
  basePath: "/csh",
  output: "standalone",
  reactStrictMode: true,
  experimental: { proxyClientMaxBodySize: "21mb" },
  async redirects() {
    return [
      { source: "/", destination: "/csh", basePath: false, permanent: false },
      {
        source: "/pages/:page.html",
        destination: "/csh",
        basePath: false,
        permanent: false,
      },
    ];
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
      { source: "/health", destination: `${backend}/health`, basePath: false },
      { source: "/docs", destination: `${backend}/docs`, basePath: false },
      {
        source: "/openapi.json",
        destination: `${backend}/openapi.json`,
        basePath: false,
      },
      {
        source: "/api/:path*",
        destination: `${backend}/api/:path*`,
        basePath: false,
      },
    ];
  },
};
export default config;
