import { useEffect, useState } from 'react'
import { ShieldCheck } from 'lucide-react'
import { CONVOKRAFT_CONFIG } from '@/config/copilot'

let sdkLoad: Promise<void> | null = null

function loadConvoKraftSdk(): Promise<void> {
  if (typeof document === 'undefined') return Promise.resolve()
  if (customElements.get('convokraft-chat-bot')) return Promise.resolve()
  if (sdkLoad) return sdkLoad

  sdkLoad = new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${CONVOKRAFT_CONFIG.sdkUrl}"]`,
    )
    const script = existing ?? document.createElement('script')

    const finish = () => resolve()
    const fail = () => reject(new Error('ConvoKraft SDK unavailable'))
    script.addEventListener('load', finish, { once: true })
    script.addEventListener('error', fail, { once: true })

    if (!existing) {
      script.src = CONVOKRAFT_CONFIG.sdkUrl
      script.async = true
      document.head.appendChild(script)
    }
  })

  return sdkLoad
}

interface ConvoKraftCopilotProps {
  caseLabel?: string
  className?: string
}

export function ConvoKraftCopilot({ caseLabel, className = '' }: ConvoKraftCopilotProps) {
  const [sdkError, setSdkError] = useState(false)

  useEffect(() => {
    let active = true
    loadConvoKraftSdk().catch(() => {
      if (active) setSdkError(true)
    })
    return () => {
      active = false
    }
  }, [])

  return (
    <section
      aria-labelledby="convokraft-copilot-heading"
      className={`rounded-radius-md border border-neutral-200 bg-neutral-50 p-4 ${className}`}
    >
      <div className="flex items-start gap-3">
        <ShieldCheck className="mt-0.5 h-5 w-5 text-status-info" aria-hidden="true" />
        <div>
          <h2 id="convokraft-copilot-heading" className="text-h2 font-semibold text-neutral-900">
            CaseClock Copilot
          </h2>
          <p className="mt-1 text-small text-neutral-600">
            Official ConvoKraft assistant for CaseClock investigation workflows.
            {caseLabel ? ` Current case: ${caseLabel}.` : ''}
          </p>
        </div>
      </div>

      <div className="mt-4 min-h-[450px] w-full overflow-hidden rounded-radius-md border border-neutral-200 bg-white sm:min-h-[500px] lg:h-[540px]">
        {sdkError ? (
          <div className="flex h-full min-h-[450px] items-center justify-center p-6 text-center text-small text-neutral-600">
            CaseClock Copilot is temporarily unavailable.
          </div>
        ) : (
          <convokraft-chat-bot
            bot-name={CONVOKRAFT_CONFIG.botName}
            project-id={CONVOKRAFT_CONFIG.projectId}
            org-id={CONVOKRAFT_CONFIG.orgId}
            className="block h-full w-full"
          />
        )}
      </div>
      <p className="mt-2 text-caption text-neutral-500">
        Case facts, clocks, dependencies, and graph data remain authoritative in CaseClock.
      </p>
    </section>
  )
}

export function resetConvoKraftSdkForTests() {
  sdkLoad = null
}
