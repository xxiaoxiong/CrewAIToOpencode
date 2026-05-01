import { describe, it, expect } from 'vitest'
import {
  getProductById,
  getProductsByCategory,
  searchProducts,
  products,
} from '@/data/products'

describe('Product Data', () => {
  it('should have products loaded', () => {
    expect(products.length).toBeGreaterThan(0)
  })

  it('should get product by id', () => {
    const product = getProductById('1')
    expect(product).toBeDefined()
    expect(product?.name).toBe('Wireless Headphones')
  })

  it('should return undefined for invalid id', () => {
    const product = getProductById('invalid')
    expect(product).toBeUndefined()
  })

  it('should filter products by category', () => {
    const electronics = getProductsByCategory('Electronics')
    expect(electronics.length).toBeGreaterThan(0)
    electronics.forEach((p) => expect(p.category).toBe('Electronics'))
  })

  it('should search products by name', () => {
    const results = searchProducts('headphones')
    expect(results.length).toBeGreaterThan(0)
  })

  it('should search products by description', () => {
    const results = searchProducts('wireless')
    expect(results.length).toBeGreaterThan(0)
  })

  it('should return empty array for no matches', () => {
    const results = searchProducts('nonexistentproduct123')
    expect(results.length).toBe(0)
  })
})

describe('Product Properties', () => {
  products.forEach((product) => {
    it(`product ${product.id} should have valid properties`, () => {
      expect(product.id).toBeDefined()
      expect(product.name).toBeDefined()
      expect(product.description).toBeDefined()
      expect(product.price).toBeGreaterThan(0)
      expect(product.category).toBeDefined()
      expect(product.stock).toBeGreaterThanOrEqual(0)
      expect(product.rating).toBeGreaterThan(0)
      expect(product.rating).toBeLessThanOrEqual(5)
    })
  })
})