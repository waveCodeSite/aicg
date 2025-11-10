import { vi } from 'vitest'

// 模拟浏览器API - Node.js环境需要
global.localStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}

global.sessionStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}

// 模拟window对象
global.window = global.window || {}
global.window.location = { href: 'http://localhost' }

// 模拟File对象（在Node.js环境中不存在）
global.File = class File {
  constructor(chunks, filename, options = {}) {
    this.name = filename
    this.size = chunks.reduce((acc, chunk) => acc + chunk.length, 0)
    this.type = options.type || ''
  }
}

// Element Plus模拟
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn()
  },
  ElMessageBox: {
    confirm: vi.fn(),
    alert: vi.fn(),
    prompt: vi.fn()
  }
}))

// Vue Router模拟
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    go: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    currentRoute: {
      value: {
        path: '/',
        query: {},
        params: {}
      }
    }
  }),
  useRoute: () => ({
    path: '/',
    query: {},
    params: {}
  })
}))

// Pinia模拟
vi.mock('pinia', () => ({
  createPinia: vi.fn(() => ({})),
  setActivePinia: vi.fn(),
  defineStore: vi.fn(() => vi.fn()),
  storeToRefs: vi.fn((obj) => obj)
}))

// Auth服务模拟
vi.mock('@/services/auth', () => ({
  authService: {
    login: vi.fn(),
    register: vi.fn(),
    getCurrentUser: vi.fn(),
    updateProfile: vi.fn(),
    changePassword: vi.fn(),
    logout: vi.fn(),
    uploadAvatar: vi.fn(),
    deleteAvatar: vi.fn(),
    getUserStats: vi.fn()
  }
}))

// Axios模拟
vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() }
    },
    create: vi.fn(() => ({
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn()
    }))
  }
}))

// 设置环境变量
process.env.NODE_ENV = 'test'
process.env.VITEST = 'true'