import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // 使用自定义加载器
    loader: "custom",
    // 指定自定义加载器文件路径（需要创建这个文件）
    loaderFile: "./src/utils/imageLoader.ts",

    // 允许加载的域名（前端访问域名）
    remotePatterns: [
      {
        protocol: "http",
        hostname: `${process.env.MINO_IMAGE_URL_PREFIX}`,
        port: "80",
        pathname: "/minio-file/**",
      },
    ],

    // 允许 data URLs
    domains: ["data:"],
  },
};

export default nextConfig;
