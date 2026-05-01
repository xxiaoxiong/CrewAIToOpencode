import './globals.css'
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import Navbar from '@/components/Navbar'
import CartProvider from '@/context/CartProvider'
import AuthProvider from '@/context/AuthProvider'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'E-Commerce Store',
  description: 'Full-featured e-commerce platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AuthProvider>
          <CartProvider>
            <Navbar />
            <main className="min-h-screen container mx-auto px-4 py-8">
              {children}
            </main>
            <footer className="bg-gray-800 text-white py-8 mt-16">
              <div className="container mx-auto px-4 text-center">
                <p>© 2026 E-Commerce Store. All rights reserved.</p>
              </div>
            </footer>
          </CartProvider>
        </AuthProvider>
      </body>
    </html>
  )
}