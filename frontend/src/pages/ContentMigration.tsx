import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  Package,
  FileText,
  BookOpen,
  Users,
  Layers,
  Loader2,
  ArrowRight,
  FileSpreadsheet,
  Sparkles,
  RefreshCw,
} from 'lucide-react'
import { apiClient } from '../services/apiClient'
import { useToast } from '../components/Toast'
import { useAuth } from '../contexts/AuthContext'

type TabId = 'overview' | 'knowledge' | 'documents' | 'forms' | 'contacts'

const tabs: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: 'overview', label: 'Overview', icon: Layers },
  { id: 'knowledge', label: 'Knowledge & marketing', icon: BookOpen },
  { id: 'documents', label: 'Documents', icon: FileText },
  { id: 'forms', label: 'Forms', icon: FileSpreadsheet },
  { id: 'contacts', label: 'Contacts', icon: Users },
]

export const ContentMigration: React.FC = () => {
  const { addToast } = useToast()
  const { isAuthenticated } = useAuth()
  const [tab, setTab] = useState<TabId>('overview')

  const { data: cap, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['content-migration-capabilities'],
    queryFn: () => apiClient.getContentMigrationCapabilities(),
    enabled: isAuthenticated,
    staleTime: 60_000,
    retry: (failureCount, err: any) => {
      if (err?.response?.status === 401 || err?.response?.status === 403) return false
      return failureCount < 1
    },
  })

  const [file, setFile] = useState<File | null>(null)
  const [extracted, setExtracted] = useState('')
  const [kbTitle, setKbTitle] = useState('')
  const [kbCategory, setKbCategory] = useState('general')
  const [bulkJson, setBulkJson] = useState('')

  const processMut = useMutation({
    mutationFn: (f: File) => apiClient.processDocument(f),
    onSuccess: (res) => {
      const text = (res as { content?: { text?: string } }).content?.text || ''
      setExtracted(text)
      addToast({
        type: 'success',
        title: 'Text extracted',
        message: 'Review and edit below, then save to your knowledge base.',
      })
    },
    onError: () =>
      addToast({ type: 'error', title: 'Processing failed', message: 'Could not extract text from this file.' }),
  })

  const saveKbMut = useMutation({
    mutationFn: () =>
      apiClient.importKnowledgeItem({
        title: kbTitle.trim() || 'Imported content',
        content: extracted.trim(),
        category: kbCategory,
        document_type: 'article',
        tags: ['migration'],
      }),
    onSuccess: () => {
      addToast({ type: 'success', title: 'Saved', message: 'Content was added to your knowledge base.' })
      setExtracted('')
      setKbTitle('')
      setFile(null)
    },
    onError: () =>
      addToast({ type: 'error', title: 'Save failed', message: 'Could not import this content. Try the Chatbot Builder if this persists.' }),
  })

  const bulkMut = useMutation({
    mutationFn: (docs: Record<string, unknown>[]) => apiClient.bulkImportKnowledgeDocuments(docs),
    onSuccess: (res) => {
      addToast({
        type: 'success',
        title: 'Bulk import finished',
        message: `Imported ${res.imported ?? 0} of ${res.total ?? 0} document(s).`,
      })
      setBulkJson('')
    },
    onError: () =>
      addToast({ type: 'error', title: 'Bulk import failed', message: 'Check JSON shape and try again.' }),
  })

  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [onDup, setOnDup] = useState<'skip' | 'update' | 'merge'>('update')

  const importCsvMut = useMutation({
    mutationFn: (f: File) => apiClient.importLeadsCsv(f, { onDuplicate: onDup }),
    onSuccess: (r) => {
      addToast({
        type: 'success',
        title: 'Import complete',
        message: `Created ${r.created}, updated ${r.updated}, skipped ${r.skipped} rows.`,
      })
      setCsvFile(null)
    },
    onError: () =>
      addToast({
        type: 'error',
        title: 'Import failed',
        message: 'CSV needs email and name columns. See requirements below.',
      }),
  })

  const handleBulkSubmit = () => {
    let parsed: unknown
    try {
      parsed = JSON.parse(bulkJson)
    } catch {
      addToast({ type: 'warning', title: 'Invalid JSON', message: 'Paste a valid JSON array or { "documents": [...] }.' })
      return
    }
    const docs = Array.isArray(parsed)
      ? parsed
      : (parsed as { documents?: unknown }).documents
    if (!Array.isArray(docs)) {
      addToast({ type: 'warning', title: 'Invalid shape', message: 'Use a JSON array or { "documents": [ ... ] }.' })
      return
    }
    bulkMut.mutate(docs as Record<string, unknown>[])
  }

  const sections = cap?.sections

  return (
    <div className="space-y-8 pb-10">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-wide text-brand-text/60 dark:text-gray-400">Import center</p>
          <h1 className="text-3xl font-bold text-brand-text dark:text-white">Content migration</h1>
          <p className="mt-2 max-w-3xl text-brand-text/70 dark:text-gray-300">
            Move marketing copy, documents, forms, and contacts into Fikiri in one place. Keep sources as-is or refine
            after import—your choice.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refetch()}
          disabled={isFetching}
          className="inline-flex shrink-0 items-center gap-2 rounded-xl border border-brand-text/15 bg-white px-4 py-2.5 text-sm font-medium text-brand-text hover:bg-brand-background/60 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:hover:bg-gray-700"
        >
          <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh capabilities
        </button>
      </div>

      {isLoading && (
        <div className="flex items-center gap-2 text-brand-text/70 dark:text-gray-400">
          <Loader2 className="h-5 w-5 animate-spin" />
          Loading migration map…
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100">
          Could not load capabilities. Sign in again or retry.{' '}
          <button type="button" className="font-medium underline" onClick={() => void refetch()}>
            Retry
          </button>
        </div>
      )}

      <div className="flex flex-wrap gap-2 border-b border-brand-text/10 pb-3 dark:border-gray-700">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            disabled={isLoading}
            onClick={() => setTab(t.id)}
            className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
              tab === t.id
                ? 'bg-brand-primary text-white shadow-sm'
                : 'text-brand-text/80 hover:bg-brand-background/80 dark:text-gray-300 dark:hover:bg-gray-800'
            }`}
          >
            <t.icon className="h-4 w-4 shrink-0" />
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && sections && (
        <div className="grid gap-6 md:grid-cols-2">
          <section className="rounded-2xl border border-brand-text/10 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <div className="mb-3 flex items-center gap-2">
              <Package className="h-5 w-5 text-brand-primary" />
              <h2 className="text-lg font-semibold text-brand-text dark:text-white">{sections.knowledge_marketing.title}</h2>
            </div>
            <p className="text-sm text-brand-text/70 dark:text-gray-300">{sections.knowledge_marketing.description}</p>
            <ul className="mt-4 space-y-2 text-sm text-brand-text/80 dark:text-gray-300">
              {sections.knowledge_marketing.modes.map((m) => (
                <li key={m.id} className="flex gap-2">
                  <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-brand-primary" />
                  <span>
                    <span className="font-medium text-brand-text dark:text-white">{m.label}</span>
                    {m.notes ? ` — ${m.notes}` : ''}
                  </span>
                </li>
              ))}
            </ul>
            <Link
              to={sections.knowledge_marketing.related_ui_path}
              className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-brand-primary hover:underline"
            >
              Open knowledge studio <ArrowRight className="h-4 w-4" />
            </Link>
          </section>

          <section className="rounded-2xl border border-brand-text/10 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <div className="mb-3 flex items-center gap-2">
              <FileText className="h-5 w-5 text-brand-primary" />
              <h2 className="text-lg font-semibold text-brand-text dark:text-white">{sections.documents.title}</h2>
            </div>
            <p className="text-sm text-brand-text/70 dark:text-gray-300">{sections.documents.description}</p>
            <p className="mt-3 text-xs text-brand-text/60 dark:text-gray-400">
              Supported file types: {sections.documents.supported_file_extensions.join(', ')}
            </p>
            <Link
              to={sections.documents.related_ui_path}
              className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-brand-primary hover:underline"
            >
              Automations & workflows <ArrowRight className="h-4 w-4" />
            </Link>
          </section>

          <section className="rounded-2xl border border-brand-text/10 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <div className="mb-3 flex items-center gap-2">
              <FileSpreadsheet className="h-5 w-5 text-brand-primary" />
              <h2 className="text-lg font-semibold text-brand-text dark:text-white">{sections.forms.title}</h2>
            </div>
            <p className="text-sm text-brand-text/70 dark:text-gray-300">{sections.forms.description}</p>
            <p className="mt-3 text-sm text-brand-text/80 dark:text-gray-300">
              {sections.forms.form_templates.length} form template(s) available in this environment.
            </p>
          </section>

          <section className="rounded-2xl border border-brand-text/10 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <div className="mb-3 flex items-center gap-2">
              <Users className="h-5 w-5 text-brand-primary" />
              <h2 className="text-lg font-semibold text-brand-text dark:text-white">{sections.contacts.title}</h2>
            </div>
            <p className="text-sm text-brand-text/70 dark:text-gray-300">{sections.contacts.description}</p>
            <p className="mt-3 text-xs text-brand-text/60 dark:text-gray-400">
              Required columns: {sections.contacts.csv_requirements.required_columns.join(', ')}. Max{' '}
              {sections.contacts.csv_requirements.max_file_mb} MB, {sections.contacts.csv_requirements.max_rows.toLocaleString()}{' '}
              rows.
            </p>
            <Link
              to={sections.contacts.related_ui_path}
              className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-brand-primary hover:underline"
            >
              Open CRM <ArrowRight className="h-4 w-4" />
            </Link>
          </section>
        </div>
      )}

      {tab === 'knowledge' && (
        <div className="space-y-8">
          <div className="rounded-2xl border border-brand-text/10 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <h2 className="text-xl font-semibold text-brand-text dark:text-white">Upload → extract → save</h2>
            <p className="mt-2 text-sm text-brand-text/70 dark:text-gray-300">
              Upload PDF, Word, CSV, Excel, or text. We extract text so you can edit it before it becomes chatbot knowledge.
            </p>
            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
              <div className="flex-1 space-y-2">
                <label htmlFor="knowledge-file-upload" className="text-xs font-medium text-brand-text/70 dark:text-gray-400">File</label>
                <input
                  id="knowledge-file-upload"
                  name="knowledge_file"
                  type="file"
                  accept=".pdf,.doc,.docx,.txt,.csv,.xlsx,.xls,.md,.png,.jpg,.jpeg"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="block w-full text-sm text-brand-text file:mr-4 file:rounded-full file:border-0 file:bg-brand-accent/20 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-brand-primary dark:text-gray-100"
                />
              </div>
              <button
                type="button"
                disabled={!file || processMut.isPending}
                onClick={() => file && processMut.mutate(file)}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand-primary px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-secondary disabled:opacity-50"
              >
                {processMut.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
                Extract text
              </button>
            </div>
            {extracted ? (
              <div className="mt-6 space-y-3">
                <label htmlFor="import-kb-title" className="sr-only">
                  Title for this snippet
                </label>
                <input
                  id="import-kb-title"
                  name="kb_title"
                  className="w-full rounded-xl border border-brand-text/10 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                  placeholder="Title for this snippet"
                  value={kbTitle}
                  onChange={(e) => setKbTitle(e.target.value)}
                />
                <label htmlFor="import-kb-category" className="sr-only">
                  Category
                </label>
                <input
                  id="import-kb-category"
                  name="kb_category"
                  className="w-full rounded-xl border border-brand-text/10 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                  placeholder="Category (e.g. pricing, services)"
                  value={kbCategory}
                  onChange={(e) => setKbCategory(e.target.value)}
                />
                <label htmlFor="import-kb-extracted-body" className="sr-only">
                  Extracted text to save
                </label>
                <textarea
                  id="import-kb-extracted-body"
                  name="kb_extracted_text"
                  className="w-full rounded-xl border border-brand-text/10 bg-brand-background/40 p-3 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                  rows={10}
                  value={extracted}
                  onChange={(e) => setExtracted(e.target.value)}
                />
                <button
                  type="button"
                  disabled={!extracted.trim() || saveKbMut.isPending}
                  onClick={() => saveKbMut.mutate()}
                  className="inline-flex items-center gap-2 rounded-xl bg-brand-primary px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-secondary disabled:opacity-50"
                >
                  {saveKbMut.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <BookOpen className="h-4 w-4" />}
                  Save to knowledge base
                </button>
              </div>
            ) : null}
          </div>

          <div className="rounded-2xl border border-brand-text/10 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <h2 className="text-xl font-semibold text-brand-text dark:text-white">Bulk JSON import</h2>
            <p className="mt-2 text-sm text-brand-text/70 dark:text-gray-300">
              Paste <code className="rounded bg-brand-background/80 px-1.5 py-0.5 text-xs">documents</code> array (same fields as{' '}
              <code className="rounded bg-brand-background/80 px-1.5 py-0.5 text-xs">POST /api/chatbot/knowledge/import/bulk</code>
              ).
            </p>
            <label htmlFor="import-kb-bulk-json" className="sr-only">
              Bulk JSON documents
            </label>
            <textarea
              id="import-kb-bulk-json"
              name="kb_bulk_json"
              className="mt-4 w-full rounded-xl border border-brand-text/10 bg-brand-background/30 p-3 font-mono text-xs dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
              rows={12}
              placeholder={`{\n  "documents": [\n    { "title": "Pricing", "content": "Starter plan...", "category": "pricing" }\n  ]\n}`}
              value={bulkJson}
              onChange={(e) => setBulkJson(e.target.value)}
            />
            <button
              type="button"
              disabled={!bulkJson.trim() || bulkMut.isPending}
              onClick={handleBulkSubmit}
              className="mt-3 inline-flex items-center gap-2 rounded-xl bg-brand-primary px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-secondary disabled:opacity-50"
            >
              {bulkMut.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              Run bulk import
            </button>
          </div>

          <p className="text-sm text-brand-text/60 dark:text-gray-400">
            For FAQs, search preview, and vector tools, use{' '}
            <Link to="/ai/chatbot-builder" className="font-medium text-brand-primary hover:underline">
              Chatbot Builder
            </Link>
            .
          </p>
        </div>
      )}

      {tab === 'documents' && !sections && !isLoading && (
        <p className="text-sm text-brand-text/70 dark:text-gray-400">Load capabilities to see document templates.</p>
      )}

      {tab === 'documents' && sections && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-brand-text/10 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <h2 className="text-xl font-semibold text-brand-text dark:text-white">Merge templates</h2>
            <p className="mt-2 text-sm text-brand-text/70 dark:text-gray-300">
              These templates support generated documents (e.g. agreements, invoices). Automations and workflow actions can fill{' '}
              <code className="rounded bg-brand-background/80 px-1 text-xs">variables</code> per lead or job.
            </p>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-brand-text/10 text-brand-text/60 dark:border-gray-600 dark:text-gray-400">
                    <th className="py-2 pr-4 font-medium">ID</th>
                    <th className="py-2 pr-4 font-medium">Name</th>
                    <th className="py-2 pr-4 font-medium">Type</th>
                    <th className="py-2 font-medium">Variables</th>
                  </tr>
                </thead>
                <tbody>
                  {sections.documents.document_templates.map((row) => (
                    <tr key={row.id} className="border-b border-brand-text/5 dark:border-gray-700/80">
                      <td className="py-2 pr-4 font-mono text-xs text-brand-text/80 dark:text-gray-300">{row.id}</td>
                      <td className="py-2 pr-4 text-brand-text dark:text-gray-100">{row.name}</td>
                      <td className="py-2 pr-4 text-brand-text/80 dark:text-gray-400">{row.document_type}</td>
                      <td className="py-2 text-brand-text/80 dark:text-gray-400">{row.variable_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Link
              to={sections.documents.related_ui_path}
              className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-brand-primary hover:underline"
            >
              Configure in Automations <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      )}

      {tab === 'forms' && !sections && !isLoading && (
        <p className="text-sm text-brand-text/70 dark:text-gray-400">Load capabilities to see form templates.</p>
      )}

      {tab === 'forms' && sections && (
        <div className="rounded-2xl border border-brand-text/10 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
          <h2 className="text-xl font-semibold text-brand-text dark:text-white">Form templates</h2>
          <p className="mt-2 text-sm text-brand-text/70 dark:text-gray-300">
            Map fields from your previous provider to these definitions. Embed HTML is available from the API for each template id.
          </p>
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-brand-text/10 text-brand-text/60 dark:border-gray-600 dark:text-gray-400">
                  <th className="py-2 pr-4 font-medium">ID</th>
                  <th className="py-2 pr-4 font-medium">Name</th>
                  <th className="py-2 pr-4 font-medium">Industry</th>
                  <th className="py-2 font-medium">Fields</th>
                </tr>
              </thead>
              <tbody>
                {sections.forms.form_templates.map((row) => (
                  <tr key={row.id} className="border-b border-brand-text/5 dark:border-gray-700/80">
                    <td className="py-2 pr-4 font-mono text-xs text-brand-text/80 dark:text-gray-300">{row.id}</td>
                    <td className="py-2 pr-4 text-brand-text dark:text-gray-100">{row.name}</td>
                    <td className="py-2 pr-4 text-brand-text/80 dark:text-gray-400">{row.industry}</td>
                    <td className="py-2 text-brand-text/80 dark:text-gray-400">{row.field_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'contacts' && !sections && !isLoading && (
        <p className="text-sm text-brand-text/70 dark:text-gray-400">Load capabilities to confirm CSV limits and policies.</p>
      )}

      {tab === 'contacts' && sections && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-brand-text/10 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <h2 className="text-xl font-semibold text-brand-text dark:text-white">CSV import</h2>
            <p className="mt-2 text-sm text-brand-text/70 dark:text-gray-300">
              Required columns: <strong>email</strong>, <strong>name</strong>. Optional: phone, source, company.
            </p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="contacts-duplicate-policy" className="text-xs font-medium text-brand-text/70 dark:text-gray-400">On duplicate emails</label>
                <select
                  id="contacts-duplicate-policy"
                  name="contacts_duplicate_policy"
                  className="mt-1 w-full rounded-xl border border-brand-text/10 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                  value={onDup}
                  onChange={(e) => setOnDup(e.target.value as 'skip' | 'update' | 'merge')}
                >
                  {sections.contacts.on_duplicate_policies.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="contacts-csv-file" className="text-xs font-medium text-brand-text/70 dark:text-gray-400">CSV file</label>
                <input
                  id="contacts-csv-file"
                  name="contacts_csv"
                  type="file"
                  accept=".csv"
                  onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
                  className="mt-1 block w-full text-sm text-brand-text file:mr-4 file:rounded-full file:border-0 file:bg-brand-accent/20 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-brand-primary dark:text-gray-100"
                />
              </div>
            </div>
            <button
              type="button"
              disabled={!csvFile || importCsvMut.isPending}
              onClick={() => csvFile && importCsvMut.mutate(csvFile)}
              className="mt-4 inline-flex items-center gap-2 rounded-xl bg-brand-primary px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-secondary disabled:opacity-50"
            >
              {importCsvMut.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Users className="h-4 w-4" />}
              Import leads
            </button>
          </div>
          <Link to="/crm" className="inline-flex items-center gap-1 text-sm font-medium text-brand-primary hover:underline">
            Full CRM board & import history <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      )}
    </div>
  )
}
