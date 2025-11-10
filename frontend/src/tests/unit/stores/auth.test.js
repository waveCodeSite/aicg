/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

// 模拟authService
vi.mock('@/services/auth', () => ({
  authService: {
    login: vi.fn(),
    register: vi.fn(),
    getCurrentUser: vi.fn(),
    updateProfile: vi.fn(),
    changePassword: vi.fn(),
    logout: vi.fn()
  }
}))

// 模拟localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}
global.localStorage = localStorageMock

describe('auth store', () => {
  let authStore

  beforeEach(() => {
    const pinia = createPinia()
    setActivePinia(pinia)
    authStore = useAuthStore()

    // 清除所有模拟调用记录
    vi.clearAllMocks()
  })

  afterEach(() => {
    // 重置localStorage模拟
    localStorageMock.getItem.mockClear()
    localStorageMock.setItem.mockClear()
    localStorageMock.removeItem.mockClear()
  })

  describe('初始状态', () => {
    it('应该从localStorage恢复token', () => {
      const testToken = 'test-token'
      localStorageMock.getItem.mockReturnValue(testToken)

      // 重新创建store
      const newAuthStore = useAuthStore()

      expect(newAuthStore.token).toBe(testToken)
      expect(localStorageMock.getItem).toHaveBeenCalledWith('token')
    })

    it('应该有正确的初始状态', () => {
      expect(authStore.token).toBe('')
      expect(authStore.user).toBe(null)
      expect(authStore.loading).toBe(false)
      expect(authStore.isAuthenticated).toBe(false)
    })

    it('应该根据token计算isAuthenticated', () => {
      expect(authStore.isAuthenticated).toBe(false)

      authStore.token = 'some-token'
      expect(authStore.isAuthenticated).toBe(true)

      authStore.token = ''
      expect(authStore.isAuthenticated).toBe(false)
    })
  })

  describe('登录功能', () => {
    it('应该成功登录', async () => {
      const { authService } = await import('@/services/auth')
      const mockResponse = {
        access_token: 'test-token',
        user: { id: '1', username: 'testuser' }
      }
      authService.login.mockResolvedValue(mockResponse)
      authService.getCurrentUser.mockResolvedValue(mockResponse.user)

      await authStore.login({
        username: 'testuser',
        password: 'password'
      })

      expect(authService.login).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password'
      })
      expect(authStore.token).toBe('test-token')
      expect(authStore.user).toEqual(mockResponse.user)
      expect(localStorageMock.setItem).toHaveBeenCalledWith('token', 'test-token')
    })

    it('应该处理登录错误', async () => {
      const { authService } = await import('@/services/auth')
      const error = new Error('登录失败')
      authService.login.mockRejectedValue(error)

      await expect(authStore.login({
        username: 'testuser',
        password: 'wrongpassword'
      })).rejects.toThrow('登录失败')

      expect(authStore.token).toBe('')
      expect(authStore.user).toBe(null)
    })

    it('应该在登录过程中设置loading状态', async () => {
      const { authService } = await import('@/services/auth')
      let resolveLogin
      const loginPromise = new Promise(resolve => {
        resolveLogin = resolve
      })
      authService.login.mockReturnValue(loginPromise)

      const loginCall = authStore.login({ username: 'test', password: 'test' })

      expect(authStore.loading).toBe(true)

      resolveLogin({ access_token: 'token', user: {} })
      await loginCall

      expect(authStore.loading).toBe(false)
    })
  })

  describe('注册功能', () => {
    it('应该成功注册', async () => {
      const { authService } = await import('@/services/auth')
      const userData = {
        username: 'newuser',
        email: 'test@example.com',
        password: 'password',
        display_name: 'New User'
      }
      const mockResponse = { id: '1', ...userData }
      authService.register.mockResolvedValue(mockResponse)

      const result = await authStore.register(userData)

      expect(authService.register).toHaveBeenCalledWith(userData)
      expect(result).toEqual(mockResponse)
    })

    it('应该处理注册错误', async () => {
      const { authService } = await import('@/services/auth')
      const error = new Error('注册失败')
      authService.register.mockRejectedValue(error)

      await expect(authStore.register({
        username: 'newuser',
        email: 'test@example.com',
        password: 'password'
      })).rejects.toThrow('注册失败')
    })
  })

  describe('获取当前用户', () => {
    it('应该成功获取用户信息', async () => {
      const { authService } = await import('@/services/auth')
      const mockUser = { id: '1', username: 'testuser' }
      authService.getCurrentUser.mockResolvedValue(mockUser)

      await authStore.getCurrentUser()

      expect(authService.getCurrentUser).toHaveBeenCalled()
      expect(authStore.user).toEqual(mockUser)
    })

    it('应该在没有token时跳过获取用户', async () => {
      const { authService } = await import('@/services/auth')

      await authStore.getCurrentUser()

      expect(authService.getCurrentUser).not.toHaveBeenCalled()
    })

    it('应该在获取用户失败时登出', async () => {
      authStore.token = 'some-token'

      const { authService } = await import('@/services/auth')
      authService.getCurrentUser.mockRejectedValue(new Error('Token无效'))

      await expect(authStore.getCurrentUser()).rejects.toThrow('Token无效')

      expect(authStore.token).toBe('')
      expect(authStore.user).toBe(null)
    })
  })

  describe('更新用户资料', () => {
    it('应该成功更新用户资料', async () => {
      const { authService } = await import('@/services/auth')
      const updateData = { display_name: 'New Name' }
      const mockUpdatedUser = { id: '1', username: 'testuser', display_name: 'New Name' }
      authService.updateProfile.mockResolvedValue(mockUpdatedUser)

      await authStore.updateProfile(updateData)

      expect(authService.updateProfile).toHaveBeenCalledWith(updateData)
      expect(authStore.user).toEqual(mockUpdatedUser)
    })
  })

  describe('修改密码', () => {
    it('应该成功修改密码', async () => {
      const { authService } = await import('@/services/auth')
      const passwordData = {
        old_password: 'oldpass',
        new_password: 'newpass'
      }
      authService.changePassword.mockResolvedValue({})

      await authStore.changePassword(passwordData)

      expect(authService.changePassword).toHaveBeenCalledWith(passwordData)
    })
  })

  describe('登出功能', () => {
    it('应该清除用户数据', () => {
      authStore.token = 'some-token'
      authStore.user = { id: '1', username: 'test' }

      authStore.logout()

      expect(authStore.token).toBe('')
      expect(authStore.user).toBe(null)
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('token')
    })
  })

  describe('头像管理', () => {
    it('应该成功上传头像', async () => {
      const { authService } = await import('@/services/auth')
      const mockFile = new File([''], 'avatar.jpg')
      const mockResponse = {
        user: { id: '1', avatar_url: 'http://example.com/avatar.jpg' }
      }
      authService.uploadAvatar.mockResolvedValue(mockResponse)

      await authStore.uploadAvatar(mockFile)

      expect(authService.uploadAvatar).toHaveBeenCalledWith(mockFile)
      expect(authStore.user.avatar_url).toBe('http://example.com/avatar.jpg')
    })

    it('应该成功删除头像', async () => {
      const { authService } = await import('@/services/auth')
      authStore.user = { id: '1', avatar_url: 'http://example.com/avatar.jpg' }
      const mockResponse = {
        user: { id: '1', avatar_url: null }
      }
      authService.deleteAvatar.mockResolvedValue(mockResponse)

      await authStore.removeAvatar()

      expect(authService.deleteAvatar).toHaveBeenCalled()
      expect(authStore.user.avatar_url).toBe(null)
    })
  })

  describe('获取用户统计', () => {
    it('应该获取用户统计信息', async () => {
      const { authService } = await import('@/services/auth')
      const mockStats = { projects_count: 5, generations_count: 10 }
      authService.getUserStats.mockResolvedValue(mockStats)

      const result = await authStore.getUserStats()

      expect(authService.getUserStats).toHaveBeenCalled()
      expect(result).toEqual(mockStats)
    })
  })
})