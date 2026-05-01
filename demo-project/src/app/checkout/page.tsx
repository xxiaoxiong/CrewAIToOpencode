'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useCartStore } from '@/context/CartStore'
import { useAuthStore } from '@/context/AuthStore'

export default function CheckoutPage() {
  const router = useRouter()
  const { items, getTotal, clearCart } = useCartStore()
  const { user } = useAuthStore()
  const [isProcessing, setIsProcessing] = useState(false)
  const [orderPlaced, setOrderPlaced] = useState(false)

  const [shippingInfo, setShippingInfo] = useState({
    address: '',
    city: '',
    zip: '',
    country: 'United States',
  })

  const total = getTotal()
  const shipping = total >= 50 ? 0 : 5

  if (!user) {
    return (
      <div className="text-center py-16">
        <h1 className="text-2xl font-bold mb-4">Please login to checkout</h1>
        <Link href="/login" className="btn-primary">
          Login
        </Link>
      </div>
    )
  }

  if (items.length === 0 && !orderPlaced) {
    return (
      <div className="text-center py-16">
        <h1 className="text-2xl font-bold mb-4">Your cart is empty</h1>
        <Link href="/products" className="btn-primary">
          Continue Shopping
        </Link>
      </div>
    )
  }

  if (orderPlaced) {
    return (
      <div className="text-center py-16">
        <div className="text-6xl mb-4">✅</div>
        <h1 className="text-3xl font-bold mb-4">Order Placed Successfully!</h1>
        <p className="text-gray-600 mb-8">
          Thank you for your order. You will receive a confirmation email soon.
        </p>
        <Link href="/orders" className="btn-primary">
          View Orders
        </Link>
      </div>
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsProcessing(true)

    await new Promise((resolve) => setTimeout(resolve, 2000))

    const orderId = 'ORD-' + Date.now()
    const orders = JSON.parse(localStorage.getItem('orders') || '[]')
    orders.unshift({
      id: orderId,
      date: new Date().toISOString(),
      items: items,
      total: total + shipping,
      status: 'Processing',
      shippingInfo,
    })
    localStorage.setItem('orders', JSON.stringify(orders))

    clearCart()
    setOrderPlaced(true)
    setIsProcessing(false)
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">Checkout</h1>

      <div className="grid md:grid-cols-2 gap-8">
        <div>
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">Shipping Information</h2>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label className="block text-gray-700 mb-2">Address</label>
                <input
                  type="text"
                  value={shippingInfo.address}
                  onChange={(e) =>
                    setShippingInfo({ ...shippingInfo, address: e.target.value })
                  }
                  className="input-field"
                  required
                />
              </div>

              <div className="mb-4">
                <label className="block text-gray-700 mb-2">City</label>
                <input
                  type="text"
                  value={shippingInfo.city}
                  onChange={(e) =>
                    setShippingInfo({ ...shippingInfo, city: e.target.value })
                  }
                  className="input-field"
                  required
                />
              </div>

              <div className="mb-4">
                <label className="block text-gray-700 mb-2">ZIP Code</label>
                <input
                  type="text"
                  value={shippingInfo.zip}
                  onChange={(e) =>
                    setShippingInfo({ ...shippingInfo, zip: e.target.value })
                  }
                  className="input-field"
                  required
                />
              </div>

              <div className="mb-6">
                <label className="block text-gray-700 mb-2">Country</label>
                <select
                  value={shippingInfo.country}
                  onChange={(e) =>
                    setShippingInfo({ ...shippingInfo, country: e.target.value })
                  }
                  className="input-field"
                >
                  <option>United States</option>
                  <option>Canada</option>
                  <option>United Kingdom</option>
                  <option>Australia</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={isProcessing}
                className="btn-primary w-full py-3"
              >
                {isProcessing ? 'Processing...' : `Place Order - $${(total + shipping).toFixed(2)}`}
              </button>
            </form>
          </div>
        </div>

        <div>
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Order Summary</h2>
            {items.map((item) => (
              <div key={item.product.id} className="flex justify-between py-2">
                <span>
                  {item.product.name} x {item.quantity}
                </span>
                <span>${(item.product.price * item.quantity).toFixed(2)}</span>
              </div>
            ))}
            <hr className="my-4" />
            <div className="flex justify-between">
              <span>Subtotal</span>
              <span>${total.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span>Shipping</span>
              <span>{shipping === 0 ? 'Free' : `$${shipping.toFixed(2)}`}</span>
            </div>
            <hr className="my-4" />
            <div className="flex justify-between font-bold text-lg">
              <span>Total</span>
              <span>${(total + shipping).toFixed(2)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}