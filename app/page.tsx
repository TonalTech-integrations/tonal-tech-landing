import { LeadProvider } from '@/components/lead-panel'
import { SiteHeader } from '@/components/site-header'
import { TonalHero } from '@/components/tonal-hero'
import { ServiceGrid } from '@/components/service-grid'
import { AcademyBanner } from '@/components/academy-banner'
import { ProofSection } from '@/components/proof-section'
import { SiteFooter } from '@/components/site-footer'

export default function Page() {
  return (
    <LeadProvider>
      <div className="min-h-dvh bg-background text-foreground">
        <SiteHeader />
        <main>
          <TonalHero />
          <ServiceGrid />
          <AcademyBanner />
          <ProofSection />
        </main>
        <SiteFooter />
      </div>
    </LeadProvider>
  )
}
