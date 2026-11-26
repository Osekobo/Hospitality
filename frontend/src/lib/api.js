import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 15000,
})

const adminToken = import.meta.env.VITE_ADMIN_API_TOKEN
if (adminToken) api.defaults.headers.common['X-Admin-Token'] = adminToken

export const getHealth = () => api.get('/health').then((response) => response.data)
export const getStats = () => api.get('/admin/stats').then((response) => response.data)
export const getBookings = () => api.get('/admin/bookings').then((response) => response.data)
export const getChats = () => api.get('/admin/chats').then((response) => response.data)
export const getTransactions = () => api.get('/mpesa/transactions').then((response) => response.data)
export const sendAdminReply = (userId, message) =>
  api.post(`/admin/chats/${userId}/reply`, { message }).then((response) => response.data)

export default api
