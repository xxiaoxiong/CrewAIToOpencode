'use client'

import Image from 'next/image'
import Link from 'next/link'
import { Product } from '@/data/products'
import { useCartStore } from '@/context/CartStore'

interface ProductCardProps {
  product: Product
}

export default function ProductCard({ product }: ProductCardProps) {
  const addItem = useCartStore((state) => state.addItem)

  const handleAddToCart = () => {
    addItem(product)
  }

  return (
    <div className="product-card bg-white">
      <div className="relative h-48 mb-4">
        <Image
          src={product.image}
          alt={product.name}
          fill
          className="object-cover rounded"
        />
      </div>
      <h3 className="text-lg font-semibold mb-2">{product.name}</h3>
      <p className="text-gray-600 text-sm mb-2 line-clamp-2">
        {product.description}
      </p>
      <div className="flex items-center justify-between mb-3">
        <span className="text-2xl font-bold text-primary">
          ${product.price.toFixed(2)}
        </span>
        <span className="text-sm text-gray-500">
          Stock: {product.stock}
        </span>
      </div>
      <div className="flex gap-2">
        <Link
          href={`/products/${product.id}`}
          className="btn-secondary flex-1 text-center"
        >
          View
        </Link>
        <button onClick={handleAddToCart} className="btn-primary flex-1">
          Add to Cart
        </button>
      </div>
    </div>
  )
}