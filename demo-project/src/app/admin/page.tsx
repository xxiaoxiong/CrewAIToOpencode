'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/context/AuthStore'
import { products as initialProducts, Product } from '@/data/products'

interface Order {
  id: string
  date: string
  total: number
  status: string
  shippingInfo: { address: string; city: string; zip: string; country: string }
}

export default function AdminPage() {
  const router = useRouter()
  const { user } = useAuthStore()
  const [activeTab, setActiveTab] = useState<'products' | 'orders'>('products')
  const [products, setProducts] = useState<Product[]>(initialProducts)
  const [orders, setOrders] = useState<Order[]>([])
  const [editingProduct, setEditingProduct] = useState<Product | null>(null)

  useEffect(() => {
    if (!user || user.role !== 'admin') {
      router.push('/')
      return
    }
    setOrders(JSON.parse(localStorage.getItem('orders') || '[]'))
  }, [user, router])

  if (!user || user.role !== 'admin') return null

  const handleDeleteProduct = (id: string) => {
    if (confirm('Are you sure you want to delete this product?')) {
      setProducts(products.filter((p) => p.id !== id))
    }
  }

  const handleUpdateStatus = (orderId: string, status: string) => {
    const updatedOrders = orders.map((o) =>
      o.id === orderId ? { ...o, status } : o
    )
    setOrders(updatedOrders)
    localStorage.setItem('orders', JSON.stringify(updatedOrders))
  }

  const handleSaveProduct = () => {
    if (!editingProduct) return

    const existingIndex = products.findIndex((p) => p.id === editingProduct.id)
    if (existingIndex >= 0) {
      const updated = [...products]
      updated[existingIndex] = editingProduct
      setProducts(updated)
    } else {
      setProducts([...products, { ...editingProduct, id: Date.now().toString() }])
    }
    setEditingProduct(null)
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Admin Dashboard</h1>

      <div className="flex gap-4 mb-8">
        <button
          onClick={() => setActiveTab('products')}
          className={`px-6 py-3 rounded ${
            activeTab === 'products'
              ? 'bg-primary text-white'
              : 'bg-gray-200 text-gray-700'
          }`}
        >
          Products
        </button>
        <button
          onClick={() => setActiveTab('orders')}
          className={`px-6 py-3 rounded ${
            activeTab === 'orders'
              ? 'bg-primary text-white'
              : 'bg-gray-200 text-gray-700'
          }`}
        >
          Orders ({orders.length})
        </button>
      </div>

      {activeTab === 'products' && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-semibold">Product Management</h2>
            <button
              onClick={() =>
                setEditingProduct({
                  id: '',
                  name: '',
                  description: '',
                  price: 0,
                  category: '',
                  image: '',
                  stock: 0,
                  rating: 0,
                })
              }
              className="btn-primary"
            >
              Add Product
            </button>
          </div>

          {editingProduct && (
            <div className="bg-gray-50 p-4 rounded mb-6">
              <h3 className="font-semibold mb-4">
                {editingProduct.id ? 'Edit Product' : 'New Product'}
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <input
                  type="text"
                  placeholder="Name"
                  value={editingProduct.name}
                  onChange={(e) =>
                    setEditingProduct({ ...editingProduct, name: e.target.value })
                  }
                  className="input-field"
                />
                <input
                  type="number"
                  placeholder="Price"
                  value={editingProduct.price}
                  onChange={(e) =>
                    setEditingProduct({
                      ...editingProduct,
                      price: parseFloat(e.target.value),
                    })
                  }
                  className="input-field"
                />
                <input
                  type="text"
                  placeholder="Category"
                  value={editingProduct.category}
                  onChange={(e) =>
                    setEditingProduct({
                      ...editingProduct,
                      category: e.target.value,
                    })
                  }
                  className="input-field"
                />
                <input
                  type="number"
                  placeholder="Stock"
                  value={editingProduct.stock}
                  onChange={(e) =>
                    setEditingProduct({
                      ...editingProduct,
                      stock: parseInt(e.target.value),
                    })
                  }
                  className="input-field"
                />
                <input
                  type="text"
                  placeholder="Image URL"
                  value={editingProduct.image}
                  onChange={(e) =>
                    setEditingProduct({ ...editingProduct, image: e.target.value })
                  }
                  className="input-field col-span-2"
                />
                <textarea
                  placeholder="Description"
                  value={editingProduct.description}
                  onChange={(e) =>
                    setEditingProduct({
                      ...editingProduct,
                      description: e.target.value,
                    })
                  }
                  className="input-field col-span-2"
                />
              </div>
              <div className="flex gap-2 mt-4">
                <button onClick={handleSaveProduct} className="btn-primary">
                  Save
                </button>
                <button
                  onClick={() => setEditingProduct(null)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-3">Name</th>
                <th className="text-left py-3">Category</th>
                <th className="text-right py-3">Price</th>
                <th className="text-right py-3">Stock</th>
                <th className="text-right py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {products.map((product) => (
                <tr key={product.id} className="border-b">
                  <td className="py-3">{product.name}</td>
                  <td className="py-3">{product.category}</td>
                  <td className="text-right py-3">${product.price.toFixed(2)}</td>
                  <td className="text-right py-3">{product.stock}</td>
                  <td className="text-right py-3">
                    <button
                      onClick={() => setEditingProduct(product)}
                      className="text-primary hover:underline mr-4"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDeleteProduct(product.id)}
                      className="text-red-500 hover:underline"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'orders' && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-6">Order Management</h2>

          {orders.length === 0 ? (
            <p className="text-gray-500">No orders yet</p>
          ) : (
            <div className="space-y-4">
              {orders.map((order) => (
                <div key={order.id} className="border rounded p-4">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h3 className="font-semibold">{order.id}</h3>
                      <p className="text-sm text-gray-500">
                        {new Date(order.date).toLocaleDateString()}
                      </p>
                      <p className="text-sm">
                        {order.shippingInfo?.address}, {order.shippingInfo?.city},{' '}
                        {order.shippingInfo?.zip}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold">${order.total.toFixed(2)}</p>
                      <select
                        value={order.status}
                        onChange={(e) =>
                          handleUpdateStatus(order.id, e.target.value)
                        }
                        className="mt-2 text-sm border rounded px-2 py-1"
                      >
                        <option>Processing</option>
                        <option>Shipped</option>
                        <option>Delivered</option>
                      </select>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}