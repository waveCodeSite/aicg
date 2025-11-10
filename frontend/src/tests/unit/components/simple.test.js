/**
 * @vitest-environment jsdom
 */

import { describe, it, expect } from 'vitest'

describe('简单测试', () => {
  it('应该通过基本测试', () => {
    expect(true).toBe(true)
  })

  it('应该正确处理数字计算', () => {
    expect(1 + 1).toBe(2)
  })

  it('应该正确处理字符串', () => {
    expect('hello'.toUpperCase()).toBe('HELLO')
  })
})