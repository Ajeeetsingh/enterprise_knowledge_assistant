import { cn } from '@/utils/cn'

import { useRevealOnScroll } from '../hooks/useRevealOnScroll'
import { ShieldCheckIcon } from './LandingIcons'
import { Reveal } from './ScrollReveal'

const ACCESS_POINTS = [
  {
    title: 'Role-aware retrieval',
    detail:
      'Document access follows assigned roles. The assistant only searches sources the signed-in user is authorised to see.',
  },
  {
    title: 'No cross-role leakage',
    detail:
      'Answers and citations stay within the caller’s permissions — private handbooks stay private.',
  },
  {
    title: 'Workspace controls',
    detail:
      'Admins manage users, roles, and document visibility from the authenticated workspace.',
  },
] as const

const ROLE_CHIPS = ['Employee', 'Finance', 'HR', 'Admin'] as const

export default function AccessTrustSection() {
  const { ref, isVisible } = useRevealOnScroll<HTMLElement>()

  return (
    <section
      ref={ref}
      className="relative scroll-mt-20 overflow-hidden border-y border-border-subtle bg-[color-mix(in_srgb,#F8FAFC_70%,#EEF2FF)] px-4 py-16 sm:px-6 sm:py-20 lg:px-8"
      id="security"
      aria-labelledby="landing-access-heading"
    >
      <div aria-hidden className="landing-section-glow landing-section-glow--alt" />

      <div className="relative mx-auto grid max-w-6xl gap-10 lg:grid-cols-2 lg:items-center lg:gap-16">
        <Reveal visible={isVisible} variant="slide-right">
          <p className="landing-eyebrow">Security & access</p>
          <h2
            id="landing-access-heading"
            className="landing-section-title font-display text-2xl tracking-tight sm:text-3xl"
          >
            Knowledge stays inside the right roles
          </h2>
          <p className="mt-4 text-base leading-relaxed text-[#475569]">
            Knowra is built around role-based document access — the same controls that protect
            your workspace also shape every retrieval.
          </p>

          <ul className="mt-8 space-y-5">
            {ACCESS_POINTS.map((item, index) => (
              <Reveal
                key={item.title}
                as="li"
                visible={isVisible}
                delayMs={120 + index * 80}
                className="flex gap-3"
              >
                <span className="landing-access-icon">
                  <ShieldCheckIcon className="size-4" />
                </span>
                <div>
                  <h3 className="text-sm font-semibold text-[#0F172A]">{item.title}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-[#475569]">{item.detail}</p>
                </div>
              </Reveal>
            ))}
          </ul>
        </Reveal>

        <Reveal visible={isVisible} variant="slide-left" delayMs={140}>
          <div
            className={cn(
              'relative overflow-hidden rounded-2xl border border-[rgba(99,102,241,0.15)]',
              'bg-white/80 p-6 shadow-[0_20px_40px_-15px_rgba(99,102,241,0.08)] backdrop-blur-md sm:p-8',
            )}
          >
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(99,102,241,0.08),transparent_60%)]"
            />
            <div className="relative">
              <p className="text-xs font-semibold uppercase tracking-wide text-[#64748B]">
                Permission-aware answering
              </p>
              <p className="mt-3 font-display text-xl font-bold tracking-tight text-[#0F172A]">
                Same question. Different sources — by role.
              </p>
              <p className="mt-2 text-sm leading-relaxed text-[#475569]">
                Retrieval respects the signed-in user&apos;s authorised documents before an answer
                is generated.
              </p>

              <div className="mt-6 flex flex-wrap gap-2">
                {ROLE_CHIPS.map((role) => (
                  <span
                    key={role}
                    className={cn(
                      'landing-role-chip',
                      role === 'Admin' && 'landing-role-chip--active',
                    )}
                  >
                    {role}
                  </span>
                ))}
              </div>

              <div className="mt-6 rounded-xl border border-[rgba(99,102,241,0.12)] bg-[#F8FAFC]/90 p-4">
                <p className="text-[11px] font-medium uppercase tracking-wide text-[#64748B]">
                  Example
                </p>
                <p className="mt-2 text-sm text-[#0F172A]">
                  “What is our leave policy?” → answers cite only handbooks shared with that role.
                </p>
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
