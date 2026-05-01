import { describe, it, expect, beforeEach } from 'vitest'
import { useCartStore } from '@/context/CartStore'

const testProduct = {
  id: 'test-1',
  name: 'Test Product',
  description: 'Test description',
  price: 99.99,
  category: 'Test',
  image: 'https://example.com/image.jpg',
  stock: 10,
  rating: 4.5,
}

describe('Cart Store', () => {
  beforeEach(() => {
    useCartStore.getState().clearCart()
  })

  it('should add item to cart', () => {
    const { addItem } = useCartStore.getState()
    addItem(testProduct)
    const { items } = useCartStore.getState()
    expect(items.length).toBe(1)
    expect(items[0].product.id).toBe(testProduct.id)
    expect(items[0].quantity).toBe(1)
  })

  it('should increment quantity for existing item', () => {
    const { addItem } = useCartStore.getState()
    addItem(testProduct)
    addItem(testProduct)
    const { items } = useCartStore.getState()
    expect(items.length).toBe(1)
    expect(items[0].quantity).toBe(2)
  })

  it('should remove item from cart', () => {
    const { addItem, removeItem } = useCartStore.getState()
    addItem(testProduct)
    removeItem(testProduct.id)
    const { items } = useCartStore.getState()
    expect(items.length).toBe(0)
  })

  it('should update item quantity', () => {
    const { addItem, updateQuantity } = useCartStore.getState()
    addItem(testProduct)
    updateQuantity(testProduct.id, 5)
    const { items } = useCartStore.getState()
    expect(items[0].quantity).toBe(5)
  })

  it('should remove item when quantity becomes zero', () => {
    const { addItem, updateQuantity } = useCartStore.getState()
    addItem(testProduct)
    updateQuantity(testProduct.id, 0)
    const { items } = useCartStore.getState()
    expect(items.length).toBe(0)
  })

  it('should calculate total correctly', () => {
    const { addItem, getTotal } = useCartStore.getState()
    addItem(testProduct)
    addItem({ ...testProduct, id: 'test-2', price: 50.0 })
    expect(getTotal()).toBeCloseTo(149.99, 2)
  })

  it('should clear cart', () => {
    const { addItem, clearCart } = useCartStore.getState()
    addItem(testProduct)
    clearCart()
    const { items } = useCartStore.getState()
    expect(items.length).toBe(0)
  })
})