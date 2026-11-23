import { Suspense } from 'react'
import { SuccessPage } from '@/components/academy/success-page'

export default function Page() {
  return (
    <Suspense>
      <SuccessPage />
    </Suspense>
  )
}
