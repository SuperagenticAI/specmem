import { useState, useEffect, useRef, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, apiExtended, kiroConfigApi, guidelinesApi, BlockSummary, BlockDetail, SessionResponse, ImpactGraphResponse, ActionResultResponse, SpecFileResponse, GuidelineResponse, ConversionResultResponse } from './api'
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
  Coverage: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  Chat: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>,
  Bolt: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>,
  User: () => <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>,
  Bot: () => <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>,
  Graph: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>,
  Play: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  Refresh: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>,
  Heart: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" /></svg>,
  Info: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  Cog: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>,
  Home: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>,
  Terminal: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>,
  ArrowRight: () => <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" /></svg>,
}

const stripMarkdown = (text: string): string => {
  return text.replace(/#{1,6}\s+/g, '').replace(/\*\*([^*]+)\*\*/g, '$1').replace(/\*([^*]+)\*/g, '$1').replace(/__([^_]+)__/g, '$1').replace(/_([^_]+)_/g, '$1').replace(/`([^`]+)`/g, '$1').replace(/```[\s\S]*?```/g, '').replace(/\[([^\]]+)\]\([^)]+\)/g, '$1').replace(/^\s*[-*+]\s+/gm, '• ').replace(/^\s*\d+\.\s+/gm, '').replace(/>\s+/g, '').replace(/\n{2,}/g, ' ').trim()
}

const typeConfig: Record<string, { color: string; bg: string; icon: string }> = {
  requirement: { color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800', icon: '📋' },
  design: { color: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-50 dark:bg-purple-900/30 border-purple-200 dark:border-purple-800', icon: '🎨' },
  task: { color: 'text-green-600 dark:text-green-400', bg: 'bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800', icon: '✅' },
  decision: { color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-900/30 border-amber-200 dark:border-amber-800', icon: '⚡' },
  knowledge: { color: 'text-cyan-600 dark:text-cyan-400', bg: 'bg-cyan-50 dark:bg-cyan-900/30 border-cyan-200 dark:border-cyan-800', icon: '💡' },
}

type ViewType = 'home' | 'specs' | 'search' | 'pinned' | 'analytics' | 'coverage' | 'sessions' | 'powers' | 'graph' | 'config' | 'guidelines'


// Animated Counter Component
const AnimatedCounter = ({ value, duration = 1000 }: { value: number; duration?: number }) => {
  const [count, setCount] = useState(0)
  useEffect(() => {
    let start = 0
    const end = value
    if (start === end) return
    const incrementTime = Math.max(duration / end, 10)
    const timer = setInterval(() => {
      start += Math.ceil(end / 50)
      if (start >= end) { setCount(end); clearInterval(timer) }
      else setCount(start)
    }, incrementTime)
    return () => clearInterval(timer)
  }, [value, duration])
  return <span>{count}</span>
}

const Skeleton = ({ className = '' }: { className?: string }) => (
  <div className={`animate-pulse bg-slate-200 dark:bg-zinc-800 rounded ${className}`} />
)

const HealthScoreCircle = ({ score, grade, color, size = 'lg' }: { score: number; grade: string; color: string; size?: 'sm' | 'lg' }) => {
  const dimensions = size === 'sm' ? { w: 80, r: 30, stroke: 6 } : { w: 128, r: 45, stroke: 8 }
  const circumference = 2 * Math.PI * dimensions.r
  const strokeDashoffset = circumference - (score / 100) * circumference
  return (
    <div className={`relative ${size === 'sm' ? 'w-20 h-20' : 'w-32 h-32'}`}>
      <svg className={`${size === 'sm' ? 'w-20 h-20' : 'w-32 h-32'} transform -rotate-90`}>
        <circle cx={dimensions.w/2} cy={dimensions.w/2} r={dimensions.r} stroke="currentColor" strokeWidth={dimensions.stroke} fill="none" className="text-slate-200 dark:text-zinc-800" />
        <circle cx={dimensions.w/2} cy={dimensions.w/2} r={dimensions.r} stroke={color} strokeWidth={dimensions.stroke} fill="none" strokeLinecap="round" style={{ strokeDasharray: circumference, strokeDashoffset, transition: 'stroke-dashoffset 1s ease-out' }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`${size === 'sm' ? 'text-xl' : 'text-3xl'} font-bold`} style={{ color }}>{grade}</span>
        <span className={`${size === 'sm' ? 'text-xs' : 'text-sm'} text-slate-500 dark:text-zinc-400`}>{Math.round(score)}%</span>
      </div>
    </div>
  )
}

const QuickActionButton = ({ icon, label, onClick, loading, variant = 'default' }: { icon: React.ReactNode; label: string; onClick: () => void; loading?: boolean; variant?: 'default' | 'primary' }) => (
  <button onClick={onClick} disabled={loading} className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all disabled:opacity-50 ${variant === 'primary' ? 'bg-gradient-to-r from-violet-500 to-purple-600 text-white shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40' : 'bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 text-slate-700 dark:text-white hover:bg-slate-50 dark:hover:bg-zinc-800'}`}>
    {loading ? <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" /> : icon}
    <span>{label}</span>
  </button>
)

// Dashboard Card Component
const DashboardCard = ({ title, icon, children, onClick, gradient, className = '' }: { title: string; icon: React.ReactNode; children: React.ReactNode; onClick?: () => void; gradient?: string; className?: string }) => (
  <div onClick={onClick} className={`rounded-2xl bg-white dark:bg-zinc-900 backdrop-blur-sm border border-slate-200/50 dark:border-zinc-800 overflow-hidden shadow-lg hover:shadow-xl transition-all duration-300 ${onClick ? 'cursor-pointer hover:scale-[1.02]' : ''} ${className}`}>
    {gradient && <div className={`h-1 bg-gradient-to-r ${gradient}`} />}
    <div className="p-5">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-slate-500 dark:text-violet-400">{icon}</span>
        <h3 className="font-semibold text-slate-900 dark:text-white">{title}</h3>
      </div>
      {children}
    </div>
  </div>
)

// Force Graph Component
const ForceGraph = ({ data, onNodeClick }: { data: ImpactGraphResponse | undefined; onNodeClick?: (node: any) => void }) => {
  const svgRef = useRef<SVGSVGElement>(null)
  const [nodes, setNodes] = useState<any[]>([])
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)
  const [filter, setFilter] = useState<string | null>(null)

  useEffect(() => {
    if (!data?.nodes.length) return
    const centerX = 400, centerY = 300, radius = 200
    const positioned = data.nodes.map((node, i) => {
      const angle = (i / data.nodes.length) * 2 * Math.PI
      const jitter = Math.random() * 50 - 25
      return { ...node, x: centerX + Math.cos(angle) * (radius + jitter), y: centerY + Math.sin(angle) * (radius + jitter) }
    })
    setNodes(positioned)
  }, [data])

  const getNodeColor = (type: string) => {
    switch (type) { case 'spec': return '#8b5cf6'; case 'code': return '#10b981'; case 'test': return '#f59e0b'; default: return '#64748b' }
  }

  const filteredNodes = filter ? nodes.filter(n => n.type === filter) : nodes
  const filteredNodeIds = new Set(filteredNodes.map(n => n.id))
  const filteredEdges = data?.edges.filter(e => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)) || []

  if (!data?.nodes.length) {
    return <div className="flex flex-col items-center justify-center h-64 text-slate-500"><Icons.Graph /><p className="mt-4">No graph data available</p></div>
  }

  return (
    <div className="relative">
      <div className="absolute top-4 left-4 flex gap-2 z-10">
        {['spec', 'code', 'test'].map(type => (
          <button key={type} onClick={() => setFilter(filter === type ? null : type)} className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${filter === type ? 'bg-violet-500 text-white' : 'bg-white dark:bg-zinc-900 text-slate-700 dark:text-white border border-slate-200 dark:border-zinc-700'}`}>
            <span className="w-2 h-2 rounded-full inline-block mr-2" style={{ backgroundColor: getNodeColor(type) }} />{type}
          </button>
        ))}
      </div>
      <svg ref={svgRef} viewBox="0 0 800 600" className="w-full h-[400px] bg-slate-50 dark:bg-black rounded-xl">
        <defs><marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill="#94a3b8" /></marker></defs>
        {filteredEdges.map((edge, i) => {
          const source = nodes.find(n => n.id === edge.source), target = nodes.find(n => n.id === edge.target)
          if (!source || !target) return null
          return <line key={i} x1={source.x} y1={source.y} x2={target.x} y2={target.y} stroke={hoveredNode === source.id || hoveredNode === target.id ? '#8b5cf6' : '#3f3f46'} strokeWidth={hoveredNode === source.id || hoveredNode === target.id ? 2 : 1} markerEnd="url(#arrowhead)" className="transition-all" />
        })}
        {filteredNodes.map(node => (
          <g key={node.id} transform={`translate(${node.x}, ${node.y})`} onMouseEnter={() => setHoveredNode(node.id)} onMouseLeave={() => setHoveredNode(null)} onClick={() => onNodeClick?.(node)} className="cursor-pointer">
            <circle r={hoveredNode === node.id ? 14 : 10} fill={getNodeColor(node.type)} className="transition-all" style={{ filter: hoveredNode === node.id ? 'drop-shadow(0 4px 6px rgba(0,0,0,0.3))' : 'none' }} />
            {hoveredNode === node.id && <text y={-20} textAnchor="middle" className="text-xs fill-slate-700 dark:fill-white font-medium">{node.label}</text>}
          </g>
        ))}
      </svg>
      <div className="mt-4 flex items-center justify-center gap-6 text-sm text-slate-500 dark:text-zinc-400">
        <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-violet-500" /> Specs ({data.stats.nodes_by_type?.spec || 0})</span>
        <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-emerald-500" /> Code ({data.stats.nodes_by_type?.code || 0})</span>
        <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-amber-500" /> Tests ({data.stats.nodes_by_type?.test || 0})</span>
      </div>
    </div>
  )
}

