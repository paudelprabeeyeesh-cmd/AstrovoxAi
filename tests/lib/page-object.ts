export abstract class PageObject {
  abstract readonly url: string

  async goto(page: Page) {
    await page.goto(this.url)
  }

  abstract locators(page: Page): Record<string, Locator>

  protected getLocator(page: Page, key: string): Locator {
    return this.locators(page)[key]
  }

  async click(page: Page, key: string) {
    await this.getLocator(page, key).click()
  }

  async fill(page: Page, key: string, value: string) {
    await this.getLocator(page, key).fill(value)
  }

  async isVisible(page: Page, key: string): Promise<boolean> {
    return this.getLocator(page, key).isVisible()
  }

  async textContent(page: Page, key: string): Promise<string | null> {
    return this.getLocator(page, key).textContent()
  }
}
