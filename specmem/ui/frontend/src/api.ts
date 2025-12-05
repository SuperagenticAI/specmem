// API client for SpecMem backend

export interface BlockSummary {
  id: string
  type: string
  text_preview: string
  source: string
  status: string
  pinned: boolean
}

export interface BlockDetail {
  id: string
  type: string
  text: string
  source: string
  status: string
  pinned: boolean
  tags: string[]
  links: string[]
}

export interface BlockListResponse {
  blocks: BlockSummary[]
  total: number
  active_count: number
  legacy_count: number
  pinned_count: number
}

export interface StatsResponse {
  total_blocks: number
  active_count: number
  legacy_count: number
  pinned_count: number
  by_type: Record<string, number>
  by_source: Record<string, number>
  memory_size_bytes: number
}

export interface SearchResult {
  block: BlockSummary
  score: number
}

export interface SearchResponse {
  results: SearchResult[]
  query: string
}

export interface PinnedBlockResponse {
  block: BlockSummary
  reason: string
}

export interface PinnedListResponse {
  blocks: PinnedBlockResponse[]
  total: number
}

export interface ExportResponse {
  success: boolean
  output_path: string
  message: string
}

// Spec file content types
export interface SpecFileResponse {
  feature_name: string
  file_type: string
  file_path: string
  content: string
  exists: boolean
}

