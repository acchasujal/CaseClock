import { useState } from 'react'
import { useScanDocument, useConfirmDocument } from '@/hooks/useDocumentScan'
import { Button } from '@/components/Button'
import { Input } from '@/components/Input'
import { RiskBadge } from '@/components/RiskBadge'
import { clockStatusToRisk } from '@/lib/utils'
import type { DocumentScanResponse } from '@shared/contracts/api'
import { FileText, Upload, ShieldCheck, CheckCircle2, AlertCircle, Loader2, X } from 'lucide-react'

interface DocumentScanModalProps {
  caseId: string
  isOpen: boolean
  onClose: () => void
  onConfirmed?: () => void
}

export function DocumentScanModal({ caseId, isOpen, onClose, onConfirmed }: DocumentScanModalProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [documentType, setDocumentType] = useState('fir')

  const scanMutation = useScanDocument(caseId)
  const confirmMutation = useConfirmDocument(caseId)

  const [scanResult, setScanResult] = useState<DocumentScanResponse | null>(null)

  // Editable candidate fields
  const [editableFirNumber, setEditableFirNumber] = useState('')
  const [editableStation, setEditableStation] = useState('')
  const [editableRegDate, setEditableRegDate] = useState('')
  const [editableCategory, setEditableCategory] = useState('')

  if (!isOpen) return null

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0])
    }
  }

  const handleScanSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFile) return

    try {
      const res = await scanMutation.mutateAsync({
        file: selectedFile,
        documentType,
      })
      setScanResult(res)
      setEditableFirNumber(res.candidate_facts.fir_number?.value || '')
      setEditableStation(res.candidate_facts.police_station?.value || '')
      setEditableRegDate(res.candidate_facts.fir_registration_date?.value || '')
      setEditableCategory(res.candidate_facts.offence_category?.value || 'theft')
    } catch {
      // Handled by mutation error state
    }
  }

  const handleConfirmSubmit = async () => {
    if (!scanResult) return

    try {
      await confirmMutation.mutateAsync({
        documentId: scanResult.document_id,
        request: {
          fir_number: editableFirNumber,
          police_station: editableStation,
          fir_registration_date: editableRegDate,
          offence_category: editableCategory,
        },
      })
      if (onConfirmed) onConfirmed()
      onClose()
    } catch {
      // Handled by mutation error state
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/60 p-4 backdrop-blur-xs"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div className="w-full max-w-2xl rounded-radius-md border border-neutral-200 bg-neutral-50 p-6 shadow-xl space-y-5 max-h-[90vh] overflow-y-auto">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-neutral-200 pb-3">
          <div className="flex items-center space-x-2">
            <div className="rounded-radius-sm bg-neutral-100 p-2 border border-neutral-200">
              <FileText className="h-5 w-5 text-neutral-800" aria-hidden="true" />
            </div>
            <div>
              <h2 id="modal-title" className="text-h2 font-bold text-neutral-900">
                Evidence Document Intelligence
              </h2>
              <p className="text-caption text-neutral-500">
                Powered by Zoho Catalyst Zia OCR & File Store
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-radius-sm p-1 text-neutral-400 hover:bg-neutral-200 hover:text-neutral-700 transition-colors"
            aria-label="Close modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* STEP 1: Upload & Scan Form */}
        {!scanResult ? (
          <form onSubmit={handleScanSubmit} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="doc-type" className="block text-small font-semibold text-neutral-700">
                Document Classification
              </label>
              <select
                id="doc-type"
                value={documentType}
                onChange={(e) => setDocumentType(e.target.value)}
                className="block w-full rounded-radius-sm border border-neutral-300 bg-neutral-100 px-3 py-2 text-small text-neutral-900 focus:border-status-info focus:ring-1 focus:ring-status-info"
              >
                <option value="fir">First Information Report (FIR)</option>
                <option value="complaint">Written Complaint</option>
                <option value="witness_statement">Witness Statement</option>
                <option value="case_diary">Case Diary Extract</option>
                <option value="medical_report">Medical / MLC Report</option>
                <option value="forensic_report">Forensic / FSL Report</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="block text-small font-semibold text-neutral-700">
                Upload Document (PDF, JPEG, PNG, TIFF)
              </label>
              <div className="border-2 border-dashed border-neutral-300 rounded-radius-md p-6 bg-neutral-100/50 text-center hover:border-status-info transition-colors">
                <Upload className="mx-auto h-8 w-8 text-neutral-400 mb-2" />
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png,.tiff,.bmp"
                  onChange={handleFileChange}
                  className="block w-full text-small text-neutral-500 file:mr-4 file:py-2 file:px-4 file:rounded-radius-sm file:border-0 file:text-small file:font-semibold file:bg-neutral-900 file:text-neutral-50 hover:file:bg-neutral-800"
                />
                <p className="text-caption text-neutral-400 mt-2">
                  Original document is securely stored in Zoho Catalyst File Store. Maximum file size: 20 MB.
                </p>
              </div>
            </div>

            {scanMutation.isPending && (
              <div className="rounded-radius-sm bg-neutral-100 p-3 border border-neutral-200 flex items-center space-x-3 text-small text-neutral-700">
                <Loader2 className="h-5 w-5 animate-spin text-status-info" />
                <div>
                  <div className="font-semibold">Processing Document...</div>
                  <div className="text-caption text-neutral-500">
                    Uploading to Catalyst File Store $\rightarrow$ Executing Zia OCR text extraction
                  </div>
                </div>
              </div>
            )}

            {scanMutation.isError && (
              <div className="rounded-radius-sm bg-neutral-100 p-3 border border-neutral-300 text-small text-status-danger flex items-center space-x-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{scanMutation.error.message}</span>
              </div>
            )}

            <div className="flex justify-end space-x-3 pt-3 border-t border-neutral-200">
              <Button type="button" variant="secondary" onClick={onClose}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={!selectedFile || scanMutation.isPending}
              >
                {scanMutation.isPending ? 'Scanning...' : 'Scan with Zia OCR'}
              </Button>
            </div>
          </form>
        ) : (
          /* STEP 2: Candidate Fact Review & Clock Preview */
          <div className="space-y-5">
            <div className="rounded-radius-sm bg-neutral-100 p-3 border border-neutral-200 flex items-center justify-between">
              <div className="flex items-center space-x-2 text-small text-neutral-800 font-semibold">
                <CheckCircle2 className="h-4 w-4 text-status-success" />
                <span>Zia OCR Extraction Complete ({scanResult.ocr_confidence}% Confidence)</span>
              </div>
              <span className="text-caption text-neutral-400 font-mono">
                Ref: {scanResult.document_id}
              </span>
            </div>

            {/* Candidate Facts Form */}
            <div className="space-y-3">
              <h3 className="text-small font-bold text-neutral-800 uppercase tracking-wider">
                Extracted Candidate Information (Review & Edit)
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Input
                  label="FIR Number"
                  value={editableFirNumber}
                  onChange={(e) => setEditableFirNumber(e.target.value)}
                />
                <Input
                  label="Police Station"
                  value={editableStation}
                  onChange={(e) => setEditableStation(e.target.value)}
                />
                <Input
                  label="Registration Date"
                  type="date"
                  value={editableRegDate}
                  onChange={(e) => setEditableRegDate(e.target.value)}
                />
                <div className="space-y-1">
                  <label className="block text-small font-semibold text-neutral-700">
                    Offence Category
                  </label>
                  <select
                    value={editableCategory}
                    onChange={(e) => setEditableCategory(e.target.value)}
                    className="block w-full rounded-radius-sm border border-neutral-300 bg-neutral-100 px-3 py-1.5 text-small text-neutral-900 focus:border-status-info focus:ring-1 focus:ring-status-info"
                  >
                    <option value="theft">Theft / Property Offence (60-day)</option>
                    <option value="cybercrime">Cyber Crime (60-day)</option>
                    <option value="homicide">Homicide / Murder (90-day)</option>
                    <option value="dacoity">Dacoity / Robbery (90-day)</option>
                    <option value="narcotics">Narcotics / NDPS (90-day)</option>
                    <option value="rape">POCSO / Sexual Assault (60-day)</option>
                  </select>
                </div>
              </div>
            </div>

            {/* STATUTORY CLOCK PREVIEW BOX */}
            {scanResult.clock_preview && (
              <div className="rounded-radius-md border border-neutral-300 bg-neutral-100 p-4 space-y-3">
                <div className="flex items-center justify-between border-b border-neutral-200 pb-2">
                  <div className="flex items-center space-x-2">
                    <ShieldCheck className="h-4 w-4 text-neutral-700" />
                    <span className="text-small font-bold text-neutral-900">
                      STATUTORY CLOCK PREVIEW
                    </span>
                  </div>
                  <span className="rounded-radius-sm bg-neutral-200 px-2 py-0.5 text-caption font-bold text-neutral-700 uppercase">
                    REQUIRES OFFICER CONFIRMATION
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-small">
                  <div>
                    <div className="text-caption text-neutral-500 font-medium">Statutory Limit</div>
                    <div className="font-bold text-neutral-900 font-mono mt-0.5">
                      {scanResult.clock_preview.duration_days} Days
                    </div>
                  </div>
                  <div>
                    <div className="text-caption text-neutral-500 font-medium">Calculated Deadline</div>
                    <div className="font-bold text-neutral-900 font-mono mt-0.5">
                      {scanResult.clock_preview.calculated_deadline}
                    </div>
                  </div>
                  <div>
                    <div className="text-caption text-neutral-500 font-medium">Days Remaining</div>
                    <div className="font-bold text-neutral-900 font-mono mt-0.5">
                      {scanResult.clock_preview.days_remaining}d
                    </div>
                  </div>
                  <div>
                    <div className="text-caption text-neutral-500 font-medium">Predicted Risk</div>
                    <div className="mt-0.5">
                      <RiskBadge level={clockStatusToRisk(scanResult.clock_preview.predicted_status)} />
                    </div>
                  </div>
                </div>

                <div className="text-caption text-neutral-500 border-t border-neutral-200 pt-2 font-mono">
                  {scanResult.clock_preview.bnss_reference}
                </div>
              </div>
            )}

            {confirmMutation.isError && (
              <div className="rounded-radius-sm bg-neutral-100 p-3 border border-neutral-300 text-small text-status-danger flex items-center space-x-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{confirmMutation.error.message}</span>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex justify-end space-x-3 pt-3 border-t border-neutral-200">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setScanResult(null)}
              >
                Back / Rescan
              </Button>
              <Button
                type="button"
                onClick={handleConfirmSubmit}
                disabled={confirmMutation.isPending}
              >
                {confirmMutation.isPending ? 'Confirming...' : 'Confirm & Apply Clock'}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
