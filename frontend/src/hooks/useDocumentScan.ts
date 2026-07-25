import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/apiClient'
import type {
  DocumentConfirmRequest,
  DocumentConfirmResponse,
  DocumentScanResponse,
} from '@shared/contracts/api'

/**
 * Read a File as a base64-encoded string (data URL stripped to raw base64).
 */
function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      // result is "data:<mime>;base64,<data>" — strip the prefix
      const base64 = result.split(',')[1] ?? ''
      resolve(base64)
    }
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })
}

export function useScanDocument(caseId: string) {
  return useMutation<DocumentScanResponse, Error, { file: File; documentType: string }>({
    mutationFn: async ({ file, documentType }) => {
      // Encode file as base64 — avoids python-multipart requirement on the server
      const file_base64 = await fileToBase64(file)

      return apiFetch<DocumentScanResponse>(
        `/api/v1/cases/${caseId}/documents/scan`,
        {
          method: 'POST',
          body: JSON.stringify({
            filename: file.name,
            content_type: file.type || 'application/pdf',
            document_type: documentType,
            file_base64,
          }),
        },
      )
    },
  })
}

export function useConfirmDocument(caseId: string) {
  const queryClient = useQueryClient()

  return useMutation<
    DocumentConfirmResponse,
    Error,
    { documentId: string; request: DocumentConfirmRequest }
  >({
    mutationFn: async ({ documentId, request }) => {
      return apiFetch<DocumentConfirmResponse>(
        `/api/v1/cases/${caseId}/documents/${documentId}/confirm`,
        {
          method: 'POST',
          body: JSON.stringify(request),
        },
      )
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['caseDetail', caseId] })
      void queryClient.invalidateQueries({ queryKey: ['worklist'] })
    },
  })
}
