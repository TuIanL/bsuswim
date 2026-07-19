import { vi } from 'vitest'
import { config } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

// 全局注册 Element Plus，使组件在单测中可渲染
config.global.plugins = [ElementPlus]

// jsdom 缺失的浏览器 API 桩
if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as any
}

// Element Plus 在 jsdom 下依赖 matchMedia
if (!window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false
  })) as any
}

// 避免 Element Plus 组件在测试里真正渲染弹出层导致噪声
window.URL.createObjectURL = window.URL.createObjectURL || (() => '')
