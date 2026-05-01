import '@testing-library/jest-dom'

const mockStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
  clear: () => {},
  key: () => null,
  length: 0,
}

Object.defineProperty(global, 'localStorage', {
  value: mockStorage,
  writable: true,
})