const ActionResultModal = ({ result, onClose }: { result: ActionResultResponse | null; onClose: () => void }) => {
  if (!result) return null
  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in" onClick={onClose}>
      <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl max-w-md w-full overflow-hidden animate-scale-in border dark:border-zinc-800" onClick={e => e.stopPropagation()}>
        <div className={`px-6 py-4 ${result.success ? 'bg-gradient-to-r from-emerald-500 to-green-500' : 'bg-gradient-to-r from-red-500 to-rose-500'}`}>
          <div className="flex items-center gap-3 text-white">{result.success ? <Icons.Check /> : <Icons.X />}<span className="font-semibold capitalize">{result.action}</span></div>
        </div>
        <div className="p-6">
          <p className="text-slate-700 dark:text-white mb-4">{result.message}</p>
          {result.data && <div className="bg-slate-50 dark:bg-black rounded-lg p-4 text-sm font-mono border dark:border-zinc-800"><pre className="text-slate-600 dark:text-zinc-300 overflow-auto">{JSON.stringify(result.data, null, 2)}</pre></div>}
          {result.error && <p className="text-red-500 text-sm mt-2">{result.error}</p>}
        </div>
        <div className="px-6 pb-6"><button onClick={onClose} className="w-full py-2.5 bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-white rounded-xl hover:bg-slate-200 dark:hover:bg-zinc-700 transition-colors">Close</button></div>
      </div>
    </div>
  )
}

// Coverage View Component with filtering and grid layout
import { CoverageResponse, FeatureCoverageResponse, CriterionResponse } from './api'

type CoverageFilter = 'all' | 'covered' | 'uncovered'

