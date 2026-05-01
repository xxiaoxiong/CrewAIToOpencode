'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuthStore } from '@/context/AuthStore'

export default function LoginPage() {
  const router = useRouter()
  const { login, register } = useAuthStore()
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (isRegister) {
      const success = register(email, password, name)
      if (success) {
        router.push('/')
      } else {
        setError('Email already registered')
      }
    } else {
      const success = login(email, password)
      if (success) {
        router.push('/')
      } else {
        setError('Invalid email or password')
      }
    }
  }

  return (
    <div className="max-w-md mx-auto mt-16">
      <div className="bg-white rounded-lg shadow-md p-8">
        <h1 className="text-2xl font-bold text-center mb-6">
          {isRegister ? 'Register' : 'Login'}
        </h1>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {isRegister && (
            <div className="mb-4">
              <label className="block text-gray-700 mb-2">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input-field"
                required
              />
            </div>
          )}

          <div className="mb-4">
            <label className="block text-gray-700 mb-2">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input-field"
              required
            />
          </div>

          <div className="mb-6">
            <label className="block text-gray-700 mb-2">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-field"
              required
            />
          </div>

          <button type="submit" className="btn-primary w-full">
            {isRegister ? 'Register' : 'Login'}
          </button>
        </form>

        <p className="text-center mt-4 text-gray-600">
          {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            onClick={() => {
              setIsRegister(!isRegister)
              setError('')
            }}
            className="text-primary hover:underline"
          >
            {isRegister ? 'Login' : 'Register'}
          </button>
        </p>

        <div className="mt-6 p-4 bg-gray-100 rounded text-sm">
          <p className="font-semibold mb-2">Test Accounts:</p>
          <p>Admin: admin@shop.com / admin123</p>
          <p>User: user@shop.com / user123</p>
        </div>
      </div>
    </div>
  )
}