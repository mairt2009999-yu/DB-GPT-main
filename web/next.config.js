/** @type {import('next').NextConfig} */
const CopyPlugin = require('copy-webpack-plugin');
const MonacoWebpackPlugin = require('monaco-editor-webpack-plugin');
const path = require('path');
const DEFAULT_GATEWAY_API_BASE = 'http://127.0.0.1:8080/api/dbgpt/v1';
const nextConfig = {
  experimental: {
    esmExternals: 'loose',
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  env: {
    API_BASE_URL: process.env.API_BASE_URL || DEFAULT_GATEWAY_API_BASE,
    NEXT_PUBLIC_GATEWAY_API_BASE: process.env.NEXT_PUBLIC_GATEWAY_API_BASE || DEFAULT_GATEWAY_API_BASE,
    GITHUB_CLIENT_ID: process.env.GITHUB_CLIENT_ID,
    GOOGLE_CLIENT_ID: process.env.GOOGLE_CLIENT_ID,
    GET_USER_URL: process.env.GET_USER_URL,
    LOGIN_URL: process.env.LOGIN_URL,
    LOGOUT_URL: process.env.LOGOUT_URL,
  },
  trailingSlash: true,
  images: { unoptimized: true },
  skipTrailingSlashRedirect: true,
  webpack: (config, { isServer }) => {
    config.resolve.fallback = { fs: false };
    if (!isServer) {
      config.plugins.push(
        new CopyPlugin({
          patterns: [
            {
              from: path.join(__dirname, 'node_modules/@oceanbase-odc/monaco-plugin-ob/worker-dist/'),
              to: 'static/ob-workers',
            },
          ],
        }),
      );
      // 添加 monaco-editor-webpack-plugin 插件
      config.plugins.push(
        new MonacoWebpackPlugin({
          // 你可以在这里配置插件的选项，例如：
          languages: ['sql'],
          filename: 'static/[name].worker.js',
        }),
      );
    }
    return config;
  },
};

const withTM = require('next-transpile-modules')([
  '@berryv/g2-react',
  '@antv/g2',
  'react-syntax-highlighter',
  '@antv/g6',
  '@antv/graphin',
  '@antv/gpt-vis',
]);

module.exports = withTM({
  ...nextConfig,
});
