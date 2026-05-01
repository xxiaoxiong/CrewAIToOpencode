'use client'

import Link from 'next/link'
import { useCartStore } from '@/context/CartStore'
import { useAuthStore } from '@/context/AuthStore'

export default function Navbar() {
  const { items } = useCartStore()
  const { user, logout } = useAuthStore()
  const cartCount = items.reduce((sum, item) => sum + item.quantity, 0)

  return (
    <nav className="bg-white shadow-md sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <Link href="/" className="text-2xl font-bold text-primary">
            ShopStore
          </Link>

          <div className="flex items-center gap-6">
            <Link href="/" className="hover:text-primary">
              Home
            </Link>
            <Link href="/products" className="hover:text-primary">
              Products
            </Link>

            <Link href="/cart" className="relative hover:text-primary">
              <span>Cart</span>
              {cartCount > 0 && (
                <span className="absolute -top-2 -right-3 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                  {cartCount}
                </span>
              )}
            </Link>

            {user ? (
              <div className="flex items-center gap-4">
                <Link href="/orders" className="hover:text-primary">
                  Orders
                </Link>
                {user.role === 'admin' && (
                  <Link href="/admin" className="hover:text-primary">
                    Admin
                  </Link>
                )}
                <button
                  onClick={logout}
                  className="text-red-500 hover:text-red-700"
                >
                  Logout
                </button>
              </div>
            ) : (
              <Link
                href="/login"
                className="bg-primary text-white px-4 py-2 rounded hover:bg-blue-700"
              >
                Login
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}