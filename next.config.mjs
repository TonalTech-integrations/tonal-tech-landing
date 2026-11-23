/** @type {import('next').NextConfig} */
const basePath = '/tonal-tech-landing'

const nextConfig = {
  output: 'export',
  basePath,
  assetPrefix: basePath,
  env: {
    NEXT_PUBLIC_BASE_PATH: basePath,
  },
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
}

export default nextConfig
