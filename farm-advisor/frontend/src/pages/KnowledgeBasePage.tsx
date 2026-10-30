import { useState, useEffect } from 'react';
import {
  BookOpen,
  Upload,
  RefreshCw,
  Search,
  FileText,
  CheckCircle2,
  AlertCircle,
  FileCheck,
  Tag,
  Database,
} from 'lucide-react';
import {
  fetchKBDocuments,
  uploadKBDocument,
  ingestKBDocuments,
  searchKnowledgeBase,
} from '../api/client';
import type { KnowledgeDoc, KnowledgeSearchResult } from '../types';

export const KnowledgeBasePage = () => {
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isReindexing, setIsReindexing] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Search Tester
  const [searchQuery, setSearchQuery] = useState('');
  const [searchCrop, setSearchCrop] = useState('');
  const [searchResults, setSearchResults] = useState<KnowledgeSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const loadDocs = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await fetchKBDocuments();
      setDocs(data);
    } catch (err: unknown) {
      setErrorMessage('Could not load knowledge base documents.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDocs();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadStatus(null);
    setErrorMessage(null);

    try {
      const res = await uploadKBDocument(file);
      setUploadStatus(`Document "${res.filename}" uploaded and indexed into Chroma successfully!`);
      await loadDocs();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMessage(`Upload failed: ${msg}`);
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  };

  const handleReindex = async () => {
    setIsReindexing(true);
    setUploadStatus(null);
    setErrorMessage(null);
    try {
      const res = await ingestKBDocuments();
      setUploadStatus(
        `Knowledge base re-indexed! Processed ${res.documents_processed} documents into ${res.chunks_created} vector chunks.`
      );
      await loadDocs();
    } catch (err: unknown) {
      setErrorMessage('Vector re-indexing failed.');
    } finally {
      setIsReindexing(false);
    }
  };

  const handleSearchTest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    try {
      const results = await searchKnowledgeBase(searchQuery.trim(), searchCrop.trim() || undefined);
      setSearchResults(results);
    } catch {
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-farm-700 font-semibold text-xs tracking-wider uppercase mb-1">
            <Database className="w-4 h-4" />
            <span>Local Chroma Vector Store (RAG)</span>
          </div>
          <h1 className="text-2xl font-extrabold text-stone-900">Agronomic Knowledge Base</h1>
          <p className="text-sm text-stone-500 mt-1">
            Curated extension guides, crop calendars, and irrigation tables embedded via NVIDIA NIM Embeddings.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleReindex}
            disabled={isReindexing}
            className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-stone-100 hover:bg-stone-200 text-stone-800 text-xs font-bold border border-stone-200 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isReindexing ? 'animate-spin' : ''}`} />
            <span>{isReindexing ? 'Re-indexing...' : 'Re-index Vector Store'}</span>
          </button>

          <label className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-farm-600 hover:bg-farm-700 text-white text-xs font-bold shadow-xs cursor-pointer transition-colors">
            <Upload className="w-3.5 h-3.5" />
            <span>{isUploading ? 'Uploading...' : 'Upload Document (.md, .pdf)'}</span>
            <input
              type="file"
              accept=".md,.txt,.pdf"
              onChange={handleFileUpload}
              disabled={isUploading}
              className="hidden"
            />
          </label>
        </div>
      </div>

      {uploadStatus && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>{uploadStatus}</span>
        </div>
      )}

      {errorMessage && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs font-semibold flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Semantic Search Tester Card */}
      <div className="p-5 rounded-2xl bg-white border border-stone-200 shadow-xs space-y-4">
        <div className="flex items-center space-x-2">
          <Search className="w-4 h-4 text-farm-600" />
          <h2 className="text-sm font-bold text-stone-900">Semantic RAG Retrieval Tester</h2>
        </div>

        <form onSubmit={handleSearchTest} className="grid grid-cols-1 sm:grid-cols-5 gap-3">
          <div className="sm:col-span-3">
            <input
              type="text"
              placeholder="e.g. soil moisture for sowing corn, late blight fungicide timing..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-stone-200 text-sm focus:ring-2 focus:ring-farm-500 focus:outline-none"
            />
          </div>
          <div>
            <select
              value={searchCrop}
              onChange={(e) => setSearchCrop(e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl border border-stone-200 text-sm focus:ring-2 focus:ring-farm-500 focus:outline-none bg-white"
            >
              <option value="">All Crops</option>
              <option value="Tomato">Tomato</option>
              <option value="Corn">Corn</option>
              <option value="Wheat">Wheat</option>
              <option value="Potato">Potato</option>
              <option value="Rice">Rice</option>
            </select>
          </div>
          <div>
            <button
              type="submit"
              disabled={isSearching || !searchQuery.trim()}
              className="w-full py-2.5 rounded-xl bg-stone-900 hover:bg-stone-800 disabled:bg-stone-300 text-white text-xs font-bold transition-colors"
            >
              {isSearching ? 'Searching...' : 'Test Search'}
            </button>
          </div>
        </form>

        {/* Search Results Preview */}
        {searchResults.length > 0 && (
          <div className="pt-3 border-t border-stone-100 space-y-3">
            <span className="text-xs font-bold text-stone-500 uppercase tracking-wider">
              Retrieved Semantic Chunks ({searchResults.length})
            </span>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {searchResults.map((res, idx) => (
                <div key={idx} className="p-3.5 rounded-xl bg-stone-50 border border-stone-200 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-farm-800 font-mono text-[11px] truncate max-w-[200px]">
                      {res.source}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-farm-100 text-farm-800 font-bold text-[10px]">
                      Score: {res.score}
                    </span>
                  </div>
                  <p className="text-stone-700 line-clamp-4 font-mono text-[11px] leading-relaxed">
                    {res.content}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Indexed Documents Table/Cards */}
      <div className="space-y-4">
        <div className="flex items-center space-x-2">
          <BookOpen className="w-5 h-5 text-farm-600" />
          <h2 className="text-lg font-bold text-stone-900">Indexed Knowledge Documents ({docs.length})</h2>
        </div>

        {isLoading ? (
          <div className="py-12 text-center text-stone-400 text-sm">
            <div className="w-6 h-6 border-2 border-farm-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            Loading documents...
          </div>
        ) : docs.length === 0 ? (
          <div className="p-8 text-center bg-white rounded-2xl border border-stone-200 text-stone-500 text-sm">
            No documents found in knowledge base. Upload your first agronomy guide above!
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {docs.map((doc) => (
              <div
                key={doc.id}
                className="p-5 rounded-2xl bg-white border border-stone-200 hover:border-farm-300 hover:shadow-xs transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="p-2 rounded-lg bg-farm-50 text-farm-700">
                      <FileText className="w-5 h-5" />
                    </div>
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-stone-100 text-stone-700 border border-stone-200">
                      {doc.category}
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-stone-900 line-clamp-1">{doc.title}</h3>
                  <div className="text-[11px] text-stone-500 font-mono mt-0.5 truncate">{doc.filename}</div>

                  <div className="flex flex-wrap gap-1 mt-3">
                    {doc.crops.map((c) => (
                      <span
                        key={c}
                        className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200"
                      >
                        <Tag className="w-2.5 h-2.5" />
                        <span>{c}</span>
                      </span>
                    ))}
                  </div>
                </div>

                <div className="pt-4 mt-4 border-t border-stone-100 flex items-center justify-between text-xs text-stone-500">
                  <div className="flex items-center space-x-1">
                    <FileCheck className="w-3.5 h-3.5 text-farm-600" />
                    <span>~{doc.chunk_count} chunks</span>
                  </div>
                  <span>{(doc.size_bytes / 1024).toFixed(1)} KB</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
