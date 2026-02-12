import React, { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Upload, FileText, MessageSquare, BookOpen, Sparkles, Loader2, Search } from 'lucide-react'
import { apiClient, KnowledgeSearchResult } from '../services/apiClient'
import { useToast } from '../components/Toast'
import { EmptyState } from '../components/EmptyState'

export const ChatbotBuilder: React.FC = () => {
  const { addToast } = useToast()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [extractedText, setExtractedText] = useState('')
  const [faqForm, setFaqForm] = useState({ question: '', answer: '', category: 'general', keywords: '' })
  const [docForm, setDocForm] = useState({ title: '', summary: '', category: 'general', content: '' })
  const [vectorPayload, setVectorPayload] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<KnowledgeSearchResult[]>([])

  const { data: faqStats } = useQuery({
    queryKey: ['faq-stats'],
    queryFn: () => apiClient.getFaqStats(),
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchInterval: 5 * 60 * 1000, // Auto-refresh every 5 minutes
  })

  const { data: faqCategories } = useQuery({
    queryKey: ['faq-categories'],
    queryFn: () => apiClient.getFaqCategories(),
    staleTime: 5 * 60 * 1000, // 5 minutes - categories don't change often
    gcTime: 30 * 60 * 1000, // 30 minutes
  })

  const documentMutation = useMutation({
    mutationFn: apiClient.processDocument,
    onSuccess: (result) => {
      const text = result.content?.text || ''
      setExtractedText(text)
      setVectorPayload(text)
      addToast({ type: 'success', title: 'Document Processed', message: 'Document processed successfully' })
    },
    onError: () => addToast({ type: 'error', title: 'Processing Failed', message: 'Failed to process document' })
  })

  const faqMutation = useMutation({
    mutationFn: apiClient.addFaq,
    onSuccess: () => {
      addToast({ type: 'success', title: 'FAQ Saved', message: 'FAQ has been saved successfully' })
      setFaqForm({ question: '', answer: '', category: 'general', keywords: '' })
    },
    onError: () => addToast({ type: 'error', title: 'Save Failed', message: 'Unable to save FAQ' })
  })

  const docMutation = useMutation({
    mutationFn: apiClient.addKnowledgeDocument,
    onSuccess: () => {
      addToast({ type: 'success', title: 'Document Saved', message: 'Business info saved to knowledge base' })
      setDocForm({ title: '', summary: '', category: 'general', content: '' })
    },
    onError: () => addToast({ type: 'error', title: 'Save Failed', message: 'Unable to save document' })
  })

  const vectorMutation = useMutation({
    mutationFn: apiClient.vectorizeKnowledge,
    onSuccess: () => addToast({ type: 'success', title: 'Content Vectorized', message: 'Content has been vectorized successfully' }),
    onError: () => addToast({ type: 'error', title: 'Vectorization Failed', message: 'Vectorization failed' })
  })

  const handleFileUpload = () => {
    if (!selectedFile) {
      addToast({ type: 'warning', title: 'No File Selected', message: 'Please choose a file first' })
      return
    }
    documentMutation.mutate(selectedFile)
  }

  const handleFaqSubmit = () => {
    if (!faqForm.question || !faqForm.answer) {
      addToast({ type: 'warning', title: 'Missing Fields', message: 'Question and answer are required' })
      return
    }
    faqMutation.mutate({
      question: faqForm.question,
      answer: faqForm.answer,
      category: faqForm.category,
      keywords: faqForm.keywords ? faqForm.keywords.split(',').map(k => k.trim()) : []
    })
  }

  const handleDocSubmit = () => {
    if (!docForm.title || !docForm.content) {
      addToast({ type: 'warning', title: 'Missing Fields', message: 'Title and content are required' })
      return
    }
    docMutation.mutate({
      title: docForm.title,
      summary: docForm.summary || docForm.content.slice(0, 160),
      category: docForm.category,
      content: docForm.content,
      tags: ['business-info'],
      keywords: docForm.summary ? docForm.summary.split(' ') : []
    })
  }

  const handleVectorize = () => {
    if (!vectorPayload) {
      addToast({ type: 'warning', title: 'Empty Content', message: 'Nothing to vectorize' })
      return
    }
    vectorMutation.mutate({ content: vectorPayload, metadata: { source: 'builder' } })
  }

  const handleSearch = async () => {
    if (!searchQuery) {
      setSearchResults([])
      return
    }
    try {
      const results = await apiClient.searchKnowledge(searchQuery)
      setSearchResults(results)
    } catch {
      addToast({ type: 'error', title: 'Search Failed', message: 'Failed to search knowledge base' })
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-wide text-brand-text/60 dark:text-gray-400">Chatbot Builder</p>
        <h1 className="text-3xl font-bold text-brand-text dark:text-white">Knowledge & FAQ Studio</h1>
        <p className="mt-2 text-brand-text/70 dark:text-gray-300">Upload documents, add FAQs, and preview chatbot responses.</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 space-y-6">
          <div className="rounded-2xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-brand-accent/20 rounded-xl">
                <Upload className="h-5 w-5 text-brand-primary" />
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400">Document ingestion</p>
                <h2 className="text-xl font-semibold text-brand-text dark:text-white">Upload PDF or DOCX</h2>
              </div>
            </div>
            <div className="space-y-3">
              <input
                type="file"
                accept=".pdf,.doc,.docx,.txt"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                className="block w-full text-sm text-brand-text dark:text-gray-100 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-brand-accent/20 file:text-brand-primary hover:file:bg-brand-accent/30"
              />
              <button
                onClick={handleFileUpload}
                className="inline-flex items-center gap-2 rounded-xl bg-brand-primary px-4 py-2 text-sm font-medium text-white hover:bg-brand-secondary disabled:opacity-50"
                disabled={!selectedFile || documentMutation.isPending}
              >
                {documentMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
                Process document
              </button>
            </div>
            {extractedText && (
              <div className="mt-4">
                <p className="text-sm font-medium text-brand-text dark:text-white mb-2">Extracted text</p>
                <textarea
                  className="w-full rounded-xl border border-brand-text/10 dark:border-gray-700 bg-brand-background/40 dark:bg-gray-900/40 text-sm text-brand-text dark:text-gray-100 p-3"
                  rows={8}
                  value={extractedText}
                  onChange={(e) => setExtractedText(e.target.value)}
                />
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-brand-accent/20 rounded-xl">
                <MessageSquare className="h-5 w-5 text-brand-primary" />
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400">FAQs</p>
                <h2 className="text-xl font-semibold text-brand-text dark:text-white">Add question & answer</h2>
              </div>
            </div>
            <input
              className="w-full rounded-xl border border-brand-text/10 dark:border-gray-700 px-3 py-2 bg-white dark:bg-gray-900 text-sm text-brand-text dark:text-gray-100"
              placeholder="Question"
              value={faqForm.question}
              onChange={(e) => setFaqForm({ ...faqForm, question: e.target.value })}
            />
            <textarea
              rows={4}
              className="w-full rounded-xl border border-brand-text/10 dark:border-gray-700 px-3 py-2 bg-white dark:bg-gray-900 text-sm text-brand-text dark:text-gray-100"
              placeholder="Answer"
              value={faqForm.answer}
              onChange={(e) => setFaqForm({ ...faqForm, answer: e.target.value })}
            />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <select
                className="rounded-xl border border-brand-text/10 dark:border-gray-700 px-3 py-2 bg-white dark:bg-gray-900 text-sm text-brand-text dark:text-gray-100"
                value={faqForm.category}
                onChange={(e) => setFaqForm({ ...faqForm, category: e.target.value })}
              >
                {(faqCategories || ['general', 'pricing', 'technical']).map(category => (
                  <option key={category} value={category}>{category}</option>
                ))}
              </select>
              <input
                className="rounded-xl border border-brand-text/10 dark:border-gray-700 px-3 py-2 bg-white dark:bg-gray-900 text-sm text-brand-text dark:text-gray-100"
                placeholder="Keywords comma separated"
                value={faqForm.keywords}
                onChange={(e) => setFaqForm({ ...faqForm, keywords: e.target.value })}
              />
            </div>
            <button
              onClick={handleFaqSubmit}
              className="inline-flex items-center gap-2 rounded-xl bg-brand-primary px-4 py-2 text-sm font-medium text-white hover:bg-brand-secondary"
              disabled={faqMutation.isPending}
            >
              {faqMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              Save FAQ
            </button>
          </div>

          <div className="rounded-2xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-brand-accent/20 rounded-xl">
                <BookOpen className="h-5 w-5 text-brand-primary" />
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400">Business info</p>
                <h2 className="text-xl font-semibold text-brand-text dark:text-white">Add knowledge snippet</h2>
              </div>
            </div>
            <input
              className="w-full rounded-xl border border-brand-text/10 dark:border-gray-700 px-3 py-2 bg-white dark:bg-gray-900 text-sm text-brand-text dark:text-gray-100"
              placeholder="Title"
              value={docForm.title}
              onChange={(e) => setDocForm({ ...docForm, title: e.target.value })}
            />
            <textarea
              rows={3}
              className="w-full rounded-xl border border-brand-text/10 dark:border-gray-700 px-3 py-2 bg-white dark:bg-gray-900 text-sm text-brand-text dark:text-gray-100"
              placeholder="Short summary"
              value={docForm.summary}
              onChange={(e) => setDocForm({ ...docForm, summary: e.target.value })}
            />
            <textarea
              rows={5}
              className="w-full rounded-xl border border-brand-text/10 dark:border-gray-700 px-3 py-2 bg-white dark:bg-gray-900 text-sm text-brand-text dark:text-gray-100"
              placeholder="Full content"
              value={docForm.content}
              onChange={(e) => setDocForm({ ...docForm, content: e.target.value })}
            />
            <button
              onClick={handleDocSubmit}
              className="inline-flex items-center gap-2 rounded-xl bg-brand-primary px-4 py-2 text-sm font-medium text-white hover:bg-brand-secondary"
              disabled={docMutation.isPending}
            >
              {docMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <BookOpen className="h-4 w-4" />}
              Save to knowledge base
            </button>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-2xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-brand-accent/20 rounded-xl">
                <Sparkles className="h-5 w-5 text-brand-primary" />
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400">Vectorization</p>
                <h2 className="text-xl font-semibold text-brand-text dark:text-white">Embed content</h2>
              </div>
            </div>
            <textarea
              className="w-full rounded-xl border border-brand-text/10 dark:border-gray-700 px-3 py-2 bg-white dark:bg-gray-900 text-sm text-brand-text dark:text-gray-100"
              rows={6}
              value={vectorPayload}
              onChange={(e) => setVectorPayload(e.target.value)}
              placeholder="Paste or reuse extracted text"
            />
            <button
              onClick={handleVectorize}
              className="mt-3 inline-flex items-center gap-2 rounded-xl bg-brand-primary px-4 py-2 text-sm font-medium text-white hover:bg-brand-secondary"
              disabled={vectorMutation.isPending}
            >
              {vectorMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              Vectorize content
            </button>
          </div>

          <div className="rounded-2xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm space-y-3">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-brand-accent/20 rounded-xl">
                <Search className="h-5 w-5 text-brand-primary" />
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400">Preview</p>
                <h2 className="text-xl font-semibold text-brand-text dark:text-white">Ask your bot</h2>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <input
                className="flex-1 rounded-xl border border-brand-text/10 dark:border-gray-700 px-3 py-2 bg-white dark:bg-gray-900 text-sm text-brand-text dark:text-gray-100"
                placeholder="Ask a question"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <button
                onClick={handleSearch}
                className="rounded-xl bg-brand-primary px-4 py-2 text-sm font-medium text-white hover:bg-brand-secondary"
              >
                Preview
              </button>
            </div>
            <div className="space-y-3">
              {searchResults.length === 0 ? (
                <EmptyState
                  icon={Search}
                  title="No preview yet"
                  description="Ask a question to see how your bot would respond."
                />
              ) : (
                searchResults.map(result => (
                  <div key={result.document_id} className="rounded-xl border border-brand-text/10 dark:border-gray-700 p-4">
                    <p className="text-sm font-semibold text-brand-text dark:text-white">{result.title}</p>
                    <p className="text-xs text-brand-text/60 dark:text-gray-400 mt-1">{result.summary}</p>
                    <p className="text-sm text-brand-text dark:text-gray-100 mt-2 whitespace-pre-wrap">{result.content_preview}</p>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-brand-text/10 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm space-y-3">
            <p className="text-xs uppercase tracking-wide text-brand-text/60 dark:text-gray-400">Stats</p>
            <h2 className="text-lg font-semibold text-brand-text dark:text-white">Knowledge health</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-2xl font-bold text-brand-text dark:text-white">{faqStats?.total_faqs ?? 0}</p>
                <p className="text-xs text-brand-text/60 dark:text-gray-400">FAQs</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-brand-text dark:text-white">{faqStats?.helpful_votes ?? 0}</p>
                <p className="text-xs text-brand-text/60 dark:text-gray-400">Helpful votes</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
