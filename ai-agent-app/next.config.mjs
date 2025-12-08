/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
};
export default nextConfig;


// /** @type {import('next').NextConfig} */
// const nextConfig = {
//   output: "standalone",
//   reactStrictMode: true,

//   async rewrites() {
//     const target = process.env.BACKEND_INTERNAL || "http://backend:8001";
//     return [
//       { source: "/api/:path*", destination: `${target}/:path*` },
//     ];
//   },
// };

// export default nextConfig;
