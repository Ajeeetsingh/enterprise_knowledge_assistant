import {
  FeaturesSection,
  FinalCtaSection,
  HeroSection,
  LandingFooter,
  LandingNavbar,
  ProductProofSection,
} from '@/features/landing'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-canvas text-foreground">
      <LandingNavbar />
      <main>
        <HeroSection />
        <FeaturesSection />
        <ProductProofSection />
        <FinalCtaSection />
      </main>
      <LandingFooter />
    </div>
  )
}
