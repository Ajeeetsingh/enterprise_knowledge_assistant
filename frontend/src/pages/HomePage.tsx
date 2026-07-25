import {
  AccessTrustSection,
  FeaturesSection,
  FinalCtaSection,
  HeroSection,
  HowItWorksSection,
  LandingFooter,
  LandingNavbar,
  ProductProofSection,
} from '@/features/landing'

export default function HomePage() {
  return (
    <div className="landing-page relative min-h-screen overflow-x-hidden text-foreground">
      {/* Decorative multi-layer aura — strictly behind content */}
      <div className="landing-aura" aria-hidden="true">
        <div className="landing-aura__blob landing-aura__blob--tr" />
        <div className="landing-aura__blob landing-aura__blob--cr" />
        <div className="landing-aura__blob landing-aura__blob--sky" />
        <div className="landing-aura__mist" />
      </div>

      <div className="relative z-[1]">
        <LandingNavbar />
        <main>
          <HeroSection />
          <FeaturesSection />
          <HowItWorksSection />
          <AccessTrustSection />
          <ProductProofSection />
          <FinalCtaSection />
        </main>
        <LandingFooter />
      </div>
    </div>
  )
}
