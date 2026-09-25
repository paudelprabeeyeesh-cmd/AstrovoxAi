export function createRNStorage() {
  return {
    getItem: (key) => Promise.resolve(null),
    setItem: (key, value) => Promise.resolve(),
    removeItem: (key) => Promise.resolve(),
  }
}

export function createSecureStorage() {
  return {
    getItem: (key) => Promise.resolve(null),
    setItem: (key, value) => Promise.resolve(),
    removeItem: (key) => Promise.resolve(),
  }
}
