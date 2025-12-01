import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api, BlockSummary, BlockDetail } from './api'
import { useWebSocket } from './useWebSocket'

// Modern Icons
const Icons = {
  Sun: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" /></svg>,
  Moon: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" /></svg>,
  Pin: () => <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M10 2a1 1 0 011 1v1.323l3.954 1.582 1.599-.8a1 1 0 01.894 1.79l-1.233.616 1.738 5.42a1 1 0 01-.285 1.05A3.989 3.989 0 0115 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.715-5.349L11 6.477V16h2a1 1 0 110 2H7a1 1 0 110-2h2V6.477L6.237 7.582l1.715 5.349a1 1 0 01-.285 1.05A3.989 3.989 0 015 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.738-5.42-1.233-.617a1 1 0 01.894-1.788l1.599.799L9 4.323V3a1 1 0 011-1z" /></svg>,
  Search: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>,
  Document: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>,
  Chart: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>,
  Download: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>,
  Folder: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg>,
  Check: () => <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>,
  Clock: () => <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  X: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>,
  ChevronRight: () => <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>,
  Sparkles: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" /></svg>,
}

// Strip markdown for clean text previews
const stripMarkdown = (text: string): string => {
  return text
    .replace(/#{1,6}\s+/g, '') // headers
    .replace(/\*\*([^*]+)\*\*/g, '$1') // bold
    .replace(/\*([^*]+)\*/g, '$1') // italic
    .replace(/__([^_]+)__/g, '$1') // bold
    .replace(/_([^_]+)_/g, '$1') // italic
    .replace(/`([^`]+)`/g, '$1') // inline code
    .replace(/```[\s\S]*?```/g, '') // code blocks
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // links
    .replace(/^\s*[-*+]\s+/gm, '• ') // list items
    .replace(/^\s*\d+\.\s+/gm, '') // numbered lists
    .replace(/>\s+/g, '') // blockquotes
    .replace(/\n{2,}/g, ' ') // multiple newlines
    .trim()
}

// Type colors and icons
const typeConfig: Record<string, { color: string; bg: string; icon: string }> = {
  requirement: { color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800', icon: '📋' },
  design: { color: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-50 dark:bg-purple-900/30 border-purple-200 dark:border-purple-800', icon: '🎨' },
  task: { color: 'text-green-600 dark:text-green-400', bg: 'bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800', icon: '✅' },
  decision: { color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-900/30 border-amber-200 dark:border-amber-800', icon: '⚡' },
  knowledge: { color: 'text-cyan-600 dark:text-cyan-400', bg: 'bg-cyan-50 dark:bg-cyan-900/30 border-cyan-200 dark:border-cyan-800', icon: '💡' },
}

function App() {
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('darkMode') === 'true' || window.matchMedia('(prefers-color-scheme: dark)').matches)
  const [sidebarOpen] = useState(true)
  const [activeView, setActiveView] = useState<'specs' | 'search' | 'pinned' | 'analytics'>('specs')
  const [selectedType, setSelectedType] = useState<string | null>(null)
  const [selectedSource, setSelectedSource] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeSearch, setActiveSearch] = useState('')
  const [selectedBlock, setSelectedBlock] = useState<BlockDetail | null>(null)
  const [autoRefresh] = useState(() => localStorage.getItem('autoRefresh') !== 'false')
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  const { isConnected } = useWebSocket({ enabled: autoRefresh, onRefresh: () => showToast('Specs updated', 'success') })

  useEffect(() => { document.documentElement.classList.toggle('dark', darkMode); localStorage.setItem('darkMode', String(darkMode)) }, [darkMode])
  useEffect(() => { localStorage.setItem('autoRefresh', String(autoRefresh)) }, [autoRefresh])

  const showToast = (message: string, type: 'success' | 'error') => { setToast({ message, type }); setTimeout(() => setToast(null), 3000) }

  const { data: blocksData, isLoading } = useQuery({ queryKey: ['blocks'], queryFn: () => api.getBlocks() })
  const { data: statsData } = useQuery({ queryKey: ['stats'], queryFn: api.getStats })
  const { data: searchData, isLoading: searchLoading } = useQuery({ queryKey: ['search', activeSearch], queryFn: () => api.search(activeSearch, 20), enabled: activeSearch.length > 0 })
  const { data: pinnedData } = useQuery({ queryKey: ['pinned'], queryFn: api.getPinned })
  const exportMutation = useMutation({ mutationFn: api.exportPack, onSuccess: (d) => showToast(d.message, d.success ? 'success' : 'error'), onError: () => showToast('Export failed', 'error') })

  const handleBlockClick = async (block: BlockSummary) => { const detail = await api.getBlock(block.id); setSelectedBlock(detail) }
  const handleSearch = (e: React.FormEvent) => { e.preventDefault(); setActiveSearch(searchQuery); setActiveView('search') }

  // Group blocks by source file
  const blocksBySource = blocksData?.blocks.reduce((acc, block) => {
    const source = block.source.split('/').slice(-2).join('/')
    if (!acc[source]) acc[source] = []
    acc[source].push(block)
    return acc
  }, {} as Record<string, BlockSummary[]>) || {}

  // Filter blocks
  const filteredBlocks = blocksData?.blocks.filter(b => {
    if (selectedType && b.type !== selectedType) return false
    if (selectedSource && !b.source.includes(selectedSource)) return false
    return true
  }) || []

  const getTypeStyle = (type: string) => typeConfig[type] || typeConfig.knowledge

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-xl shadow-lg backdrop-blur-sm ${toast.type === 'success' ? 'bg-emerald-500/90 text-white' : 'bg-red-500/90 text-white'} animate-in slide-in-from-top-2`}>
          {toast.message}
        </div>
      )}

      {/* Header */}
      <header className="sticky top-0 z-40 backdrop-blur-xl bg-white/80 dark:bg-slate-900/80 border-b border-slate-200/50 dark:border-slate-700/50">
        <div className="flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-lg shadow-violet-500/25">
                <span className="text-white font-bold text-lg">S</span>
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-slate-900 to-slate-600 dark:from-white dark:to-slate-400 bg-clip-text text-transparent">SpecMem</h1>
                <p className="text-xs text-slate-500 dark:text-slate-400">Living Documentation</p>
              </div>
            </div>
          </div>

          {/* Search Bar */}
          <form onSubmit={handleSearch} className="flex-1 max-w-xl mx-8">
            <div className="relative">
              <Icons.Search />
              <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search specifications..."
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500 transition-all" />
              <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"><Icons.Search /></div>
            </div>
          </form>

          <div className="flex items-center gap-3">
            {isConnected && <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400"><span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>Live</span>}
            <button onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-violet-500 to-purple-600 text-white font-medium shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 transition-all disabled:opacity-50">
              <Icons.Download />{exportMutation.isPending ? 'Exporting...' : 'Export Pack'}
            </button>
            <button onClick={() => setDarkMode(!darkMode)} className="p-2.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
              {darkMode ? <Icons.Sun /> : <Icons.Moon />}
            </button>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className={`${sidebarOpen ? 'w-64' : 'w-16'} flex-shrink-0 border-r border-slate-200/50 dark:border-slate-700/50 bg-white/50 dark:bg-slate-900/50 backdrop-blur-sm min-h-[calc(100vh-73px)] transition-all duration-300`}>
          <nav className="p-4 space-y-2">
            {[
              { id: 'specs', label: 'Specifications', icon: <Icons.Document />, count: blocksData?.total },
              { id: 'search', label: 'Search', icon: <Icons.Search /> },
              { id: 'pinned', label: 'Pinned', icon: <Icons.Pin />, count: pinnedData?.total },
              { id: 'analytics', label: 'Analytics', icon: <Icons.Chart /> },
            ].map((item) => (
              <button key={item.id} onClick={() => setActiveView(item.id as typeof activeView)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all ${activeView === item.id ? 'bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 font-medium' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'}`}>
                {item.icon}
                {sidebarOpen && <span className="flex-1 text-left">{item.label}</span>}
                {sidebarOpen && item.count !== undefined && <span className="text-xs bg-slate-200 dark:bg-slate-700 px-2 py-0.5 rounded-full">{item.count}</span>}
              </button>
            ))}
          </nav>

          {sidebarOpen && statsData && (
            <div className="px-4 py-4 border-t border-slate-200/50 dark:border-slate-700/50">
              <h3 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">By Type</h3>
              <div className="space-y-1">
                {Object.entries(statsData.by_type).map(([type, count]) => (
                  <button key={type} onClick={() => { setSelectedType(selectedType === type ? null : type); setActiveView('specs') }}
                    className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm transition-all ${selectedType === type ? 'bg-slate-200 dark:bg-slate-700' : 'hover:bg-slate-100 dark:hover:bg-slate-800'}`}>
                    <span>{typeConfig[type]?.icon || '📄'}</span>
                    <span className="flex-1 text-left capitalize text-slate-700 dark:text-slate-300">{type}</span>
                    <span className="text-xs text-slate-500">{count}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {sidebarOpen && Object.keys(blocksBySource).length > 0 && (
            <div className="px-4 py-4 border-t border-slate-200/50 dark:border-slate-700/50">
              <h3 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">Sources</h3>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {Object.entries(blocksBySource).slice(0, 10).map(([source, blocks]) => (
                  <button key={source} onClick={() => { setSelectedSource(selectedSource === source ? null : source); setActiveView('specs') }}
                    className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm transition-all ${selectedSource === source ? 'bg-slate-200 dark:bg-slate-700' : 'hover:bg-slate-100 dark:hover:bg-slate-800'}`}>
                    <Icons.Folder />
                    <span className="flex-1 text-left truncate text-slate-700 dark:text-slate-300 text-xs">{source}</span>
                    <span className="text-xs text-slate-500">{blocks.length}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6 overflow-auto">
          {/* Specs View */}
          {activeView === 'specs' && (
            <div>
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
                    {selectedType ? `${selectedType.charAt(0).toUpperCase() + selectedType.slice(1)}s` : selectedSource ? selectedSource : 'All Specifications'}
                  </h2>
                  <p className="text-slate-500 dark:text-slate-400 mt-1">{filteredBlocks.length} items • Living documentation for your project</p>
                </div>
                {(selectedType || selectedSource) && (
                  <button onClick={() => { setSelectedType(null); setSelectedSource(null) }} className="text-sm text-violet-600 dark:text-violet-400 hover:underline">Clear filters</button>
                )}
              </div>

              {/* Stats Cards */}
              <div className="grid grid-cols-4 gap-4 mb-8">
                {[
                  { label: 'Total Specs', value: statsData?.total_blocks || 0, color: 'from-blue-500 to-cyan-500', icon: '📊' },
                  { label: 'Active', value: statsData?.active_count || 0, color: 'from-emerald-500 to-green-500', icon: '✅' },
                  { label: 'Pinned', value: statsData?.pinned_count || 0, color: 'from-amber-500 to-orange-500', icon: '📌' },
                  { label: 'Legacy', value: statsData?.legacy_count || 0, color: 'from-slate-400 to-slate-500', icon: '📦' },
                ].map((stat) => (
                  <div key={stat.label} className="relative overflow-hidden rounded-2xl bg-white dark:bg-slate-800/50 border border-slate-200/50 dark:border-slate-700/50 p-5 shadow-sm">
                    <div className={`absolute top-0 right-0 w-24 h-24 bg-gradient-to-br ${stat.color} opacity-10 rounded-full -translate-y-8 translate-x-8`}></div>
                    <span className="text-2xl">{stat.icon}</span>
                    <p className="text-3xl font-bold text-slate-900 dark:text-white mt-2">{stat.value}</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400">{stat.label}</p>
                  </div>
                ))}
              </div>

              {/* Spec Cards */}
              {isLoading ? (
                <div className="flex items-center justify-center py-20">
                  <div className="w-8 h-8 border-4 border-violet-500 border-t-transparent rounded-full animate-spin"></div>
                </div>
              ) : filteredBlocks.length === 0 ? (
                <div className="text-center py-20">
                  <Icons.Document />
                  <p className="text-slate-500 dark:text-slate-400 mt-4">No specifications found</p>
                </div>
              ) : (
                <div className="grid gap-4">
                  {filteredBlocks.map((block) => {
                    const style = getTypeStyle(block.type)
                    return (
                      <div key={block.id} onClick={() => handleBlockClick(block)}
                        className={`group relative overflow-hidden rounded-xl border ${style.bg} p-5 cursor-pointer hover:shadow-lg hover:scale-[1.01] transition-all duration-200`}>
                        <div className="flex items-start gap-4">
                          <div className={`w-10 h-10 rounded-xl ${style.bg} flex items-center justify-center text-xl flex-shrink-0`}>
                            {typeConfig[block.type]?.icon || '📄'}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-2">
                              <span className={`text-xs font-semibold uppercase tracking-wider ${style.color}`}>{block.type}</span>
                              {block.pinned && <span className="text-amber-500"><Icons.Pin /></span>}
                              {block.status === 'legacy' && <span className="text-xs bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400 px-2 py-0.5 rounded-full">Legacy</span>}
                            </div>
                            <p className="text-slate-800 dark:text-slate-200 leading-relaxed">{stripMarkdown(block.text_preview)}</p>
                            <div className="flex items-center gap-4 mt-3 text-xs text-slate-500 dark:text-slate-400">
                              <span className="flex items-center gap-1"><Icons.Folder />{block.source.split('/').slice(-2).join('/')}</span>
                            </div>
                          </div>
                          <Icons.ChevronRight />
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* Search View */}
          {activeView === 'search' && (
            <div>
              <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">Search Results</h2>
              <p className="text-slate-500 dark:text-slate-400 mb-6">{activeSearch ? `Results for "${activeSearch}"` : 'Enter a query to search specifications'}</p>

              {searchLoading ? (
                <div className="flex items-center justify-center py-20"><div className="w-8 h-8 border-4 border-violet-500 border-t-transparent rounded-full animate-spin"></div></div>
              ) : !activeSearch ? (
                <div className="text-center py-20 text-slate-500"><Icons.Search /><p className="mt-4">Use the search bar above to find specifications</p></div>
              ) : searchData?.results.length === 0 ? (
                <div className="text-center py-20 text-slate-500"><p>No results found for "{activeSearch}"</p></div>
              ) : (
                <div className="space-y-4">
                  {searchData?.results.map((result, idx) => {
                    const style = getTypeStyle(result.block.type)
                    return (
                      <div key={result.block.id} onClick={() => handleBlockClick(result.block)} className={`rounded-xl border ${style.bg} p-5 cursor-pointer hover:shadow-lg transition-all`}>
                        <div className="flex items-center gap-3 mb-3">
                          <span className="w-8 h-8 rounded-lg bg-violet-100 dark:bg-violet-900/50 flex items-center justify-center text-violet-600 dark:text-violet-400 font-bold text-sm">#{idx + 1}</span>
                          <span className={`text-xs font-semibold uppercase ${style.color}`}>{result.block.type}</span>
                          <span className="text-xs text-slate-500 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-full">Score: {(result.score * 100).toFixed(0)}%</span>
                        </div>
                        <p className="text-slate-800 dark:text-slate-200">{stripMarkdown(result.block.text_preview)}</p>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* Pinned View */}
          {activeView === 'pinned' && (
            <div>
              <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">📌 Pinned Specifications</h2>
              <p className="text-slate-500 dark:text-slate-400 mb-6">Critical specs that are always included in agent context</p>

              {pinnedData?.blocks.length === 0 ? (
                <div className="text-center py-20 text-slate-500"><p>No pinned specifications</p></div>
              ) : (
                <div className="space-y-4">
                  {pinnedData?.blocks.map((item) => {
                    const style = getTypeStyle(item.block.type)
                    return (
                      <div key={item.block.id} onClick={() => handleBlockClick(item.block)} className={`rounded-xl border ${style.bg} p-5 cursor-pointer hover:shadow-lg transition-all`}>
                        <div className="flex items-center gap-2 mb-3">
                          <span className="text-amber-500"><Icons.Pin /></span>
                          <span className={`text-xs font-semibold uppercase ${style.color}`}>{item.block.type}</span>
                        </div>
                        <p className="text-slate-800 dark:text-slate-200 mb-2">{stripMarkdown(item.block.text_preview)}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400 italic">{item.reason}</p>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* Analytics View */}
          {activeView === 'analytics' && statsData && (
            <div>
              <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">📊 Analytics</h2>
              <p className="text-slate-500 dark:text-slate-400 mb-6">Insights into your specification memory</p>

              <div className="grid grid-cols-2 gap-6">
                {/* Type Distribution */}
                <div className="rounded-2xl bg-white dark:bg-slate-800/50 border border-slate-200/50 dark:border-slate-700/50 p-6">
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Specification Types</h3>
                  <div className="space-y-3">
                    {Object.entries(statsData.by_type).map(([type, count]) => {
                      const percentage = Math.round((count / statsData.total_blocks) * 100)
                      return (
                        <div key={type}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                              <span>{typeConfig[type]?.icon}</span>
                              <span className="capitalize">{type}</span>
                            </span>
                            <span className="text-sm font-medium text-slate-900 dark:text-white">{count} ({percentage}%)</span>
                          </div>
                          <div className="h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                            <div className={`h-full bg-gradient-to-r from-violet-500 to-purple-500 rounded-full transition-all duration-500`} style={{ width: `${percentage}%` }}></div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Source Files */}
                <div className="rounded-2xl bg-white dark:bg-slate-800/50 border border-slate-200/50 dark:border-slate-700/50 p-6">
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Source Files</h3>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {Object.entries(statsData.by_source).sort((a, b) => b[1] - a[1]).map(([source, count]) => (
                      <div key={source} className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-700/50 last:border-0">
                        <span className="text-sm text-slate-600 dark:text-slate-400 truncate max-w-[200px]">{source.split('/').slice(-2).join('/')}</span>
                        <span className="text-sm font-medium text-slate-900 dark:text-white bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded-full">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Memory Stats */}
                <div className="col-span-2 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 p-6 text-white">
                  <h3 className="text-lg font-semibold mb-4">Memory Overview</h3>
                  <div className="grid grid-cols-4 gap-6">
                    <div>
                      <p className="text-4xl font-bold">{statsData.total_blocks}</p>
                      <p className="text-violet-200">Total Specs</p>
                    </div>
                    <div>
                      <p className="text-4xl font-bold">{(statsData.memory_size_bytes / 1024).toFixed(1)}</p>
                      <p className="text-violet-200">KB Memory</p>
                    </div>
                    <div>
                      <p className="text-4xl font-bold">{Object.keys(statsData.by_source).length}</p>
                      <p className="text-violet-200">Source Files</p>
                    </div>
                    <div>
                      <p className="text-4xl font-bold">{Object.keys(statsData.by_type).length}</p>
                      <p className="text-violet-200">Spec Types</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Block Detail Modal */}
      {selectedBlock && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50" onClick={() => setSelectedBlock(null)}>
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className={`${getTypeStyle(selectedBlock.type).bg} px-6 py-4 border-b border-slate-200/50 dark:border-slate-700/50`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{typeConfig[selectedBlock.type]?.icon || '📄'}</span>
                  <div>
                    <span className={`text-sm font-semibold uppercase ${getTypeStyle(selectedBlock.type).color}`}>{selectedBlock.type}</span>
                    <div className="flex items-center gap-2 mt-1">
                      {selectedBlock.pinned && <span className="text-xs bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 px-2 py-0.5 rounded-full">📌 Pinned</span>}
                      <span className={`text-xs px-2 py-0.5 rounded-full ${selectedBlock.status === 'active' ? 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300' : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400'}`}>{selectedBlock.status}</span>
                    </div>
                  </div>
                </div>
                <button onClick={() => setSelectedBlock(null)} className="p-2 hover:bg-slate-200/50 dark:hover:bg-slate-700/50 rounded-lg transition-colors"><Icons.X /></button>
              </div>
            </div>
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              <div className="prose prose-slate dark:prose-invert max-w-none prose-headings:text-slate-900 dark:prose-headings:text-white prose-p:text-slate-700 dark:prose-p:text-slate-300 prose-strong:text-slate-900 dark:prose-strong:text-white prose-code:bg-slate-100 dark:prose-code:bg-slate-800 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-slate-100 dark:prose-pre:bg-slate-800 prose-li:text-slate-700 dark:prose-li:text-slate-300">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{selectedBlock.text}</ReactMarkdown>
              </div>
              <div className="mt-6 pt-6 border-t border-slate-200 dark:border-slate-700 space-y-4">
                <div>
                  <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Source</h4>
                  <p className="text-sm text-slate-700 dark:text-slate-300 font-mono bg-slate-100 dark:bg-slate-700/50 px-3 py-2 rounded-lg">{selectedBlock.source}</p>
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">ID</h4>
                  <code className="text-xs text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-700/50 px-3 py-2 rounded-lg block">{selectedBlock.id}</code>
                </div>
                {selectedBlock.tags.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">Tags</h4>
                    <div className="flex flex-wrap gap-2">{selectedBlock.tags.map((tag, i) => <span key={i} className="text-xs bg-violet-100 dark:bg-violet-900/50 text-violet-700 dark:text-violet-300 px-2 py-1 rounded-full">{tag}</span>)}</div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
