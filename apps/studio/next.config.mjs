/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: [
    '@platform/types',
    '@platform/supabase',
  ],
};

export default nextConfig;
