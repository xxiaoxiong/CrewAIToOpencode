'use client'

import Image from 'next/image'
import Link from 'next/link'
import { useCartStore } from '@/context/CartStore'
import { useAuthStore } from '@/context/AuthStore'

export default function CartPage() {
  const { items, updateQuantity, removeItem, getTotal, clearCart } = useCartStore()
  const { user } = useAuthStore()
  const total = getTotal()

  if (items.length === 0) {
    return (
      <div className="text-center py-16">
        <h1 className="text-2xl font-bold mb-4">Your cart is empty</h1>
        <Link href="/products" className="btn-primary">
          Continue Shopping
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">Shopping Cart</h1>

      <div className="bg-white rounded-lg shadow-md p-6 mb-8">
        {items.map((item) => (
          <div
            key={item.product.id}
            className="flex items-center gap-4 py-4 border-b last:border-b-0"
          >
            <div className="relative w-20 h-20 flex-shrink-0">
              <Image
                src={item.product.image}
                alt={item.product.name}
                fill
                className="object-cover rounded"
              />
            </div>

            <div className="flex-1">
              <h3 className="font-semibold">{item.product.name}</h3>
              <p className="text-gray-500">${item.product.price.toFixed(2)}</p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() =>
                  updateQuantity(item.product.id, item.quantity - 1)
                }
                className="w-8 h-8 border rounded hover:bg-gray-100"
              >
                -
              </button>
              <span className="w-8 text-center">{item.quantity}</span>
              <button
                onClick={() =>
                  updateQuantity(item.product.id, item.quantity + 1)
                }
                className="w-8 h-8 border rounded hover:bg-gray-100"
              >
                +
              </button>
            </div>

            <div className="text-right">
              <p className="font-semibold">
                ${(item.product.price * item.quantity).toFixed(2)}
              </p>
              <button
                onClick={() => removeItem(item.product.id)}
                className="text-red-500 text-sm hover:underline"
              >
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex justify-between mb-4">
          <span className="text-lg">Subtotal</span>
          <span className="text-lg font-semibold">${total.toFixed(2)}</span>
        </div>
        <div className="flex justify-between mb-4">
          <span className="text-lg">Shipping</span>
          <span className="text-lg font-semibold">
            {total >= 50 ? 'Free' : '$5.00'}
          </span>
        </div>
        <div className="flex justify-between mb-6 text-xl font-bold">
          <span>Total</span>
          <span>${(total + (total >= 50 ? 0 : 5)).toFixed(2)}</span>
        </div>

        <div className="flex gap-4">
          <button onClick={clearCart} className="btn-secondary flex-1">
            Clear Cart
          </button>
          {user ? (
            <Link href="/checkout" className="btn-primary flex-1 text-center">
              Proceed to Checkout
            </Link>
          ) : (
            <Link href="/login" className="btn-primary flex-1 text-center">
              Login to Checkout
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}