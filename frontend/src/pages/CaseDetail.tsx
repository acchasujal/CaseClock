import { Link, useSearchParams, useParams } from 'react-router-dom'
import { ArrowLeft, Clock3, ShieldAlert, Network, Layers } from 'lucide-react'
import { CaseCopilotPanel } from '@/components/CaseCopilotPanel'
import { ClockBadge } from '@/components/ClockBadge'
import { DependencyPanel } from '@/components/DependencyPanel'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'
import { RiskBadge } from '@/components/RiskBadge'
import { useAuth } from '@/contexts/AuthContext'
import { useCaseDetail } from '@/hooks/useCaseDetail'
import { useUpdateDependency } from '@/hooks/useUpdateDependency'
import { NetworkAnalysisPanel } from '@/components/NetworkAnalysisPanel'
import { SimilarityPanel } from '@/components/SimilarityPanel'

const tabs = [
  { id: 'clock', label: 'Clock', icon: Clock3 },
  { id: 'dependencies', label: 'Dependencies', icon: ShieldAlert },
  { id: 'network', label: 'Network Analysis', icon: Network },
  { id: 'similarity', label: 'Similar Cases', icon: Layers },
  { id: 'copilot', label: 'Copilot', icon: ShieldAlert },
] as const

export default function CaseDetail() {
  const { id } = useParams<{ id: string }>()
  const { role } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = tabs.some((tab) => tab.id === searchParams.get('tab')) ? searchParams.get('tab')! : 'clock'
  const caseQuery = useCaseDetail(id)
  const dependencyUpdate = useUpdateDependency()

  if (!id) return <ErrorState message="A case identifier is required to open this record." />
  if (caseQuery.isLoading) return <LoadingSkeleton layout="detail" />
  if (caseQuery.isError) return <ErrorState message={caseQuery.error.message} onRetry={() => void caseQuery.refetch()} />
  if (!caseQuery.data) return <EmptyState message="This case record is not available." />

  const caseDetail = caseQuery.data

  return (
    <div className="space-y-6">
      <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-2 text-small text-neutral-600">
        <Link to="/worklist" className="inline-flex min-h-11 items-center gap-2 rounded-radius-sm px-2 text-status-info hover:bg-neutral-100 focus-visible:ring-2 focus-visible:ring-status-info">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to Worklist
        </Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{caseDetail.fir_number}</span>
      </nav>
      <header className="border-b border-neutral-200 pb-6">
        <div className="flex flex-wrap items-center gap-2"><p className="text-caption font-semibold uppercase tracking-wide text-neutral-500">Case detail</p><span className="rounded-radius-sm border border-neutral-300 bg-neutral-100 px-2 py-1 text-caption font-semibold text-neutral-700">Synthetic Data</span></div>
        <div className="mt-2 flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <h1 className="text-h1 font-semibold text-neutral-900">{caseDetail.fir_number}</h1>
            <p className="mt-1 text-body text-neutral-600">{caseDetail.offence_category}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <RiskBadge level="UNDETERMINED" />
            <span className="text-caption text-neutral-600">Risk is not included in the case-detail response.</span>
          </div>
        </div>
        <dl className="mt-5 grid grid-cols-1 gap-4 border-t border-neutral-200 pt-4 sm:grid-cols-2 xl:grid-cols-5">
          <div><dt className="text-caption font-semibold uppercase tracking-wide text-neutral-500">Police station</dt><dd className="mt-1 text-small text-neutral-800">{caseDetail.station_name}</dd></div>
          <div><dt className="text-caption font-semibold uppercase tracking-wide text-neutral-500">Assigned officer</dt><dd className="mt-1 text-small text-neutral-600">Not included in record</dd></div>
          <div><dt className="text-caption font-semibold uppercase tracking-wide text-neutral-500">Current stage</dt><dd className="mt-1 text-small text-neutral-600">Not included in record</dd></div>
          <div><dt className="text-caption font-semibold uppercase tracking-wide text-neutral-500">Case ID</dt><dd className="mt-1 text-small text-neutral-800">{caseDetail.id}</dd></div>
          <div><dt className="text-caption font-semibold uppercase tracking-wide text-neutral-500">Clocks</dt><dd className="mt-1 flex flex-wrap gap-2">{caseDetail.clocks.length ? caseDetail.clocks.map((clock) => <ClockBadge key={clock.id} daysRemaining={clock.days_remaining} status={clock.status} />) : <span className="text-small text-neutral-600">No clock recorded</span>}</dd></div>
        </dl>
      </header>

      <nav className="overflow-x-auto border-b border-neutral-200" aria-label="Case detail tabs" role="tablist">
        <div className="flex min-w-max gap-5">
          {tabs.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return <button key={tab.id} type="button" role="tab" aria-selected={isActive} onClick={() => setSearchParams({ tab: tab.id })} className={`inline-flex items-center gap-2 border-b-2 px-1 py-3 text-small font-semibold transition-colors duration-fast ${isActive ? 'border-status-info text-status-info' : 'border-transparent text-neutral-600 hover:border-neutral-300 hover:text-neutral-900'}`}><Icon className="h-4 w-4" aria-hidden="true" />{tab.label}</button>
          })}
        </div>
      </nav>

      {activeTab === 'clock' && <div className="grid gap-6 xl:grid-cols-3"><div className="space-y-6 xl:col-span-2"><DependencyPanel dependencies={caseDetail.dependencies} isUpdating={dependencyUpdate.isPending} onResolve={(dependencyId) => dependencyUpdate.mutate({ id: dependencyId, status: 'resolved', caseId: id })} /></div><aside className="space-y-6"><section aria-labelledby="clock-heading" className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4"><h2 id="clock-heading" className="text-h2 font-semibold text-neutral-900">Statutory clocks</h2><div className="mt-4 space-y-3">{caseDetail.clocks.length ? caseDetail.clocks.map((clock) => <div key={clock.id} className="rounded-radius-sm border border-neutral-200 p-3"><p className="text-small font-semibold text-neutral-800">{clock.clock_type}</p><dl className="mt-2 space-y-1 text-small"><div className="flex justify-between gap-3"><dt className="text-neutral-600">Days remaining</dt><dd className="tabular-nums text-neutral-800">{clock.days_remaining}</dd></div><div className="flex justify-between gap-3"><dt className="text-neutral-600">Risk</dt><dd className="text-neutral-800">{clock.status}</dd></div><div><dt className="text-neutral-600">Statutory section</dt><dd className="mt-1 text-neutral-800">{clock.bnss_reference}</dd></div><div className="flex justify-between gap-3"><dt className="text-neutral-600">Status</dt><dd className="text-neutral-800">{clock.status}</dd></div></dl></div>) : <EmptyState message="No statutory clocks are recorded for this case." />}</div></section><CaseMetadata stationName={caseDetail.station_name} category={caseDetail.offence_category} /></aside></div>}
      {activeTab === 'dependencies' && <DependencyPanel dependencies={caseDetail.dependencies} isUpdating={dependencyUpdate.isPending} onResolve={(dependencyId) => dependencyUpdate.mutate({ id: dependencyId, status: 'resolved', caseId: id })} />}
      {activeTab === 'network' && <NetworkAnalysisPanel caseId={caseDetail.id} />}
      {activeTab === 'similarity' && <SimilarityPanel caseId={caseDetail.id} firNumber={caseDetail.fir_number} />}
      {activeTab === 'copilot' && <CaseCopilotPanel caseId={caseDetail.id} role={role ?? 'IO'} />}
    </div>
  )
}

function CaseMetadata({ stationName, category }: { stationName: string; category: string }) {
  return <section aria-labelledby="metadata-heading" className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-4"><h2 id="metadata-heading" className="text-h2 font-semibold text-neutral-900">Case metadata</h2><dl className="mt-4 space-y-3 text-small"><div><dt className="text-neutral-500">Police station</dt><dd className="mt-1 text-neutral-800">{stationName}</dd></div><div><dt className="text-neutral-500">Crime category</dt><dd className="mt-1 text-neutral-800">{category}</dd></div></dl></section>
}