const API_BASE = '/api'

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options)
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`)
  }
  return response.json()
}

// Coverage types
export interface CriterionResponse {
  id: string
  number: string
  text: string
  feature_name: string
  is_covered: boolean
  confidence: number
  test_name: string | null
  test_file: string | null
}

export interface FeatureCoverageResponse {
  feature_name: string
  total_count: number
  tested_count: number
  coverage_percentage: number
  criteria: CriterionResponse[]
}

export interface CoverageResponse {
  total_criteria: number
  covered_criteria: number
  coverage_percentage: number
  features: FeatureCoverageResponse[]
  badge_url: string
}

export interface TestSuggestionResponse {
  criterion_id: string
  criterion_text: string
  feature_name: string
  suggested_file: string
  suggested_name: string
  verification_points: string[]
}

// Session types
export interface SessionMessageResponse {
  role: string
  content: string
  timestamp_ms: number | null
}

export interface SessionResponse {
  session_id: string
  title: string
  workspace_directory: string
  date_created_ms: number
  message_count: number
  messages?: SessionMessageResponse[]
}

export interface SessionSearchResultResponse {
  session: SessionResponse
  score: number
  matched_message_indices: number[]
}

export interface SessionListResponse {
  sessions: SessionResponse[]
  total: number
}

export interface SessionSearchResponse {
  results: SessionSearchResultResponse[]
  query: string
}

// Power types
export interface PowerToolResponse {
  name: string
  description: string
}

export interface PowerResponse {
  name: string
  description: string
  version: string | null
  keywords: string[]
  tools: PowerToolResponse[]
  steering_files: string[]
}

export interface PowerListResponse {
  powers: PowerResponse[]
  total: number
}

export const api = {
  getBlocks: (status?: string, type?: string): Promise<BlockListResponse> => {
    const params = new URLSearchParams()
    if (status && status !== 'all') params.set('status', status)
    if (type && type !== 'all') params.set('type', type)
    const query = params.toString()
    return fetchJson(`${API_BASE}/blocks${query ? `?${query}` : ''}`)
  },

  getBlock: (id: string): Promise<BlockDetail> => {
    return fetchJson(`${API_BASE}/blocks/${encodeURIComponent(id)}`)
  },

  getStats: (): Promise<StatsResponse> => {
    return fetchJson(`${API_BASE}/stats`)
  },

  search: (query: string, limit = 10): Promise<SearchResponse> => {
    return fetchJson(`${API_BASE}/search?q=${encodeURIComponent(query)}&limit=${limit}`)
  },

  getPinned: (): Promise<PinnedListResponse> => {
    return fetchJson(`${API_BASE}/pinned`)
  },

  exportPack: (): Promise<ExportResponse> => {
    return fetchJson(`${API_BASE}/export`, { method: 'POST' })
  },

  // Spec file content endpoint
  getSpecFile: (featureName: string, fileType: string): Promise<SpecFileResponse> => {
    return fetchJson(`${API_BASE}/specs/${encodeURIComponent(featureName)}/${encodeURIComponent(fileType)}`)
  },

  // Coverage endpoints
  getCoverage: (): Promise<CoverageResponse> => {
    return fetchJson(`${API_BASE}/coverage`)
  },

  getCoverageSuggestions: (feature?: string): Promise<TestSuggestionResponse[]> => {
    const params = feature ? `?feature=${encodeURIComponent(feature)}` : ''
    return fetchJson(`${API_BASE}/coverage/suggestions${params}`)
  },

  // Session endpoints
  getSessions: (limit = 20, workspaceOnly = false): Promise<SessionListResponse> => {
    return fetchJson(`${API_BASE}/sessions?limit=${limit}&workspace_only=${workspaceOnly}`)
  },

  searchSessions: (query: string, limit = 10): Promise<SessionSearchResponse> => {
    return fetchJson(`${API_BASE}/sessions/search?q=${encodeURIComponent(query)}&limit=${limit}`)
  },

  getSession: (sessionId: string): Promise<SessionResponse> => {
    return fetchJson(`${API_BASE}/sessions/${sessionId}`)
  },

  // Power endpoints
  getPowers: (): Promise<PowerListResponse> => {
    return fetchJson(`${API_BASE}/powers`)
  },

  getPower: (powerName: string): Promise<PowerResponse> => {
    return fetchJson(`${API_BASE}/powers/${encodeURIComponent(powerName)}`)
  },
}


// Health Score types
export interface ScoreBreakdownResponse {
  category: string
  score: number
  weight: number
  weighted_score: number
  details: string
}

export interface HealthScoreResponse {
  overall_score: number
  letter_grade: string
  grade_color: string
  breakdown: ScoreBreakdownResponse[]
  suggestions: string[]
  spec_count: number
  feature_count: number
}

// Impact Graph types
export interface GraphNodeResponse {
  id: string
  type: string
  label: string
  metadata: Record<string, unknown>
  x: number | null
  y: number | null
}

export interface GraphEdgeResponse {
  source: string
  target: string
  relationship: string
  weight: number
}

export interface ImpactGraphResponse {
  nodes: GraphNodeResponse[]
  edges: GraphEdgeResponse[]
  stats: {
    total_nodes: number
    total_edges: number
    nodes_by_type: Record<string, number>
  }
}

// Quick Action types
export interface ActionResultResponse {
  success: boolean
  action: string
  message: string
  data: Record<string, unknown> | null
  error: string | null
}

// Add new API methods
export const apiExtended = {
  ...api,

  // Health Score
  getHealthScore: (): Promise<HealthScoreResponse> => {
    return fetchJson(`${API_BASE}/health`)
  },

  // Impact Graph
  getImpactGraph: (types?: string[]): Promise<ImpactGraphResponse> => {
    const params = types ? `?types=${types.join(',')}` : ''
    return fetchJson(`${API_BASE}/graph${params}`)
  },

  // Quick Actions
  runAction: (action: string, params?: Record<string, string>): Promise<ActionResultResponse> => {
    const queryParams = params ? `?${new URLSearchParams(params).toString()}` : ''
    return fetchJson(`${API_BASE}/actions/${action}${queryParams}`, { method: 'POST' })
  },

  scanAction: (): Promise<ActionResultResponse> => {
    return fetchJson(`${API_BASE}/actions/scan`, { method: 'POST' })
  },

  buildAction: (): Promise<ActionResultResponse> => {
    return fetchJson(`${API_BASE}/actions/build`, { method: 'POST' })
  },

  validateAction: (): Promise<ActionResultResponse> => {
    return fetchJson(`${API_BASE}/actions/validate`, { method: 'POST' })
  },

  coverageAction: (): Promise<ActionResultResponse> => {
    return fetchJson(`${API_BASE}/actions/coverage`, { method: 'POST' })
  },

  queryAction: (q: string): Promise<ActionResultResponse> => {
    return fetchJson(`${API_BASE}/actions/query?q=${encodeURIComponent(q)}`, { method: 'POST' })
  },
}


// =============================================================================
// Lifecycle API Types
// =============================================================================

export interface SpecHealthScoreResponse {
  spec_id: string
  spec_path: string
  score: number
  code_references: number
  last_modified: string
  query_count: number
  is_orphaned: boolean
  is_stale: boolean
  compression_ratio: number | null
  recommendations: string[]
}

export interface LifecycleHealthResponse {
  total_specs: number
  orphaned_count: number
  stale_count: number
  average_score: number
  scores: SpecHealthScoreResponse[]
}

export interface PruneResultResponse {
  spec_id: string
  spec_path: string
  action: string
  archive_path: string | null
  reason: string
}

export interface PruneRequest {
  spec_names?: string[]
  mode?: 'archive' | 'delete'
  dry_run?: boolean
  force?: boolean
  orphaned?: boolean
  stale?: boolean
  stale_days?: number
}

export interface PruneResponse {
  success: boolean
  message: string
  dry_run: boolean
  results: PruneResultResponse[]
}

export interface GenerateRequest {
  files: string[]
  format?: string
  group_by?: 'file' | 'directory' | 'module'
  write?: boolean
}

export interface GeneratedSpecResponse {
  spec_name: string
  spec_path: string
  source_files: string[]
  adapter_format: string
  content_preview: string
  content_size: number
}

export interface GenerateResponse {
  success: boolean
  message: string
  specs: GeneratedSpecResponse[]
}

export interface CompressRequest {
  spec_names?: string[]
  threshold?: number
  all_verbose?: boolean
  save?: boolean
}

export interface CompressedSpecResponse {
  spec_id: string
  original_size: number
  compressed_size: number
  compression_ratio: number
  preserved_criteria_count: number
}

export interface CompressResponse {
  success: boolean
  message: string
  results: CompressedSpecResponse[]
  verbose_specs?: string[]
}

// =============================================================================
// Lifecycle API Methods
// =============================================================================

export const lifecycleApi = {
  // Get health scores for all specs
  getHealth: (staleDays = 90): Promise<LifecycleHealthResponse> => {
    return fetchJson(`${API_BASE}/lifecycle/health?stale_days=${staleDays}`)
  },

  // Get health score for a specific spec
  getSpecHealth: (specName: string, staleDays = 90): Promise<SpecHealthScoreResponse> => {
    return fetchJson(`${API_BASE}/lifecycle/health/${encodeURIComponent(specName)}?stale_days=${staleDays}`)
  },

  // Prune specs
  prune: (request: PruneRequest): Promise<PruneResponse> => {
    return fetchJson(`${API_BASE}/lifecycle/prune`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })
  },

  // Generate specs from code
  generate: (request: GenerateRequest): Promise<GenerateResponse> => {
    return fetchJson(`${API_BASE}/lifecycle/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })
  },

  // Compress verbose specs
  compress: (request: CompressRequest): Promise<CompressResponse> => {
    return fetchJson(`${API_BASE}/lifecycle/compress`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })
  },

  // Quick action for lifecycle health
  healthAction: (): Promise<ActionResultResponse> => {
    return fetchJson(`${API_BASE}/actions/lifecycle-health`, { method: 'POST' })
  },
}


