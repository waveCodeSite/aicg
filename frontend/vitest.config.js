import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  test: {
    environment: 'node', // 改为node环境支持WSL
    globals: true,
    setupFiles: ['./src/tests/setup.js'],
    include: ['src/tests/unit/**/*.test.js'],
    exclude: ['node_modules/', 'dist/'],
    // WSL优化配置
    pool: 'forks',
    poolOptions: {
      forks: {
        singleFork: true,
        isolate: false,
        minForks: 1,
        maxForks: 1
      }
    },
    testTimeout: 30000,
    hookTimeout: 30000,
    watch: false,
    maxConcurrency: 1,
    maxWorkers: 1,
    // 禁用覆盖率以简化环境
    coverage: { enabled: false }
  }
})