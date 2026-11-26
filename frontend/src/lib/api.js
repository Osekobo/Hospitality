import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 15000,
})

export const getStats = () => api.get('/admin/stats').then((r) => r.data)
export const getBookings = () => api.get('/admin/bookings').then((r) => r.data)
export const getChats = () => api.get('/admin/chats').then((r) => r.data)
export const getUsers = () => api.get('/admin/users').then((r) => r.data)
export const getProperties = () => api.get('/admin/properties').then((r) => r.data)
export const getTransactions = () => api.get('/mpesa/transactions').then((r) => r.data)
export const sendChat = (payload) => api.post('/chat/message', payload).then((r) => r.data)

export default api