// =============================================================================
// Kiro Configuration API Types
// =============================================================================

export interface SteeringFileResponse {
  name: string
  title: string
  inclusion: string
  file_match_pattern: string | null
  body_preview: string
}

export interface MCPServerResponse {
  name: string
  command: string
  args: string[]
  disabled: boolean
  auto_approve: string[]
}

export interface HookResponse {
  name: string
  description: string
  trigger: string
  file_pattern: string | null
  enabled: boolean
  action: string | null
}

export interface KiroConfigResponse {
  steering_files: SteeringFileResponse[]
  mcp_servers: MCPServerResponse[]
  hooks: HookResponse[]
  total_tools: number
  enabled_servers: number
  active_hooks: number
}

// =============================================================================
// Kiro Configuration API Methods
// =============================================================================

export const kiroConfigApi = {
  getConfig: (): Promise<KiroConfigResponse> => {
    return fetchJson(`${API_BASE}/kiro-config`)
  },
}


// =============================================================================
// Coding Guidelines API Types
// =============================================================================

export interface GuidelineResponse {
  id: string
  title: string
  content: string
  source_type: string
  source_file: string
  file_pattern: string | null
  tags: string[]
  is_sample: boolean
}

export interface GuidelinesListResponse {
  guidelines: GuidelineResponse[]
  total_count: number
  counts_by_source: Record<string, number>
}

export interface ConversionResultResponse {
  filename: string
  content: string
  frontmatter: Record<string, unknown>
  source_id: string
}

export interface ExportResultResponse {
  format: string
  content: string
  filename: string
}

// =============================================================================
// Coding Guidelines API Methods
// =============================================================================

export const guidelinesApi = {
  // Get all guidelines with optional filtering
  getGuidelines: (params?: { source?: string; file?: string; q?: string }): Promise<GuidelinesListResponse> => {
    const searchParams = new URLSearchParams()
    if (params?.source) searchParams.set('source', params.source)
    if (params?.file) searchParams.set('file', params.file)
    if (params?.q) searchParams.set('q', params.q)
    const query = searchParams.toString()
    return fetchJson(`${API_BASE}/guidelines${query ? `?${query}` : ''}`)
  },

  // Convert a guideline to any format (steering, claude, cursor)
  convertGuideline: (guidelineId: string, format: string, preview = true): Promise<ConversionResultResponse> => {
    return fetchJson(`${API_BASE}/guidelines/convert`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ guideline_id: guidelineId, format, preview }),
    })
  },

  // Legacy: Convert to steering (for backwards compatibility)
  convertToSteering: (guidelineId: string, preview = true): Promise<ConversionResultResponse> => {
    return fetchJson(`${API_BASE}/guidelines/convert`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ guideline_id: guidelineId, format: 'steering', preview }),
    })
  },

  // Export guidelines to Claude or Cursor format
  exportGuidelines: (format: 'claude' | 'cursor'): Promise<ExportResultResponse> => {
    return fetchJson(`${API_BASE}/guidelines/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ format }),
    })
  },
}
