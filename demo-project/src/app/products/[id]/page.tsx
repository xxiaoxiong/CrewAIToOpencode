'use client'

import { useParams } from 'next/navigation'
import Image from 'next/image'
import { getProductById } from '@/data/products'
import { useCartStore } from '@/context/CartStore'
import Link from 'next/link'

export default function ProductDetailPage() {
  const params = useParams()
  const product = getProductById(params.id as string)
  const addItem = useCartStore((state) => state.addItem)

  if (!product) {
    return (
      <div className="text-center py-16">
        <h1 className="text-2xl font-bold mb-4">Product Not Found</h1>
        <Link href="/products" className="text-primary hover:underline">
          Back to Products
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <Link href="/products" className="text-primary hover:underline mb-4 inline-block">
        ← Back to Products
      </Link>

      <div className="grid md:grid-cols-2 gap-8">
        <div className="relative h-96">
          <Image
            src={product.image}
            alt={product.name}
            fill
            className="object-cover rounded-lg"
          />
        </div>

        <div>
          <span className="text-sm text-gray-500">{product.category}</span>
          <h1 className="text-3xl font-bold mb-4">{product.name}</h1>
          <p className="text-2xl font-bold text-primary mb-4">
            ${product.price.toFixed(2)}
          </p>
          <p className="text-gray-600 mb-6">{product.description}</p>

          <div className="flex items-center gap-4 mb-6">
            <div className="flex items-center">
              <span className="text-gray-600 mr-2">Rating:</span>
              <span className="text-yellow-500">
                {'★'.repeat(Math.floor(product.rating))}
                {'☆'.repeat(5 - Math.floor(product.rating))}
              </span>
              <span className="text-gray-500 ml-1">({product.rating})</span>
            </div>
          </div>

          <div className="flex items-center gap-4 mb-6">
            <span className="text-gray-600">Stock: {product.stock} available</span>
          </div>

          <button
            onClick={() => addItem(product)}
            className="btn-primary w-full py-3 text-lg"
          >
            Add to Cart
          </button>
        </div>
      </div>
    </div>
  )
}