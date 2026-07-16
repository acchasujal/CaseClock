import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ShieldCheck, RotateCcw } from 'lucide-react'
import { Button } from '@/components/Button'
import { Input } from '@/components/Input'
import { apiFetch } from '@/lib/apiClient'
import type { CopilotQueryResponse, UserRole } from '@shared/contracts/api'

interface CaseCopilotPanelProps {
  caseId: string
  role: UserRole
}

export function CaseCopilotPanel({ caseId, role }: CaseCopilotPanelProps) {
  const [question, setQuestion] = useState('')

  const query = useMutation<CopilotQueryResponse, Error, string>({
    mutationFn: (value) =>
      apiFetch<CopilotQueryResponse>('/copilot/query', {
        method: 'POST',
        body: JSON.stringify({ query: value, case_id: caseId, user_role: role }),
      }),
  })

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (question.trim()) {
      query.mutate(question.trim())
      // Clear the input on submit so the user can type a follow-up
      setQuestion('')
    }
  }

  const handleClear = () => {
    query.reset()
    setQuestion('')
  }

  return (
    <section aria-labelledby="case-copilot-heading" className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4">
      <div className="flex items-start gap-3">
        <ShieldCheck className="mt-0.5 h-5 w-5 text-status-info" aria-hidden="true" />
        <div>
          <h2 id="case-copilot-heading" className="text-h2 font-semibold text-neutral-900">Case Copilot</h2>
          <p className="mt-1 text-small text-neutral-600">
            Evidence-linked assistance for the current case record.
          </p>
        </div>
      </div>

      <form className="mt-4 flex flex-col gap-2 sm:flex-row" onSubmit={submit} aria-label="Case Copilot query form">
        <div className="flex-1">
          <Input
            label="Question about this case"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="What is blocking this investigation?"
          />
        </div>
        <div className="flex gap-2 self-end">
          <Button
            type="submit"
            isLoading={query.isPending}
            disabled={!question.trim()}
            aria-label="Submit question to Copilot"
          >
            Ask
          </Button>
          {(query.data ?? query.isError) && (
            <Button
              type="button"
              variant="ghost"
              onClick={handleClear}
              aria-label="Clear Copilot response and start over"
              title="Clear response"
            >
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
            </Button>
          )}
        </div>
      </form>

      {/* Response area with aria-live for screen readers */}
      <div className="mt-4" role="log" aria-live="polite" aria-label="Copilot response" aria-atomic="false">
        {query.isPending && (
          <p className="text-small text-neutral-600" aria-live="polite">Running query...</p>
        )}

        {query.isError && (
          <div className="rounded-radius-sm border border-status-danger/20 bg-status-danger/5 p-3">
            <p className="text-small text-status-danger">{query.error.message}</p>
          </div>
        )}

        {query.data?.refused && (
          <div
            className="rounded-radius-sm border border-neutral-200 bg-neutral-100 p-3"
            role="status"
          >
            <div className="flex items-center gap-2 text-small font-semibold text-neutral-800">
              <ShieldCheck className="h-4 w-4 text-status-info" aria-hidden="true" />
              Unable to answer safely
            </div>
            <p className="mt-2 text-small text-neutral-700">{query.data.refusal_reason}</p>
            <p className="mt-1 text-caption text-neutral-500">
              Confidence gate: {Math.round((query.data.confidence ?? 0) * 100)}%
            </p>
          </div>
        )}

        {query.data && !query.data.refused && (
          <div className="rounded-radius-sm border border-neutral-200 bg-neutral-50 p-3">
            <p className="text-small text-neutral-800">{query.data.answer}</p>
            <p className="mt-1 text-caption text-neutral-500">
              Confidence: {Math.round((query.data.confidence ?? 0) * 100)}%
            </p>
            {query.data.reasoning_path && query.data.reasoning_path.length > 0 && (
              <details className="mt-3 text-small text-neutral-700">
                <summary className="cursor-pointer font-semibold focus-visible:ring-1 focus-visible:ring-status-info rounded-radius-sm">
                  Citations and reasoning path
                </summary>
                <ul className="mt-2 list-disc space-y-1 pl-5" aria-label="Reasoning path">
                  {query.data.reasoning_path.map((path) => (
                    <li key={path}>{path}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
