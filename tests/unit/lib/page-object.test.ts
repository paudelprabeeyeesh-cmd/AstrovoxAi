import { describe, it, expect } from 'vitest'

class TestPageObject {
  readonly url = '/test'
  locators(page) {
    return {
      button: page.locator('button'),
      input: page.locator('input')
    }
  }
}

describe('page-object', () => {
  it('PageObject has url property', () => {
    const po = new TestPageObject()
    expect(po.url).toBe('/test')
  })

  it('PageObject.getLocator returns locator by key', () => {
    const po = new TestPageObject()
    const mockPage = {
      locator: (selector) => ({ selector, click: () => {}, fill: () => {}, isVisible: () => true, textContent: () => 'text' })
    }
    const locator = (po as any).getLocator(mockPage, 'button')
    expect(locator.selector).toBe('button')
  })
})