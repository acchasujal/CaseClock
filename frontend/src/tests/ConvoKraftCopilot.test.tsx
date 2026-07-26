import { act, cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CONVOKRAFT_CONFIG } from '@/config/copilot'
import { ConvoKraftCopilot, resetConvoKraftSdkForTests } from '@/components/ConvoKraftCopilot'

const sdkSelector = `script[src="${CONVOKRAFT_CONFIG.sdkUrl}"]`

function finishSdkLoad() {
  const script = document.querySelector<HTMLScriptElement>(sdkSelector)
  expect(script).not.toBeNull()
  act(() => script?.dispatchEvent(new Event('load')))
}

beforeEach(() => {
  resetConvoKraftSdkForTests()
  document.querySelectorAll(sdkSelector).forEach((script) => script.remove())
})

afterEach(() => cleanup())

describe('ConvoKraftCopilot', () => {
  it('loads the official SDK once and renders the configured bot element', () => {
    const { unmount } = render(<ConvoKraftCopilot caseLabel="FIR/MAN/0003" />)
    finishSdkLoad()

    const bot = document.querySelector('convokraft-chat-bot')
    expect(document.querySelectorAll(sdkSelector)).toHaveLength(1)
    expect(bot).toHaveAttribute('bot-name', 'voiceassistant')
    expect(bot).toHaveAttribute('project-id', '51441000000017001')
    expect(bot).toHaveAttribute('org-id', '60077090566')
    expect(screen.getByText(/FIR\/MAN\/0003/)).toBeInTheDocument()

    unmount()
    render(<ConvoKraftCopilot />)
    expect(document.querySelectorAll(sdkSelector)).toHaveLength(1)
  })

  it('isolates SDK failure without crashing the surrounding page', async () => {
    render(
      <main>
        <ConvoKraftCopilot />
        <p>Worklist remains available</p>
      </main>,
    )
    const script = document.querySelector<HTMLScriptElement>(sdkSelector)
    expect(script).not.toBeNull()
    act(() => script?.dispatchEvent(new Event('error')))

    await waitFor(() => expect(screen.getByText('CaseClock Copilot is temporarily unavailable.')).toBeInTheDocument())
    expect(screen.getByText('Worklist remains available')).toBeInTheDocument()
    expect(screen.queryByText(/QuickML|graph engine/i)).not.toBeInTheDocument()
  })

  it('does not issue a QuickML request in ConvoKraft mode', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    render(<ConvoKraftCopilot />)
    finishSdkLoad()

    await act(async () => Promise.resolve())
    expect(fetchSpy).not.toHaveBeenCalledWith(expect.stringContaining('/api/chat'), expect.anything())
    fetchSpy.mockRestore()
  })
})
