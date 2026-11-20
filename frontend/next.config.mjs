/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Builds a small self-contained server (.next/standalone) for the Docker image.
  output: "standalone",
};

export default nextConfig;
