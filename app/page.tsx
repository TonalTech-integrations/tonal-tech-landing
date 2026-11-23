import { LeadProvider } from '@/components/lead-panel'
import { SiteHeader } from '@/components/site-header'
import { TonalHero } from '@/components/tonal-hero'
import { ServiceGrid } from '@/components/service-grid'
import { AcademySection } from '@/components/academy-section'
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
          <AcademySection />
          <ProofSection />
        </main>
        <SiteFooter />
      </div>
    </LeadProvider>
  )
}
