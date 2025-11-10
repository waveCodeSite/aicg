/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import Login from '@/views/Login.vue'
import { useAuthStore } from '@/stores/auth'

// 模拟auth store
vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn()
}))

describe('Login.vue', () => {
  let wrapper
  let mockAuthStore
  let mockRouter

  beforeEach(() => {
    // 创建pinia实例
    const pinia = createPinia()
    setActivePinia(pinia)

    // 模拟auth store
    mockAuthStore = {
      login: vi.fn(),
      loading: false,
      isAuthenticated: false
    }
    useAuthStore.mockReturnValue(mockAuthStore)

    // 模拟router
    mockRouter = {
      push: vi.fn(),
      currentRoute: {
        value: {
          query: {}
        }
      }
    }

    wrapper = mount(Login, {
      global: {
        plugins: [pinia],
        mocks: {
          $router: mockRouter
        }
      }
    })
  })

  describe('组件渲染', () => {
    it('应该正确渲染登录表单', () => {
      expect(wrapper.find('h1').text()).toBe('欢迎回来')
      expect(wrapper.find('h2').text()).toBe('登录您的账户')
      expect(wrapper.find('form').exists()).toBe(true)
    })

    it('应该显示用户名和密码输入框', () => {
      const usernameInput = wrapper.find('input[type="text"]')
      const passwordInput = wrapper.find('input[type="password"]')

      expect(usernameInput.exists()).toBe(true)
      expect(passwordInput.exists()).toBe(true)
      expect(usernameInput.attributes('placeholder')).toContain('请输入用户名')
      expect(passwordInput.attributes('placeholder')).toContain('请输入密码')
    })

    it('应该显示登录按钮', () => {
      const loginButton = wrapper.find('button[type="submit"]')
      expect(loginButton.exists()).toBe(true)
      expect(loginButton.text()).toContain('登 录')
    })

    it('应该显示注册链接', () => {
      const registerLink = wrapper.find('a')
      expect(registerLink.exists()).toBe(true)
      expect(registerLink.text()).toContain('还没有账户？')
    })
  })

  describe('表单验证', () => {
    it('应该验证必填字段', async () => {
      const form = wrapper.findComponent({ name: 'ElForm' })
      await form.trigger('submit')

      // 应该显示验证错误
      expect(wrapper.text()).toContain('请输入用户名')
      expect(wrapper.text()).toContain('请输入密码')
    })

    it('应该在输入有效数据后不显示验证错误', async () => {
      // 填写表单
      await wrapper.find('input[type="text"]').setValue('testuser')
      await wrapper.find('input[type="password"]').setValue('password123')

      const form = wrapper.findComponent({ name: 'ElForm' })
      await form.trigger('submit')

      // 不应该显示验证错误
      expect(wrapper.text()).not.toContain('请输入用户名')
      expect(wrapper.text()).not.toContain('请输入密码')
    })
  })

  describe('登录功能', () => {
    it('应该在表单提交时调用登录方法', async () => {
      mockAuthStore.login.mockResolvedValue({})

      // 填写表单
      await wrapper.find('input[type="text"]').setValue('testuser')
      await wrapper.find('input[type="password"]').setValue('password123')

      // 提交表单
      const form = wrapper.find('form')
      await form.trigger('submit.prevent')

      expect(mockAuthStore.login).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password123'
      })
    })

    it('应该在登录成功后重定向', async () => {
      mockAuthStore.login.mockResolvedValue({})

      // 填写并提交表单
      await wrapper.find('input[type="text"]').setValue('testuser')
      await wrapper.find('input[type="password"]').setValue('password123')
      await wrapper.find('form').trigger('submit.prevent')

      // 等待登录完成
      await wrapper.vm.$nextTick()

      expect(mockRouter.push).toHaveBeenCalledWith('/dashboard')
    })

    it('应该在登录失败时不重定向', async () => {
      mockAuthStore.login.mockRejectedValue(new Error('登录失败'))

      // 填写并提交表单
      await wrapper.find('input[type="text"]').setValue('testuser')
      await wrapper.find('input[type="password"]').setValue('wrongpassword')
      await wrapper.find('form').trigger('submit.prevent')

      // 等待登录完成
      await wrapper.vm.$nextTick()

      expect(mockRouter.push).not.toHaveBeenCalled()
    })

    it('应该处理查询参数中的重定向地址', async () => {
      mockAuthStore.login.mockResolvedValue({})

      // 设置重定向查询参数
      mockRouter.currentRoute.value.query = { redirect: '/projects' }

      // 重新挂载组件以获取新的路由信息
      wrapper = mount(Login, {
        global: {
          plugins: [createPinia()],
          mocks: {
            $router: mockRouter
          }
        }
      })

      // 填写并提交表单
      await wrapper.find('input[type="text"]').setValue('testuser')
      await wrapper.find('input[type="password"]').setValue('password123')
      await wrapper.find('form').trigger('submit.prevent')

      expect(mockRouter.push).toHaveBeenCalledWith('/projects')
    })
  })

  describe('加载状态', () => {
    it('应该在加载时禁用登录按钮', async () => {
      mockAuthStore.loading = true

      // 重新挂载组件
      wrapper = mount(Login, {
        global: {
          plugins: [createPinia()],
          mocks: {
            $router: mockRouter
          }
        }
      })

      const loginButton = wrapper.find('button[type="submit"]')
      expect(loginButton.attributes('disabled')).toBeDefined()
      expect(loginButton.attributes('loading')).toBeDefined()
    })

    it('应该在加载时显示加载文本', async () => {
      mockAuthStore.loading = true

      wrapper = mount(Login, {
        global: {
          plugins: [createPinia()],
          mocks: {
            $router: mockRouter
          }
        }
      })

      expect(wrapper.text()).toContain('登录中')
    })
  })

  describe('用户体验', () => {
    it('应该支持回车键登录', async () => {
      mockAuthStore.login.mockResolvedValue({})

      // 填写表单
      await wrapper.find('input[type="text"]').setValue('testuser')
      await wrapper.find('input[type="password"]').setValue('password123')

      // 在密码输入框按回车
      const passwordInput = wrapper.find('input[type="password"]')
      await passwordInput.trigger('keyup.enter')

      expect(mockAuthStore.login).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password123'
      })
    })

    it('应该在已登录时重定向到仪表板', () => {
      mockAuthStore.isAuthenticated = true

      wrapper = mount(Login, {
        global: {
          plugins: [createPinia()],
          mocks: {
            $router: mockRouter
          }
        }
      })

      // 组件挂载时应该已经重定向
      expect(mockRouter.push).toHaveBeenCalledWith('/dashboard')
    })
  })
})