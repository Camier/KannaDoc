import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: `${process.env.MINO_IMAGE_URL_PREFIX}`,
        //hostname: '192.168.1.5',
        port: '80', // 如果使用的是特定端口
        pathname: '/minio-file/**', // 允许所有路径
      },
    ], // 允许加载来自 minio 的图片
        // 允许 data URLs
    domains: ['data:'],
  },
};

export default nextConfig;
