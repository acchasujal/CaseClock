import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ShieldCheck } from 'lucide-react'
import { Button } from '@/components/Button'
import { Input } from '@/components/Input'
import type { CopilotQueryResponse, UserRole } from '@shared/contracts/api'

interface CaseCopilotPanelProps {
  caseId: string
  role: UserRole
}

export function CaseCopilotPanel({ caseId, role }: CaseCopilotPanelProps) {
  const [question, setQuestion] = useState('')
  const query = useMutation<CopilotQueryResponse, Error, string>({
    mutationFn: async (value) => {
      const response = await fetch('/copilot/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: value, case_id: caseId, user_role: role }),
      })
      if (!response.ok) throw new Error(`Unable to run query: ${response.statusText}`)
      return response.json()
    },
  })

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (question.trim()) query.mutate(question.trim())
  }

  return (
    <section aria-labelledby="case-copilot-heading" className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4">
      <div className="flex items-start gap-3">
        <ShieldCheck className="mt-0.5 h-5 w-5 text-status-info" aria-hidden="true" />
        <div>
          <h2 id="case-copilot-heading" className="text-h2 font-semibold text-neutral-900">Case Copilot</h2>
          <p className="mt-1 text-small text-neutral-600">Evidence-linked assistance for the current case record.</p>
        </div>
      </div>
      <form className="mt-4 flex flex-col gap-2 sm:flex-row" onSubmit={submit}>
        <Input label="Question about this case" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="What is blocking this investigation?" />
        <Button type="submit" isLoading={query.isPending} className="self-end" disabled={!question.trim()}>Ask</Button>
      </form>
      <div className="mt-4" role="log" aria-live="polite" aria-label="Copilot response">
        {query.isPending && <p className="text-small text-neutral-600">Running query...</p>}
        {query.isError && <p className="text-small text-status-danger">{query.error.message}</p>}
        {query.data?.refused && (
          <div className="rounded-radius-sm border border-neutral-200 bg-neutral-100 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-neutral-800"><ShieldCheck className="h-4 w-4 text-status-info" aria-hidden="true" />Unable to answer safely</div>
            <p className="mt-2 text-small text-neutral-700">{query.data.refusal_reason}</p>
            <p className="mt-2 text-caption text-neutral-600">Confidence: {query.data.confidence}</p>
          </div>
        )}
        {query.data && !query.data.refused && (
          <div className="rounded-radius-sm border border-neutral-200 bg-neutral-50 p-3">
            <p className="text-small text-neutral-800">{query.data.answer}</p>
            <p className="mt-2 text-caption text-neutral-600">Confidence: {query.data.confidence}</p>
            {query.data.reasoning_path && query.data.reasoning_path.length > 0 && (
              <details className="mt-3 text-small text-neutral-700">
                <summary className="cursor-pointer font-semibold">Citations and path</summary>
                <ul className="mt-2 list-disc space-y-1 pl-5">{query.data.reasoning_path.map((path) => <li key={path}>{path}</li>)}</ul>
              </details>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
