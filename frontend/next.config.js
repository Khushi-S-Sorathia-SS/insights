/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  // Image optimization
  images: {
    unoptimized: true,
  },
  // Webpack config
  webpack: (config) => {
    return config;
  },
};

module.exports = nextConfig;
