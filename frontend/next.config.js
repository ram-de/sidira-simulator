/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    SIDIRA_API_BASE_INTERNAL: process.env.SIDIRA_API_BASE_INTERNAL,
  },
  // typedRoutes is off for now — friction with dynamic href strings on the
  // landing page card grid. Revisit when the route shape stabilizes.
  experimental: {
    typedRoutes: false,
  },
};

module.exports = nextConfig;
