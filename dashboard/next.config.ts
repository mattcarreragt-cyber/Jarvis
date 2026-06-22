import type { NextConfig } from "next";

// BUILD_TARGET=export  → site statique dans out/ (pour l'APK Capacitor)
// sinon                → standalone (build serveur Docker, défaut)
const isExport = process.env.BUILD_TARGET === "export";

const nextConfig: NextConfig = {
  output: isExport ? "export" : "standalone",
  ...(isExport ? { images: { unoptimized: true } } : {}),
};

export default nextConfig;
