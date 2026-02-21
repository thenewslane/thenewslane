/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: [
    '@platform/types',
    '@platform/theme',
    '@platform/supabase',
  ],
};

export default nextConfig;