const CoverageView = ({ 
  coverageData, 
  coverageLoading,
  getCoverageBg
}: { 
  coverageData: CoverageResponse | undefined
  coverageLoading: boolean
  getCoverageBg: (pct: number) => string
}) => {
  const [filter, setFilter] = useState<CoverageFilter>('all')
  const [selectedFeature, setSelectedFeature] = useState<FeatureCoverageResponse | null>(null)

  // Filter features based on selection
  const getFilteredFeatures = () => {
    if (!coverageData) return []
    return coverageData.features.filter(feature => {
      if (filter === 'all') return true
      if (filter === 'covered') return feature.coverage_percentage === 100
      if (filter === 'uncovered') return feature.coverage_percentage < 100
      return true
    })
  }

  // Filter criteria within a feature
  const getFilteredCriteria = (criteria: CriterionResponse[]) => {
    if (filter === 'all') return criteria
    if (filter === 'covered') return criteria.filter(c => c.is_covered)
    if (filter === 'uncovered') return criteria.filter(c => !c.is_covered)
    return criteria
  }

  const filteredFeatures = getFilteredFeatures()

  if (coverageLoading) {
    return (
      <div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">📊 <span className="gradient-text-static">Spec Coverage</span></h2>
        <p className="text-slate-500 dark:text-zinc-400 mb-6">Acceptance criteria coverage analysis</p>
        <div className="space-y-4"><Skeleton className="h-32 w-full rounded-xl" /><Skeleton className="h-48 w-full rounded-xl" /></div>
      </div>
    )
  }

  if (!coverageData || coverageData.total_criteria === 0) {
    return (
      <div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">📊 <span className="gradient-text-static">Spec Coverage</span></h2>
        <p className="text-slate-500 dark:text-zinc-400 mb-6">Acceptance criteria coverage analysis</p>
        <div className="text-center py-20"><Icons.Coverage /><p className="text-slate-500 dark:text-zinc-400 mt-4">No acceptance criteria found</p></div>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">📊 <span className="gradient-text-static">Spec Coverage</span></h2>
          <p className="text-slate-500 dark:text-zinc-400 mt-1">{coverageData.features.length} features • {coverageData.total_criteria} criteria</p>
        </div>
        {/* Filter Buttons */}
        <div className="flex gap-2">
          <button 
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${filter === 'all' ? 'bg-violet-500 text-white' : 'bg-white dark:bg-zinc-900 text-slate-700 dark:text-white border border-slate-200 dark:border-zinc-700 hover:bg-slate-50 dark:hover:bg-zinc-800'}`}
          >
            All ({coverageData.total_criteria})
          </button>
          <button 
            onClick={() => setFilter('covered')}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${filter === 'covered' ? 'bg-emerald-500 text-white' : 'bg-white dark:bg-zinc-900 text-slate-700 dark:text-white border border-slate-200 dark:border-zinc-700 hover:bg-slate-50 dark:hover:bg-zinc-800'}`}
          >
            ✅ Covered ({coverageData.covered_criteria})
          </button>
          <button 
            onClick={() => setFilter('uncovered')}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${filter === 'uncovered' ? 'bg-red-500 text-white' : 'bg-white dark:bg-zinc-900 text-slate-700 dark:text-white border border-slate-200 dark:border-zinc-700 hover:bg-slate-50 dark:hover:bg-zinc-800'}`}
          >
            ❌ Uncovered ({coverageData.total_criteria - coverageData.covered_criteria})
          </button>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-6 mb-8">
        <div className={`relative overflow-hidden rounded-2xl bg-gradient-to-br ${getCoverageBg(coverageData.coverage_percentage)} p-6 text-white cursor-pointer hover:scale-[1.02] transition-all`} onClick={() => setFilter('all')}>
          <p className="text-5xl font-bold">{Math.round(coverageData.coverage_percentage)}%</p>
          <p className="text-white/80 mt-1">Overall Coverage</p>
        </div>
        <div className="rounded-2xl bg-white dark:bg-zinc-900 border border-slate-200/50 dark:border-zinc-800 p-6 cursor-pointer hover:scale-[1.02] transition-all hover:shadow-lg" onClick={() => setFilter('covered')}>
          <p className="text-4xl font-bold text-emerald-500">{coverageData.covered_criteria}</p>
          <p className="text-slate-500 dark:text-zinc-400 mt-1">Covered Criteria</p>
        </div>
        <div className="rounded-2xl bg-white dark:bg-zinc-900 border border-slate-200/50 dark:border-zinc-800 p-6 cursor-pointer hover:scale-[1.02] transition-all hover:shadow-lg" onClick={() => setFilter('uncovered')}>
          <p className="text-4xl font-bold text-red-500">{coverageData.total_criteria - coverageData.covered_criteria}</p>
          <p className="text-slate-500 dark:text-zinc-400 mt-1">Uncovered Criteria</p>
        </div>
      </div>

      {/* Feature Cards Grid */}
      {filteredFeatures.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-slate-500 dark:text-zinc-400">No features match the current filter</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredFeatures.map((feature) => {
            const coveredCount = feature.criteria.filter(c => c.is_covered).length
            const uncoveredCount = feature.criteria.length - coveredCount
            
            return (
              <div 
                key={feature.feature_name} 
                onClick={() => setSelectedFeature(feature)}
                className="rounded-2xl bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 overflow-hidden hover:shadow-xl transition-all duration-300 hover:scale-[1.02] cursor-pointer"
              >
                {/* Feature Header */}
                <div className={`bg-gradient-to-r ${getCoverageBg(feature.coverage_percentage)} px-5 py-4`}>
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-bold text-white capitalize">
                      {feature.feature_name.replace(/-/g, ' ')}
                    </h3>
                    <span className="text-2xl font-bold text-white">{Math.round(feature.coverage_percentage)}%</span>
                  </div>
                  <div className="mt-2 h-2 bg-white/30 rounded-full overflow-hidden">
                    <div className="h-full bg-white rounded-full" style={{ width: `${feature.coverage_percentage}%` }}></div>
                  </div>
                </div>
                
                {/* Criteria Summary */}
                <div className="p-4 space-y-3">
                  {/* Covered */}
                  <div className="flex items-center justify-between p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900">
                    <div className="flex items-center gap-2">
                      <span className="text-emerald-500"><Icons.Check /></span>
                      <span className="text-sm font-medium text-emerald-700 dark:text-emerald-400">Covered</span>
                    </div>
                    <span className="text-lg font-bold text-emerald-600 dark:text-emerald-400">{coveredCount}</span>
                  </div>
                  
                  {/* Uncovered */}
                  <div className="flex items-center justify-between p-3 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900">
                    <div className="flex items-center gap-2">
                      <span className="text-red-500"><Icons.X /></span>
                      <span className="text-sm font-medium text-red-700 dark:text-red-400">Uncovered</span>
                    </div>
                    <span className="text-lg font-bold text-red-600 dark:text-red-400">{uncoveredCount}</span>
                  </div>
                  
                  {/* Preview of criteria */}
                  <div className="pt-2 border-t border-slate-100 dark:border-zinc-800">
                    <p className="text-xs text-slate-500 dark:text-zinc-500 mb-2">Preview:</p>
                    {feature.criteria.slice(0, 2).map((c) => (
                      <p key={c.id} className="text-xs text-slate-600 dark:text-zinc-400 truncate mb-1">
                        {c.is_covered ? '✅' : '❌'} {c.text.slice(0, 50)}...
                      </p>
                    ))}
                    {feature.criteria.length > 2 && (
                      <p className="text-xs text-violet-500 dark:text-violet-400 mt-2">+{feature.criteria.length - 2} more criteria</p>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Feature Detail Modal */}
      {selectedFeature && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in" onClick={() => setSelectedFeature(null)}>
          <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden animate-scale-in border dark:border-zinc-800" onClick={(e) => e.stopPropagation()}>
            {/* Modal Header */}
            <div className={`px-6 py-4 bg-gradient-to-r ${getCoverageBg(selectedFeature.coverage_percentage)}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 text-white">
                  <span className="text-2xl">📊</span>
                  <div>
                    <h3 className="font-semibold capitalize text-lg">{selectedFeature.feature_name.replace(/-/g, ' ')}</h3>
                    <p className="text-sm text-white/70">{selectedFeature.criteria.length} acceptance criteria</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-3xl font-bold text-white">{Math.round(selectedFeature.coverage_percentage)}%</span>
                  <button onClick={() => setSelectedFeature(null)} className="p-2 hover:bg-white/20 rounded-lg transition-colors text-white"><Icons.X /></button>
                </div>
              </div>
            </div>
            
            {/* Modal Filter */}
            <div className="px-6 py-3 border-b border-slate-200 dark:border-zinc-800 bg-slate-50 dark:bg-black">
              <div className="flex gap-2">
                <button 
                  onClick={() => setFilter('all')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${filter === 'all' ? 'bg-violet-500 text-white' : 'bg-white dark:bg-zinc-900 text-slate-600 dark:text-zinc-400 border border-slate-200 dark:border-zinc-700'}`}
                >
                  All ({selectedFeature.criteria.length})
                </button>
                <button 
                  onClick={() => setFilter('covered')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${filter === 'covered' ? 'bg-emerald-500 text-white' : 'bg-white dark:bg-zinc-900 text-slate-600 dark:text-zinc-400 border border-slate-200 dark:border-zinc-700'}`}
                >
                  ✅ Covered ({selectedFeature.criteria.filter(c => c.is_covered).length})
                </button>
                <button 
                  onClick={() => setFilter('uncovered')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${filter === 'uncovered' ? 'bg-red-500 text-white' : 'bg-white dark:bg-zinc-900 text-slate-600 dark:text-zinc-400 border border-slate-200 dark:border-zinc-700'}`}
                >
                  ❌ Uncovered ({selectedFeature.criteria.filter(c => !c.is_covered).length})
                </button>
              </div>
            </div>
            
            {/* Criteria List */}
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              <div className="space-y-3">
                {getFilteredCriteria(selectedFeature.criteria).map((criterion, idx) => (
                  <div 
                    key={criterion.id} 
                    className={`p-4 rounded-xl border ${criterion.is_covered ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-900' : 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-900'}`}
                  >
                    <div className="flex items-start gap-3">
                      <span className={`mt-0.5 ${criterion.is_covered ? 'text-emerald-500' : 'text-red-500'}`}>
                        {criterion.is_covered ? <Icons.Check /> : <Icons.X />}
                      </span>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-mono bg-slate-200 dark:bg-zinc-800 text-slate-600 dark:text-zinc-400 px-2 py-0.5 rounded">{criterion.number || `#${idx + 1}`}</span>
                          <span className={`text-xs font-medium ${criterion.is_covered ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                            {criterion.is_covered ? 'COVERED' : 'UNCOVERED'}
                          </span>
                        </div>
                        <p className="text-sm text-slate-800 dark:text-white">{criterion.text}</p>
                        {criterion.is_covered && criterion.test_file && (
                          <div className="mt-2 p-2 bg-white dark:bg-black rounded-lg border border-slate-200 dark:border-zinc-800">
                            <p className="text-xs text-slate-500 dark:text-zinc-500">Tested by:</p>
                            <p className="text-xs font-mono text-violet-600 dark:text-violet-400">{criterion.test_file}</p>
                            {criterion.test_name && <p className="text-xs font-mono text-slate-600 dark:text-zinc-400">{criterion.test_name}</p>}
                          </div>
                        )}
                        {!criterion.is_covered && (
                          <div className="mt-2 p-2 bg-amber-50 dark:bg-amber-950/30 rounded-lg border border-amber-200 dark:border-amber-900">
                            <p className="text-xs text-amber-700 dark:text-amber-400">💡 This criterion needs a test. Consider adding one to improve coverage.</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {getFilteredCriteria(selectedFeature.criteria).length === 0 && (
                  <div className="text-center py-8">
                    <p className="text-slate-500 dark:text-zinc-400">No criteria match the current filter</p>
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

// Guidelines View Component
const GuidelinesView = () => {
  const [filter, setFilter] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedGuideline, setSelectedGuideline] = useState<GuidelineResponse | null>(null)
  const [conversionResult, setConversionResult] = useState<ConversionResultResponse | null>(null)

  const { data: guidelinesData, isLoading } = useQuery({
    queryKey: ['guidelines', filter, searchQuery],
    queryFn: () => guidelinesApi.getGuidelines({ source: filter || undefined, q: searchQuery || undefined }),
    staleTime: 60000,
  })

  const [convertFormat, setConvertFormat] = useState<string | null>(null)

  const convertMutation = useMutation({
    mutationFn: ({ id, format }: { id: string; format: string }) => guidelinesApi.convertGuideline(id, format, true),
    onSuccess: (data) => setConversionResult(data),
  })

  const sourceColors: Record<string, { bg: string; text: string; icon: string }> = {
    claude: { bg: 'from-orange-500 to-amber-500', text: 'text-orange-600 dark:text-orange-400', icon: '🤖' },
    cursor: { bg: 'from-blue-500 to-cyan-500', text: 'text-blue-600 dark:text-blue-400', icon: '🖱️' },
    steering: { bg: 'from-violet-500 to-purple-500', text: 'text-violet-600 dark:text-violet-400', icon: '🎯' },
    agents: { bg: 'from-green-500 to-emerald-500', text: 'text-green-600 dark:text-green-400', icon: '🤝' },
    sample: { bg: 'from-slate-500 to-zinc-500', text: 'text-slate-600 dark:text-slate-400', icon: '📝' },
  }

  if (isLoading) {
    return (
      <div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">📜 <span className="gradient-text-static">Coding Guidelines</span></h2>
        <p className="text-slate-500 dark:text-zinc-400 mb-6">Team coding standards and rules</p>
        <div className="space-y-4"><Skeleton className="h-32 w-full rounded-xl" /><Skeleton className="h-48 w-full rounded-xl" /></div>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">📜 <span className="gradient-text-static">Coding Guidelines</span></h2>
          <p className="text-slate-500 dark:text-zinc-400 mt-1">{guidelinesData?.total_count || 0} guidelines from {Object.keys(guidelinesData?.counts_by_source || {}).length} sources</p>
        </div>
        <div className="flex gap-2">
          <input type="text" placeholder="Search guidelines..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
            className="px-4 py-2 rounded-xl bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
        </div>
      </div>

      {/* Filter Buttons */}
      <div className="flex gap-2 mb-6">
        <button onClick={() => setFilter(null)} className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${!filter ? 'bg-violet-500 text-white' : 'bg-white dark:bg-zinc-900 text-slate-700 dark:text-white border border-slate-200 dark:border-zinc-700'}`}>
          All ({guidelinesData?.total_count || 0})
        </button>
        {Object.entries(guidelinesData?.counts_by_source || {}).map(([source, count]) => (
          <button key={source} onClick={() => setFilter(filter === source ? null : source)}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all flex items-center gap-2 ${filter === source ? 'bg-violet-500 text-white' : 'bg-white dark:bg-zinc-900 text-slate-700 dark:text-white border border-slate-200 dark:border-zinc-700'}`}>
            <span>{sourceColors[source]?.icon || '📄'}</span>
            <span className="capitalize">{source}</span>
            <span className="bg-slate-200 dark:bg-zinc-700 px-2 py-0.5 rounded-full text-xs">{count}</span>
          </button>
        ))}
      </div>

      {/* Guidelines Grid */}
      {!guidelinesData?.guidelines.length ? (
        <div className="text-center py-20"><Icons.Document /><p className="text-slate-500 dark:text-zinc-400 mt-4">No guidelines found</p></div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {guidelinesData.guidelines.map((guideline) => {
            const colors = sourceColors[guideline.source_type] || sourceColors.sample
            return (
              <div key={guideline.id} onClick={() => setSelectedGuideline(guideline)}
                className="rounded-2xl bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 overflow-hidden hover:shadow-xl transition-all duration-300 hover:scale-[1.02] cursor-pointer">
                <div className={`bg-gradient-to-r ${colors.bg} px-5 py-4`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{colors.icon}</span>
                      <span className="text-white font-medium capitalize">{guideline.source_type}</span>
                    </div>
                    {guideline.is_sample && <span className="text-xs bg-white/20 text-white px-2 py-1 rounded-full">Sample</span>}
                  </div>
                </div>
                <div className="p-4">
                  <h3 className="font-semibold text-slate-900 dark:text-white mb-2">{guideline.title}</h3>
                  <p className="text-sm text-slate-600 dark:text-zinc-400 line-clamp-3">{stripMarkdown(guideline.content).slice(0, 150)}...</p>
                  {guideline.file_pattern && (
                    <div className="mt-3 text-xs text-slate-500 dark:text-zinc-500 font-mono bg-slate-100 dark:bg-zinc-800 px-2 py-1 rounded inline-block">
                      {guideline.file_pattern}
                    </div>
                  )}
                  <div className="flex flex-wrap gap-1 mt-3">
                    {guideline.tags.slice(0, 3).map((tag) => (
                      <span key={tag} className="text-xs bg-violet-100 dark:bg-violet-950 text-violet-700 dark:text-violet-400 px-2 py-0.5 rounded-full">{tag}</span>
                    ))}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Guideline Detail Modal */}
      {selectedGuideline && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in" onClick={() => setSelectedGuideline(null)}>
          <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl max-w-3xl w-full max-h-[85vh] overflow-hidden animate-scale-in border dark:border-zinc-800" onClick={(e) => e.stopPropagation()}>
            <div className={`bg-gradient-to-r ${sourceColors[selectedGuideline.source_type]?.bg || 'from-slate-500 to-zinc-500'} px-6 py-4`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 text-white">
                  <span className="text-2xl">{sourceColors[selectedGuideline.source_type]?.icon || '📄'}</span>
                  <div>
                    <h3 className="font-semibold">{selectedGuideline.title}</h3>
                    <p className="text-sm text-white/70">{selectedGuideline.source_file}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <button onClick={(e) => { e.stopPropagation(); setConvertFormat(convertFormat ? null : selectedGuideline.id) }}
                      className="px-3 py-1.5 bg-white/20 hover:bg-white/30 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-1">
                      Convert to...
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                    </button>
                    {convertFormat === selectedGuideline.id && (
                      <div className="absolute right-0 mt-1 w-48 bg-white dark:bg-zinc-800 rounded-lg shadow-xl border dark:border-zinc-700 py-1 z-10">
                        <button onClick={(e) => { e.stopPropagation(); convertMutation.mutate({ id: selectedGuideline.id, format: 'steering' }); setConvertFormat(null) }}
                          className="w-full px-4 py-2 text-left text-sm text-slate-700 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-zinc-700 flex items-center gap-2">
                          <span>🎯</span> Kiro Steering
                        </button>
                        <button onClick={(e) => { e.stopPropagation(); convertMutation.mutate({ id: selectedGuideline.id, format: 'claude' }); setConvertFormat(null) }}
                          className="w-full px-4 py-2 text-left text-sm text-slate-700 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-zinc-700 flex items-center gap-2">
                          <span>🤖</span> CLAUDE.md
                        </button>
                        <button onClick={(e) => { e.stopPropagation(); convertMutation.mutate({ id: selectedGuideline.id, format: 'cursor' }); setConvertFormat(null) }}
                          className="w-full px-4 py-2 text-left text-sm text-slate-700 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-zinc-700 flex items-center gap-2">
                          <span>🖱️</span> .cursorrules
                        </button>
                      </div>
                    )}
                  </div>
                  <button onClick={() => setSelectedGuideline(null)} className="p-2 hover:bg-white/20 rounded-lg transition-colors text-white"><Icons.X /></button>
                </div>
              </div>
            </div>
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              <div className="text-slate-700 dark:text-zinc-300 whitespace-pre-wrap font-mono text-sm">{selectedGuideline.content}</div>
            </div>
          </div>
        </div>
      )}

      {/* Conversion Result Modal */}
      {conversionResult && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in" onClick={() => setConversionResult(null)}>
          <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl max-w-3xl w-full max-h-[85vh] overflow-hidden animate-scale-in border dark:border-zinc-800" onClick={(e) => e.stopPropagation()}>
            <div className="bg-gradient-to-r from-emerald-500 to-green-500 px-6 py-4">
              <div className="flex items-center justify-between text-white">
                <div className="flex items-center gap-3">
                  <Icons.Check />
                  <div>
                    <h3 className="font-semibold">Conversion Preview</h3>
                    <p className="text-sm text-white/70">{conversionResult.filename}</p>
                  </div>
                </div>
                <button onClick={() => setConversionResult(null)} className="p-2 hover:bg-white/20 rounded-lg transition-colors"><Icons.X /></button>
              </div>
            </div>
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              <div className="bg-slate-50 dark:bg-black rounded-xl p-4 border dark:border-zinc-800">
                <pre className="text-sm text-slate-700 dark:text-zinc-300 whitespace-pre-wrap font-mono">{conversionResult.content}</pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function App() {
  const queryClient = useQueryClient()
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('darkMode') === 'true' || window.matchMedia('(prefers-color-scheme: dark)').matches)
  const [activeView, setActiveView] = useState<ViewType>('home')

  const [searchQuery, setSearchQuery] = useState('')
  const [activeSearch, setActiveSearch] = useState('')
  const [selectedBlock, setSelectedBlock] = useState<BlockDetail | null>(null)
  const [selectedSession, setSelectedSession] = useState<SessionResponse | null>(null)
  const [selectedSpecFile, setSelectedSpecFile] = useState<SpecFileResponse | null>(null)
  const [autoRefresh] = useState(() => localStorage.getItem('autoRefresh') !== 'false')
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)
  const [actionResult, setActionResult] = useState<ActionResultResponse | null>(null)

  const handleWebSocketRefresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['blocks'] })
    queryClient.invalidateQueries({ queryKey: ['stats'] })
    queryClient.invalidateQueries({ queryKey: ['health'] })
    showToast('Specs updated', 'success')
  }, [queryClient])

  const { isConnected } = useWebSocket({ enabled: autoRefresh, onRefresh: handleWebSocketRefresh })

  useEffect(() => { document.documentElement.classList.toggle('dark', darkMode); localStorage.setItem('darkMode', String(darkMode)) }, [darkMode])
  const showToast = (message: string, type: 'success' | 'error') => { setToast({ message, type }); setTimeout(() => setToast(null), 3000) }

  // Queries - essential data loads immediately
  const { data: blocksData, isLoading } = useQuery({ queryKey: ['blocks'], queryFn: () => api.getBlocks() })
  const { data: statsData } = useQuery({ queryKey: ['stats'], queryFn: api.getStats })
  const { data: searchData, isLoading: searchLoading } = useQuery({ queryKey: ['search', activeSearch], queryFn: () => api.search(activeSearch, 20), enabled: activeSearch.length > 0 })
  useQuery({ queryKey: ['pinned'], queryFn: api.getPinned })
  const { data: kiroConfigData, isLoading: kiroConfigLoading } = useQuery({ queryKey: ['kiroConfig'], queryFn: kiroConfigApi.getConfig })
  const { data: healthData, isLoading: healthLoading } = useQuery({ queryKey: ['health'], queryFn: apiExtended.getHealthScore, staleTime: 300000 })
  
  // Lazy queries - only fetch when needed (home, coverage, or graph view)
  const shouldFetchCoverage = activeView === 'home' || activeView === 'coverage'
  const shouldFetchGraph = activeView === 'home' || activeView === 'graph'
  const shouldFetchSessions = activeView === 'home' || activeView === 'sessions'
  
  const { data: coverageData, isLoading: coverageLoading } = useQuery({ 
    queryKey: ['coverage'], 
    queryFn: api.getCoverage, 
    staleTime: 300000,
    enabled: shouldFetchCoverage 
  })
  const { data: graphData, isLoading: graphLoading } = useQuery({ 
    queryKey: ['graph'], 
    queryFn: () => apiExtended.getImpactGraph(), 
    staleTime: 300000,
    enabled: shouldFetchGraph 
  })
  const { data: sessionsData, isLoading: sessionsLoading } = useQuery({ 
    queryKey: ['sessions'], 
    queryFn: () => api.getSessions(20, false), 
    staleTime: 300000,
    enabled: shouldFetchSessions 
  })
  useQuery({ queryKey: ['powers'], queryFn: api.getPowers })

  const exportMutation = useMutation({ mutationFn: api.exportPack, onSuccess: (d) => showToast(d.message, d.success ? 'success' : 'error'), onError: () => showToast('Export failed', 'error') })
  const scanMutation = useMutation({ mutationFn: apiExtended.scanAction, onSuccess: (d) => { setActionResult(d); queryClient.invalidateQueries() } })
  const buildMutation = useMutation({ mutationFn: apiExtended.buildAction, onSuccess: (d) => { setActionResult(d); queryClient.invalidateQueries() } })
  const validateMutation = useMutation({ mutationFn: apiExtended.validateAction, onSuccess: (d) => setActionResult(d) })
  const coverageMutation = useMutation({ mutationFn: apiExtended.coverageAction, onSuccess: (d) => setActionResult(d) })

  const handleBlockClick = async (block: BlockSummary) => { 
    try {
      const detail = await api.getBlock(block.id)
      setSelectedBlock(detail)
    } catch (error) {
      console.error('Failed to load block:', error)
      showToast('Failed to load specification', 'error')
    }
  }
  const handleSpecFileClick = async (featureName: string, fileType: string) => {
    try {
      const specFile = await api.getSpecFile(featureName, fileType)
      setSelectedSpecFile(specFile)
    } catch (error) {
      console.error('Failed to load spec file:', error)
      showToast('Failed to load specification file', 'error')
    }
  }
  const handleSearch = (e: React.FormEvent) => { e.preventDefault(); setActiveSearch(searchQuery); setActiveView('search') }
  const handleSessionClick = async (session: SessionResponse) => { const detail = await api.getSession(session.session_id); setSelectedSession(detail) }

  const getTypeStyle = (type: string) => typeConfig[type] || typeConfig.knowledge
  const getCoverageColor = (pct: number) => pct >= 80 ? 'text-emerald-500' : pct >= 50 ? 'text-amber-500' : 'text-red-500'
  const getCoverageBg = (pct: number) => pct >= 80 ? 'from-emerald-500 to-green-500' : pct >= 50 ? 'from-amber-500 to-orange-500' : 'from-red-500 to-rose-500'

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 dark:from-black dark:via-black dark:to-black">
      {toast && <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-xl shadow-lg backdrop-blur-sm animate-slide-in ${toast.type === 'success' ? 'bg-emerald-500/90 text-white' : 'bg-red-500/90 text-white'}`}>{toast.message}</div>}
      <ActionResultModal result={actionResult} onClose={() => setActionResult(null)} />

      {/* Header */}
      <header className="sticky top-0 z-40 backdrop-blur-xl bg-white/80 dark:bg-black/90 border-b border-slate-200/50 dark:border-zinc-800">
        <div className="flex items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => setActiveView('home')}>
            <img src="/logo.png" alt="SpecMem" className="w-10 h-10 rounded-xl shadow-lg shadow-violet-500/30" />
            <div>
              <h1 className="text-xl brand-logo gradient-text-static tracking-tight">SpecMem</h1>
              <p className="text-xs text-slate-500 dark:text-zinc-400">Living Documentation</p>
            </div>
          </div>

          <form onSubmit={handleSearch} className="flex-1 max-w-xl mx-8">
            <div className="relative">
              <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search specifications..."
                className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-100 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-700 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all" />
              <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 dark:text-zinc-500"><Icons.Search /></div>
            </div>
          </form>

          <div className="flex items-center gap-3">
            {isConnected && <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400"><span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>Live</span>}
            <button onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-violet-500 to-purple-600 text-white font-medium shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 transition-all disabled:opacity-50 text-sm">
              <Icons.Download />{exportMutation.isPending ? 'Exporting...' : 'Export'}
            </button>
            <button onClick={() => setDarkMode(!darkMode)} className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-zinc-800 transition-colors text-slate-600 dark:text-white">{darkMode ? <Icons.Sun /> : <Icons.Moon />}</button>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-56 flex-shrink-0 border-r border-slate-200/50 dark:border-zinc-800 bg-white/50 dark:bg-black backdrop-blur-sm min-h-[calc(100vh-57px)]">
          <nav className="p-3 space-y-1">
            {[
              { id: 'home', label: 'Dashboard', icon: <Icons.Home /> },
              { id: 'specs', label: 'Specifications', icon: <Icons.Document />, count: blocksData?.total },
              { id: 'graph', label: 'Impact Graph', icon: <Icons.Graph /> },
              { id: 'coverage', label: 'Coverage', icon: <Icons.Coverage />, badge: coverageData ? `${Math.round(coverageData.coverage_percentage)}%` : undefined },
              { id: 'config', label: 'Kiro Config', icon: <Icons.Cog /> },
              { id: 'guidelines', label: 'Guidelines', icon: <Icons.Document /> },
              { id: 'sessions', label: 'Sessions', icon: <Icons.Chat />, count: sessionsData?.total },
              { id: 'analytics', label: 'Analytics', icon: <Icons.Chart /> },
            ].map((item) => (
              <button key={item.id} onClick={() => setActiveView(item.id as ViewType)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm transition-all ${activeView === item.id ? 'bg-violet-500/20 text-violet-400 font-medium' : 'text-slate-600 dark:text-zinc-400 hover:bg-slate-100 dark:hover:bg-zinc-900 dark:hover:text-white'}`}>
                {item.icon}
                <span className="flex-1 text-left">{item.label}</span>
                {item.count !== undefined && <span className="text-xs bg-slate-200 dark:bg-zinc-800 text-slate-600 dark:text-zinc-300 px-2 py-0.5 rounded-full">{item.count}</span>}
                {item.badge && <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${getCoverageColor(coverageData?.coverage_percentage || 0)} bg-slate-100 dark:bg-zinc-800`}>{item.badge}</span>}
              </button>
            ))}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6 overflow-auto">

          {/* HOME / DASHBOARD VIEW */}
          {activeView === 'home' && (
            <div className="space-y-8">
              {/* Hero Section - Clean design for light/dark mode */}
              <div className="relative rounded-2xl overflow-hidden">
                {/* Subtle gradient background */}
                <div className="absolute inset-0 bg-gradient-to-br from-violet-50 via-white to-purple-50 dark:from-zinc-900 dark:via-black dark:to-zinc-900"></div>
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-violet-100/50 via-transparent to-transparent dark:from-violet-900/30 dark:via-transparent dark:to-transparent"></div>
                
                <div className="relative border border-slate-200/80 dark:border-zinc-800 rounded-2xl p-8">
                  <div className="flex items-center gap-8">
                    <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 p-1 shadow-xl shadow-violet-500/30 flex-shrink-0">
                      <div className="w-full h-full rounded-xl bg-white dark:bg-black flex items-center justify-center overflow-hidden">
                        <img src="/logo.png" alt="SpecMem" className="w-20 h-20 object-contain" onError={(e) => { e.currentTarget.style.display = 'none' }} />
                      </div>
                    </div>
                    <div className="flex-1">
                      <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">Welcome to <span className="gradient-text-static">SpecMem</span></h1>
                      <p className="text-slate-600 dark:text-zinc-400 text-lg mb-4">Unified Agent Experience & Cognitive Memory for AI Coding Agents</p>
                      <div className="flex gap-3">
                        <button onClick={() => scanMutation.mutate()} disabled={scanMutation.isPending} className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-violet-500 to-purple-600 text-white rounded-xl font-semibold hover:from-violet-600 hover:to-purple-700 transition-all shadow-lg shadow-violet-500/25">
                          {scanMutation.isPending ? <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <Icons.Search />} Scan Workspace
                        </button>
                        <button onClick={() => setActiveView('specs')} className="flex items-center gap-2 px-5 py-2.5 bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-white rounded-xl font-semibold hover:bg-slate-200 dark:hover:bg-zinc-700 transition-colors">
                          <Icons.Document /> Browse Specs
                        </button>
                      </div>
                    </div>
                    {healthData && (
                      <div className="text-center flex-shrink-0">
                        <HealthScoreCircle score={healthData.overall_score} grade={healthData.letter_grade} color={healthData.grade_color} />
                        <p className="text-slate-500 dark:text-zinc-400 text-sm mt-2">Health Score</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Stats Row */}
              <div className="grid grid-cols-4 gap-4">
                {[
                  { label: 'Total Specs', value: statsData?.total_blocks || 0, icon: '📊', gradient: 'from-violet-500 to-purple-500', onClick: () => setActiveView('specs') },
                  { label: 'Features', value: healthData?.feature_count || 0, icon: '🎯', gradient: 'from-emerald-500 to-teal-500', onClick: () => setActiveView('specs') },
                  { label: 'Coverage', value: `${Math.round(coverageData?.coverage_percentage || 0)}%`, icon: '✅', gradient: 'from-amber-500 to-orange-500', onClick: () => setActiveView('coverage') },
                  { label: 'Graph Nodes', value: graphData?.stats.total_nodes || 0, icon: '🔗', gradient: 'from-pink-500 to-rose-500', onClick: () => setActiveView('graph') },
                ].map((stat) => (
                  <div key={stat.label} onClick={stat.onClick} className="relative overflow-hidden rounded-2xl bg-white dark:bg-zinc-900 border border-slate-200/50 dark:border-zinc-800 p-5 cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-300">
                    <div className={`absolute top-0 right-0 w-24 h-24 bg-gradient-to-br ${stat.gradient} opacity-10 dark:opacity-20 rounded-full -translate-y-8 translate-x-8`}></div>
                    <span className="text-3xl">{stat.icon}</span>
                    <p className="text-3xl font-bold text-slate-900 dark:text-white mt-2">{typeof stat.value === 'number' ? <AnimatedCounter value={stat.value} /> : stat.value}</p>
                    <p className="text-sm text-slate-500 dark:text-zinc-400">{stat.label}</p>
                  </div>
                ))}
              </div>

              {/* Quick Actions */}
              <div>
                <h3 className="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">Quick Actions</h3>
                <div className="flex flex-wrap gap-3">
                  <QuickActionButton icon={<Icons.Search />} label="Scan" onClick={() => scanMutation.mutate()} loading={scanMutation.isPending} />
                  <QuickActionButton icon={<Icons.Download />} label="Build Pack" onClick={() => buildMutation.mutate()} loading={buildMutation.isPending} />
                  <QuickActionButton icon={<Icons.Check />} label="Validate" onClick={() => validateMutation.mutate()} loading={validateMutation.isPending} />
                  <QuickActionButton icon={<Icons.Coverage />} label="Coverage" onClick={() => coverageMutation.mutate()} loading={coverageMutation.isPending} />
                </div>
              </div>

              {/* Dashboard Grid */}
              <div className="grid grid-cols-3 gap-6">
                {/* Health Breakdown */}
                <DashboardCard title="Health Breakdown" icon={<Icons.Heart />} gradient="from-violet-500 to-purple-500">
                  {healthLoading ? <Skeleton className="h-32" /> : healthData ? (
                    <div className="space-y-3">
                      {healthData.breakdown.slice(0, 4).map(item => (
                        <div key={item.category}>
                          <div className="flex justify-between text-sm mb-1">
                            <span className="text-slate-600 dark:text-slate-400 capitalize">{item.category}</span>
                            <span className="font-medium text-slate-900 dark:text-white">{Math.round(item.score)}%</span>
                          </div>
                          <div className="h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                            <div className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500 rounded-full transition-all duration-1000" style={{ width: `${item.score}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : <p className="text-slate-500">No health data</p>}
                </DashboardCard>

                {/* Spec Types */}
                <DashboardCard title="Spec Types" icon={<Icons.Document />} gradient="from-emerald-500 to-teal-500" onClick={() => setActiveView('specs')}>
                  {statsData ? (
                    <div className="space-y-2">
                      {Object.entries(statsData.by_type).slice(0, 5).map(([type, count]) => (
                        <div key={type} className="flex items-center justify-between py-1">
                          <span className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                            <span>{typeConfig[type]?.icon || '📄'}</span>
                            <span className="capitalize">{type}</span>
                          </span>
                          <span className="text-sm font-medium text-slate-900 dark:text-white bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded-full">{count}</span>
                        </div>
                      ))}
                    </div>
                  ) : <Skeleton className="h-32" />}
                </DashboardCard>

                {/* Coverage Summary */}
                <DashboardCard title="Coverage Summary" icon={<Icons.Coverage />} gradient="from-amber-500 to-orange-500" onClick={() => setActiveView('coverage')}>
                  {coverageLoading ? <Skeleton className="h-32" /> : coverageData ? (
                    <div className="text-center">
                      <div className={`text-5xl font-bold ${getCoverageColor(coverageData.coverage_percentage)}`}>{Math.round(coverageData.coverage_percentage)}%</div>
                      <p className="text-slate-500 dark:text-zinc-400 mt-2">{coverageData.covered_criteria} / {coverageData.total_criteria} criteria covered</p>
                      <div className="mt-4 h-3 bg-slate-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                        <div className={`h-full bg-gradient-to-r ${getCoverageBg(coverageData.coverage_percentage)} rounded-full`} style={{ width: `${coverageData.coverage_percentage}%` }}></div>
                      </div>
                    </div>
                  ) : <p className="text-zinc-500 text-center py-8">No coverage data</p>}
                </DashboardCard>

                {/* Impact Graph Preview */}
                <DashboardCard title="Impact Graph" icon={<Icons.Graph />} gradient="from-pink-500 to-rose-500" onClick={() => setActiveView('graph')} className="col-span-2">
                  {graphLoading ? <Skeleton className="h-48" /> : graphData?.nodes.length ? (
                    <div className="flex items-center justify-between">
                      <div className="flex gap-8">
                        {[{ type: 'spec', color: 'bg-violet-500' }, { type: 'code', color: 'bg-emerald-500' }, { type: 'test', color: 'bg-amber-500' }].map(item => (
                          <div key={item.type} className="text-center">
                            <div className={`w-12 h-12 ${item.color} rounded-xl flex items-center justify-center text-white text-xl font-bold mx-auto mb-2`}>
                              {graphData.stats.nodes_by_type?.[item.type] || 0}
                            </div>
                            <span className="text-sm text-slate-500 capitalize">{item.type}s</span>
                          </div>
                        ))}
                      </div>
                      <div className="text-right">
                        <p className="text-3xl font-bold text-slate-900 dark:text-white">{graphData.stats.total_edges}</p>
                        <p className="text-sm text-slate-500">Connections</p>
                      </div>
                    </div>
                  ) : <p className="text-slate-500 text-center py-8">Run scan to build graph</p>}
                </DashboardCard>

                {/* Kiro Config Summary */}
                <DashboardCard title="Kiro Config" icon={<Icons.Cog />} gradient="from-cyan-500 to-blue-500" onClick={() => setActiveView('config')}>
                  {kiroConfigLoading ? <Skeleton className="h-32" /> : kiroConfigData ? (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between"><span className="text-slate-500 dark:text-zinc-400">MCP Servers</span><span className="font-bold text-violet-500">{kiroConfigData.enabled_servers}</span></div>
                      <div className="flex items-center justify-between"><span className="text-slate-500 dark:text-zinc-400">Active Hooks</span><span className="font-bold text-emerald-500">{kiroConfigData.active_hooks}</span></div>
                      <div className="flex items-center justify-between"><span className="text-slate-500 dark:text-zinc-400">Steering Files</span><span className="font-bold text-amber-500">{kiroConfigData.steering_files.length}</span></div>
                    </div>
                  ) : <p className="text-zinc-500">No config found</p>}
                </DashboardCard>
              </div>
            </div>
          )}


          {/* SPECS VIEW - Feature Cards Grid */}
          {activeView === 'specs' && (
            <div>
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Feature <span className="gradient-text-static">Specifications</span></h2>
                  <p className="text-slate-500 dark:text-zinc-400 mt-1">
                    {(() => {
                      const features = new Set(blocksData?.blocks.map(b => b.source.split('/').slice(-2, -1)[0]) || [])
                      return `${features.size} features`
                    })()}
                  </p>
                </div>
              </div>
              {isLoading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {[1,2,3,4,5,6].map(i => <Skeleton key={i} className="h-64 w-full rounded-2xl" />)}
                </div>
              ) : !blocksData?.blocks.length ? (
                <div className="text-center py-20"><p className="text-slate-500 dark:text-zinc-400">No specifications found</p></div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {(() => {
                    // Group blocks by feature (folder name)
                    const featureMap = new Map<string, { requirements: BlockSummary | null, design: BlockSummary | null, tasks: BlockSummary | null }>()
                    
                    blocksData.blocks.forEach(block => {
                      // Extract feature name from source path (e.g., ".kiro/specs/feature-name/requirements.md")
                      const parts = block.source.split('/')
                      const featureName = parts[parts.length - 2] || 'unknown'
                      const fileName = parts[parts.length - 1]?.replace('.md', '') || ''
                      
                      if (!featureMap.has(featureName)) {
                        featureMap.set(featureName, { requirements: null, design: null, tasks: null })
                      }
                      
                      const feature = featureMap.get(featureName)!
                      if (fileName === 'requirements' || block.type === 'requirement') {
                        feature.requirements = block
                      } else if (fileName === 'design' || block.type === 'design') {
                        feature.design = block
                      } else if (fileName === 'tasks' || block.type === 'task') {
                        feature.tasks = block
                      }
                    })
                    
                    return Array.from(featureMap.entries()).map(([featureName, specs]) => (
                      <div key={featureName} className="rounded-2xl bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 overflow-hidden hover:shadow-xl transition-all duration-300 hover:scale-[1.02]">
                        {/* Feature Header */}
                        <div className="bg-gradient-to-r from-violet-500 to-purple-600 px-5 py-4">
                          <h3 className="text-lg font-bold text-white capitalize">
                            {featureName.replace(/-/g, ' ')}
                          </h3>
                          <p className="text-violet-200 text-sm mt-1">
                            {[specs.requirements && 'Requirements', specs.design && 'Design', specs.tasks && 'Tasks'].filter(Boolean).join(' • ')}
                          </p>
                        </div>
                        
                        {/* Spec Documents */}
                        <div className="p-4 space-y-3">
                          {/* Requirements */}
                          {specs.requirements && (
                            <button 
                              onClick={() => handleSpecFileClick(featureName, 'requirements')}
                              className="w-full text-left p-3 rounded-xl bg-blue-50 dark:bg-blue-950/50 border border-blue-200 dark:border-blue-900 hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors group"
                            >
                              <div className="flex items-center gap-3">
                                <span className="text-2xl">📋</span>
                                <div className="flex-1 min-w-0">
                                  <div className="font-medium text-blue-700 dark:text-blue-400">Requirements</div>
                                  <p className="text-xs text-blue-600/70 dark:text-blue-400/60 truncate mt-0.5">
                                    {stripMarkdown(specs.requirements.text_preview).slice(0, 60)}...
                                  </p>
                                </div>
                                <Icons.ChevronRight />
                              </div>
                            </button>
                          )}
                          
                          {/* Design */}
                          {specs.design && (
                            <button 
                              onClick={() => handleSpecFileClick(featureName, 'design')}
                              className="w-full text-left p-3 rounded-xl bg-purple-50 dark:bg-purple-950/50 border border-purple-200 dark:border-purple-900 hover:bg-purple-100 dark:hover:bg-purple-900/40 transition-colors group"
                            >
                              <div className="flex items-center gap-3">
                                <span className="text-2xl">🎨</span>
                                <div className="flex-1 min-w-0">
                                  <div className="font-medium text-purple-700 dark:text-purple-400">Design</div>
                                  <p className="text-xs text-purple-600/70 dark:text-purple-400/60 truncate mt-0.5">
                                    {stripMarkdown(specs.design.text_preview).slice(0, 60)}...
                                  </p>
                                </div>
                                <Icons.ChevronRight />
                              </div>
                            </button>
                          )}
                          
                          {/* Tasks */}
                          {specs.tasks && (
                            <button 
                              onClick={() => handleSpecFileClick(featureName, 'tasks')}
                              className="w-full text-left p-3 rounded-xl bg-green-50 dark:bg-green-950/50 border border-green-200 dark:border-green-900 hover:bg-green-100 dark:hover:bg-green-900/40 transition-colors group"
                            >
                              <div className="flex items-center gap-3">
                                <span className="text-2xl">✅</span>
                                <div className="flex-1 min-w-0">
                                  <div className="font-medium text-green-700 dark:text-green-400">Tasks</div>
                                  <p className="text-xs text-green-600/70 dark:text-green-400/60 truncate mt-0.5">
                                    {stripMarkdown(specs.tasks.text_preview).slice(0, 60)}...
                                  </p>
                                </div>
                                <Icons.ChevronRight />
                              </div>
                            </button>
                          )}
                          
                          {/* Empty state for missing docs */}
                          {!specs.requirements && !specs.design && !specs.tasks && (
                            <p className="text-zinc-500 text-sm text-center py-4">No spec documents found</p>
                          )}
                        </div>
                      </div>
                    ))
                  })()}
                </div>
              )}
            </div>
          )}

          {/* GRAPH VIEW */}
          {activeView === 'graph' && (
            <div>
              <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">🔗 <span className="gradient-text-static">Impact Graph</span></h2>
              <p className="text-slate-500 dark:text-zinc-400 mb-6">Visualize relationships between specs, code, and tests</p>
              {graphLoading ? <Skeleton className="h-[500px] w-full rounded-xl" /> : (
                <div className="rounded-2xl bg-white dark:bg-zinc-900 border border-slate-200/50 dark:border-zinc-800 p-6">
                  <ForceGraph data={graphData} onNodeClick={(node) => showToast(`Selected: ${node.label}`, 'success')} />
                </div>
              )}
            </div>
          )}

          {/* SEARCH VIEW */}
          {activeView === 'search' && (
            <div>
              <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">Search Results</h2>
              <p className="text-slate-500 dark:text-slate-400 mb-6">{activeSearch ? `Results for "${activeSearch}"` : 'Enter a query to search'}</p>
              {searchLoading ? (
                <div className="space-y-4">{[1,2,3].map(i => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}</div>
              ) : !activeSearch ? (
                <div className="text-center py-20 text-slate-500"><p>Use the search bar above</p></div>
              ) : searchData?.results.length === 0 ? (
                <div className="text-center py-20 text-slate-500"><p>No results found</p></div>
              ) : (
                <div className="space-y-4">
                  {searchData?.results.map((result, idx) => {
                    const style = getTypeStyle(result.block.type)
                    return (
                      <div key={result.block.id} onClick={() => handleBlockClick(result.block)} className={`rounded-xl border ${style.bg} p-5 cursor-pointer hover:shadow-lg transition-all`}>
                        <div className="flex items-center gap-3 mb-3">
                          <span className="w-8 h-8 rounded-lg bg-violet-100 dark:bg-violet-900/50 flex items-center justify-center text-violet-600 dark:text-violet-400 font-bold text-sm">#{idx + 1}</span>
                          <span className={`text-xs font-semibold uppercase ${style.color}`}>{result.block.type}</span>
                          <span className="text-xs text-slate-500 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-full">{(result.score * 100).toFixed(0)}%</span>
                        </div>
                        <p className="text-slate-800 dark:text-slate-200">{stripMarkdown(result.block.text_preview)}</p>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* COVERAGE VIEW */}
          {activeView === 'coverage' && (
            <CoverageView 
              coverageData={coverageData} 
              coverageLoading={coverageLoading}
              getCoverageBg={getCoverageBg}
            />
          )}


          {/* SESSIONS VIEW */}
          {activeView === 'sessions' && (
            <div>
              <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">💬 <span className="gradient-text-static">Kiro Sessions</span></h2>
              <p className="text-slate-500 dark:text-zinc-400 mb-6">Browse your Kiro conversation history</p>
              {sessionsLoading ? (
                <div className="space-y-4">{[1,2,3].map(i => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}</div>
              ) : !sessionsData || sessionsData.sessions.length === 0 ? (
                <div className="text-center py-20">
                  <div className="w-16 h-16 bg-slate-100 dark:bg-zinc-900 rounded-2xl flex items-center justify-center mx-auto mb-4"><Icons.Chat /></div>
                  <p className="text-slate-500 dark:text-zinc-400">No Kiro sessions found</p>
                  <p className="text-sm text-slate-400 dark:text-zinc-500 mt-2">Sessions are created when you use Kiro IDE</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {sessionsData.sessions.map((session) => (
                    <div key={session.session_id} onClick={() => handleSessionClick(session)} className="rounded-xl bg-white dark:bg-zinc-900 border border-slate-200/50 dark:border-zinc-800 p-5 cursor-pointer hover:shadow-lg hover:scale-[1.01] transition-all">
                      <div className="flex items-start gap-4">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center text-white"><Icons.Chat /></div>
                        <div className="flex-1 min-w-0">
                          <h3 className="font-medium text-slate-900 dark:text-white truncate">{session.title || 'Untitled Session'}</h3>
                          <div className="flex items-center gap-4 mt-2 text-xs text-slate-500 dark:text-zinc-400">
                            <span className="flex items-center gap-1"><Icons.Clock />{new Date(session.date_created_ms).toLocaleDateString()}</span>
                            <span className="flex items-center gap-1"><Icons.Chat />{session.message_count} messages</span>
                          </div>
                        </div>
                        <Icons.ChevronRight />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* KIRO CONFIG VIEW */}
          {activeView === 'config' && (
            <div>
              <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">⚙️ <span className="gradient-text-static">Kiro Configuration</span></h2>
              <p className="text-slate-500 dark:text-zinc-400 mb-6">MCP servers, hooks, and steering files for this workspace</p>
              {kiroConfigLoading ? (
                <div className="space-y-4">{[1,2,3].map(i => <Skeleton key={i} className="h-32 w-full rounded-xl" />)}</div>
              ) : !kiroConfigData ? (
                <div className="text-center py-20"><Icons.Cog /><p className="text-slate-500 dark:text-zinc-400 mt-4">No Kiro configuration found</p></div>
              ) : (
                <div className="space-y-8">
                  {/* Summary Cards */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 p-5 text-white">
                      <div className="text-4xl font-bold">{kiroConfigData.enabled_servers}</div>
                      <div className="text-white/80">MCP Servers</div>
                    </div>
                    <div className="rounded-xl bg-gradient-to-br from-emerald-500 to-green-600 p-5 text-white">
                      <div className="text-4xl font-bold">{kiroConfigData.active_hooks}</div>
                      <div className="text-white/80">Active Hooks</div>
                    </div>
                    <div className="rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 p-5 text-white">
                      <div className="text-4xl font-bold">{kiroConfigData.steering_files.length}</div>
                      <div className="text-white/80">Steering Files</div>
                    </div>
                  </div>

                  {/* CLI Commands */}
                  <div className="rounded-2xl bg-zinc-900 p-6 text-white border border-zinc-800">
                    <div className="flex items-center gap-2 mb-4">
                      <Icons.Terminal />
                      <h3 className="text-lg font-semibold">CLI Commands</h3>
                    </div>
                    <div className="grid grid-cols-2 gap-4 font-mono text-sm">
                      {[
                        { cmd: 'specmem demo', desc: 'Launch this dashboard' },
                        { cmd: 'specmem query "search"', desc: 'Search specifications' },
                        { cmd: 'specmem cov', desc: 'Check spec coverage' },
                        { cmd: 'specmem health', desc: 'Check health score' },
                        { cmd: 'specmem build', desc: 'Build memory index' },
                        { cmd: 'specmem validate', desc: 'Validate specs' },
                      ].map(item => (
                        <div key={item.cmd} className="flex items-center gap-3 bg-black rounded-lg px-4 py-3 border border-zinc-800">
                          <span className="text-emerald-400">$</span>
                          <span className="text-white flex-1">{item.cmd}</span>
                          <span className="text-zinc-500 text-xs">{item.desc}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* MCP Servers */}
                  {kiroConfigData.mcp_servers.length > 0 && (
                    <div className="rounded-2xl bg-white dark:bg-zinc-900 border border-slate-200/50 dark:border-zinc-800 overflow-hidden">
                      <div className="bg-gradient-to-r from-violet-500 to-purple-600 px-6 py-3">
                        <h3 className="text-lg font-semibold text-white">🔌 MCP Servers</h3>
                      </div>
                      <div className="p-4 space-y-3">
                        {kiroConfigData.mcp_servers.map((server) => (
                          <div key={server.name} className="p-4 rounded-xl bg-slate-50 dark:bg-black border border-slate-200 dark:border-zinc-800">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-semibold text-slate-900 dark:text-white">{server.name}</span>
                              <span className={`text-xs px-2 py-1 rounded-full ${server.disabled ? 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400' : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400'}`}>
                                {server.disabled ? '❌ Disabled' : '✅ Enabled'}
                              </span>
                            </div>
                            <div className="text-sm text-slate-600 dark:text-zinc-400 font-mono mb-2">{server.command} {server.args.join(' ')}</div>
                            {server.auto_approve.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-2">
                                <span className="text-xs text-slate-500 dark:text-zinc-500">Auto-approve:</span>
                                {server.auto_approve.map((tool) => (
                                  <span key={tool} className="text-xs bg-violet-100 dark:bg-violet-950 text-violet-700 dark:text-violet-400 px-2 py-0.5 rounded-full">{tool}</span>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Hooks */}
                  {kiroConfigData.hooks.length > 0 && (
                    <div className="rounded-2xl bg-white dark:bg-zinc-900 border border-slate-200/50 dark:border-zinc-800 overflow-hidden">
                      <div className="bg-gradient-to-r from-emerald-500 to-green-600 px-6 py-3">
                        <h3 className="text-lg font-semibold text-white">🪝 Hooks</h3>
                      </div>
                      <div className="p-4 space-y-3">
                        {kiroConfigData.hooks.map((hook) => (
                          <div key={hook.name} className="p-4 rounded-xl bg-slate-50 dark:bg-black border border-slate-200 dark:border-zinc-800">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-semibold text-slate-900 dark:text-white">{hook.name}</span>
                              <span className={`text-xs px-2 py-1 rounded-full ${hook.enabled ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400' : 'bg-slate-100 dark:bg-zinc-800 text-slate-500 dark:text-zinc-400'}`}>
                                {hook.enabled ? '✅ Active' : '⏸️ Inactive'}
                              </span>
                            </div>
                            <p className="text-sm text-slate-600 dark:text-zinc-400 mb-2">{hook.description}</p>
                            <div className="flex items-center gap-4 text-xs">
                              <span className="bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-400 px-2 py-1 rounded">Trigger: {hook.trigger}</span>
                              {hook.file_pattern && <span className="bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-400 px-2 py-1 rounded">Pattern: {hook.file_pattern}</span>}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Steering Files */}
                  {kiroConfigData.steering_files.length > 0 && (
                    <div className="rounded-2xl bg-white dark:bg-zinc-900 border border-slate-200/50 dark:border-zinc-800 overflow-hidden">
                      <div className="bg-gradient-to-r from-amber-500 to-orange-600 px-6 py-3">
                        <h3 className="text-lg font-semibold text-white">📝 Steering Files</h3>
                      </div>
                      <div className="p-4 space-y-3">
                        {kiroConfigData.steering_files.map((steering) => (
                          <div key={steering.name} className="p-4 rounded-xl bg-slate-50 dark:bg-black border border-slate-200 dark:border-zinc-800">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-semibold text-slate-900 dark:text-white">{steering.title || steering.name}</span>
                              <span className={`text-xs px-2 py-1 rounded-full ${steering.inclusion === 'always' ? 'bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-400' : steering.inclusion === 'fileMatch' ? 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400' : 'bg-slate-100 dark:bg-zinc-800 text-slate-500 dark:text-zinc-400'}`}>
                                {steering.inclusion}
                              </span>
                            </div>
                            {steering.file_match_pattern && <div className="text-xs text-slate-500 dark:text-zinc-500 mb-2 font-mono">Pattern: {steering.file_match_pattern}</div>}
                            <p className="text-sm text-slate-600 dark:text-zinc-400 line-clamp-2">{stripMarkdown(steering.body_preview)}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}


          {/* ANALYTICS VIEW */}
          {activeView === 'analytics' && statsData && (
            <div>
              <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">📊 <span className="gradient-text-static">Analytics</span></h2>
              <p className="text-slate-500 dark:text-zinc-400 mb-6">Insights into your specification memory</p>
              <div className="grid grid-cols-2 gap-6">
                <div className="rounded-2xl bg-white dark:bg-zinc-900 border border-slate-200/50 dark:border-zinc-800 p-6">
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Specification Types</h3>
                  <div className="space-y-3">
                    {Object.entries(statsData.by_type).map(([type, count]) => {
                      const percentage = Math.round((count / statsData.total_blocks) * 100)
                      return (
                        <div key={type}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="flex items-center gap-2 text-sm text-slate-700 dark:text-white"><span>{typeConfig[type]?.icon}</span><span className="capitalize">{type}</span></span>
                            <span className="text-sm font-medium text-slate-900 dark:text-white">{count} ({percentage}%)</span>
                          </div>
                          <div className="h-2 bg-slate-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                            <div className="h-full bg-gradient-to-r from-violet-500 to-purple-500 rounded-full" style={{ width: `${percentage}%` }}></div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
                <div className="rounded-2xl bg-white dark:bg-zinc-900 border border-slate-200/50 dark:border-zinc-800 p-6">
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Source Files</h3>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {Object.entries(statsData.by_source).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([source, count]) => (
                      <div key={source} className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-zinc-800 last:border-0">
                        <span className="text-sm text-slate-600 dark:text-zinc-400 truncate max-w-[200px]">{source.split('/').slice(-2).join('/')}</span>
                        <span className="text-sm font-medium text-slate-900 dark:text-white bg-slate-100 dark:bg-zinc-800 px-2 py-0.5 rounded-full">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="col-span-2 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 p-6 text-white">
                  <h3 className="text-lg font-semibold mb-4">Memory Overview</h3>
                  <div className="grid grid-cols-4 gap-6">
                    <div><p className="text-4xl font-bold">{statsData.total_blocks}</p><p className="text-violet-200">Total Specs</p></div>
                    <div><p className="text-4xl font-bold">{(statsData.memory_size_bytes / 1024).toFixed(1)}</p><p className="text-violet-200">KB Memory</p></div>
                    <div><p className="text-4xl font-bold">{Object.keys(statsData.by_source).length}</p><p className="text-violet-200">Source Files</p></div>
                    <div><p className="text-4xl font-bold">{Object.keys(statsData.by_type).length}</p><p className="text-violet-200">Spec Types</p></div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* GUIDELINES VIEW */}
          {activeView === 'guidelines' && <GuidelinesView />}
        </main>
      </div>

      {/* Block Detail Modal */}
      {selectedBlock && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in" onClick={() => setSelectedBlock(null)}>
          <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-hidden animate-scale-in border dark:border-zinc-800" onClick={(e) => e.stopPropagation()}>
            <div className={`${getTypeStyle(selectedBlock.type).bg} px-6 py-4 border-b border-slate-200/50 dark:border-zinc-800`}>
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
              <div className="text-slate-700 dark:text-zinc-300 whitespace-pre-wrap">{stripMarkdown(selectedBlock.text)}</div>
              <div className="mt-6 pt-6 border-t border-slate-200 dark:border-zinc-800 space-y-4">
                <div><h4 className="text-xs font-semibold text-slate-500 dark:text-zinc-500 uppercase mb-1">Source</h4><p className="text-sm text-slate-700 dark:text-white font-mono bg-slate-100 dark:bg-black px-3 py-2 rounded-lg border dark:border-zinc-800">{selectedBlock.source}</p></div>
                {selectedBlock.tags.length > 0 && (<div><h4 className="text-xs font-semibold text-slate-500 dark:text-zinc-500 uppercase mb-2">Tags</h4><div className="flex flex-wrap gap-2">{selectedBlock.tags.map((tag, i) => <span key={i} className="text-xs bg-violet-100 dark:bg-violet-950 text-violet-700 dark:text-violet-400 px-2 py-1 rounded-full">{tag}</span>)}</div></div>)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Session Detail Modal */}
      {selectedSession && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in" onClick={() => setSelectedSession(null)}>
          <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl max-w-3xl w-full max-h-[85vh] overflow-hidden animate-scale-in border dark:border-zinc-800" onClick={(e) => e.stopPropagation()}>
            <div className="bg-gradient-to-r from-cyan-500 to-blue-500 px-6 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 text-white"><Icons.Chat /><div><h3 className="font-semibold">{selectedSession.title || 'Untitled Session'}</h3><p className="text-sm text-white/70">{new Date(selectedSession.date_created_ms).toLocaleString()}</p></div></div>
                <button onClick={() => setSelectedSession(null)} className="p-2 hover:bg-white/20 rounded-lg transition-colors text-white"><Icons.X /></button>
              </div>
            </div>
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              <div className="space-y-4">
                {selectedSession.messages?.map((msg, idx) => (
                  <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                    {msg.role !== 'user' && <div className="w-8 h-8 rounded-full bg-violet-100 dark:bg-violet-950 flex items-center justify-center flex-shrink-0 text-violet-600 dark:text-violet-400"><Icons.Bot /></div>}
                    <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${msg.role === 'user' ? 'bg-violet-500 text-white' : 'bg-slate-100 dark:bg-zinc-800 text-slate-800 dark:text-white'}`}><p className="text-sm whitespace-pre-wrap">{msg.content}</p></div>
                    {msg.role === 'user' && <div className="w-8 h-8 rounded-full bg-violet-500 flex items-center justify-center flex-shrink-0 text-white"><Icons.User /></div>}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Spec File Content Modal */}
      {selectedSpecFile && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in" onClick={() => setSelectedSpecFile(null)}>
          <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden animate-scale-in border dark:border-zinc-800" onClick={(e) => e.stopPropagation()}>
            <div className={`px-6 py-4 border-b border-slate-200/50 dark:border-zinc-800 ${
              selectedSpecFile.file_type === 'requirements' ? 'bg-gradient-to-r from-blue-500 to-blue-600' :
              selectedSpecFile.file_type === 'design' ? 'bg-gradient-to-r from-purple-500 to-purple-600' :
              'bg-gradient-to-r from-green-500 to-green-600'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 text-white">
                  <span className="text-2xl">
                    {selectedSpecFile.file_type === 'requirements' ? '📋' : selectedSpecFile.file_type === 'design' ? '🎨' : '✅'}
                  </span>
                  <div>
                    <h3 className="font-semibold capitalize">{selectedSpecFile.feature_name.replace(/-/g, ' ')} - {selectedSpecFile.file_type}</h3>
                    <p className="text-sm text-white/70">.kiro/specs/{selectedSpecFile.feature_name}/{selectedSpecFile.file_type}.md</p>
                  </div>
                </div>
                <button onClick={() => setSelectedSpecFile(null)} className="p-2 hover:bg-white/20 rounded-lg transition-colors text-white"><Icons.X /></button>
              </div>
            </div>
            <div className="p-6 overflow-y-auto max-h-[75vh]">
              {selectedSpecFile.exists ? (
                <div className="text-slate-700 dark:text-zinc-300 whitespace-pre-wrap font-mono text-sm leading-relaxed">
                  {stripMarkdown(selectedSpecFile.content)}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Icons.Document />
                  <p className="text-slate-500 dark:text-zinc-400 mt-4">File not found</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }
        @keyframes scale-in { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
        @keyframes slide-in { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } }
        .animate-fade-in { animation: fade-in 0.2s ease-out; }
        .animate-scale-in { animation: scale-in 0.2s ease-out; }
        .animate-slide-in { animation: slide-in 0.3s ease-out; }
      `}</style>
    </div>
  )
}

export default App
