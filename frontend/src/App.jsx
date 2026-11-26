import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { LoadingState } from './components/ui'
import { useI18n } from './lib/i18nCore'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Bookings = lazy(() => import('./pages/Bookings'))
const Chats = lazy(() => import('./pages/Chats'))
const Transactions = lazy(() => import('./pages/Transactions'))

export default function App() {
  const { t } = useI18n()

  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingState label={t('common.loading')} />}>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/bookings" element={<Bookings />} />
            <Route path="/chats" element={<Chats />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
