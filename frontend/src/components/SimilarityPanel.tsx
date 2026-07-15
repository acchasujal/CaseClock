import { AlertTriangle, ShieldCheck, Layers, Link as LinkIcon } from 'lucide-react'

interface SimilarityPanelProps {
  caseId: string
  firNumber: string
}

export function SimilarityPanel({ caseId: _caseId, firNumber: _firNumber }: SimilarityPanelProps) {
  // Candidate features that the backend similarity model would analyze
  const matchParameters = [
    { name: 'Shared Suspect Network', status: 'Pending Model Link', desc: 'Checks co-accused logs and suspect records against other open cases.', icon: Layers },
    { name: 'Shared Phone Call Matches', status: 'Pending CDR Upload', desc: 'Identifies mutual cell-tower connections or call history logs.', icon: LinkIcon },
    { name: 'Shared Registered Address', status: 'Pending Database Sync', desc: 'Correlates home addresses or contact locations across districts.', icon: LinkIcon },
    { name: 'Shared Forensic Dependency', status: 'Available (Visual)', desc: 'Identifies lab bottle-necks (e.g. Bangalore Ballistics Lab).', icon: ShieldCheck, available: true }
  ]

  return (
    <div className="space-y-6">
      {/* Disclaimer Alert */}
      <div className="rounded-radius-md border border-amber-200 bg-amber-50 p-4 flex items-start space-x-3 text-amber-800">
        <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
        <div>
          <h3 className="font-semibold text-small">Similarity Analysis Fallback</h3>
          <p className="text-caption mt-1 leading-normal">
            No similarity data returned from the backend. The Similarity Engine (Lane 2) must be integrated to run co-accused clustering or phone correlates. Displays mock candidate match dimensions below.
          </p>
        </div>
      </div>

      {/* Similarity Inspection Panel */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Match parameters list */}
        <div className="lg:col-span-2 space-y-4">
          <h3 className="text-h2 font-semibold text-neutral-800">Similarity Match Dimensions</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {matchParameters.map((param) => {
              const Icon = param.icon
              return (
                <div 
                  key={param.name} 
                  className="p-4 rounded-radius-md border border-neutral-200 bg-neutral-50 shadow-sm flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-small font-semibold text-neutral-800">{param.name}</h4>
                      <Icon className="h-4 w-4 text-neutral-400" />
                    </div>
                    <p className="text-caption text-neutral-500 leading-normal">{param.desc}</p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-neutral-200/50 flex justify-between items-center text-caption font-mono">
                    <span className="text-neutral-400">Status</span>
                    <span className={param.available ? 'text-status-success font-semibold' : 'text-neutral-500 italic'}>
                      {param.status}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Similar Cases list stub */}
        <div className="rounded-radius-md border border-neutral-200 bg-neutral-50 p-5 flex flex-col justify-between">
          <div>
            <h3 className="font-semibold text-neutral-700 uppercase text-caption">Similar Investigations</h3>
            <p className="text-caption text-neutral-500 mt-2 leading-normal">
              Lists cases matching modus operandi or common suspects. Requires similarity query payload.
            </p>
          </div>
          
          <div className="mt-6 py-8 border border-dashed border-neutral-300 rounded-radius-sm bg-neutral-100 text-center">
            <Layers className="mx-auto h-8 w-8 text-neutral-400 mb-2" />
            <span className="text-caption font-semibold text-neutral-500">
              No Similar cases loaded
            </span>
            <p className="text-[10px] text-neutral-400 mt-1 max-w-[180px] mx-auto leading-normal">
              Prototype only supports detailed viewing for Case 847 and Case 902.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
