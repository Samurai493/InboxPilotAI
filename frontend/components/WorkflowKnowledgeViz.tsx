'use client'

import { useCallback, useMemo, useState } from 'react'

export type KgEntity = {
  id: string
  type?: string
  name?: string
}

export type KgRelation = {
  type?: string
  source_entity_id?: string
  target_entity_id?: string
  source_name?: string
  target_name?: string
  /** normalized ids from persist snapshot */
  source_id?: string
  target_id?: string
}

export type AuditEntry = Record<string, unknown> & { node?: string; action?: string }

const NODE_TITLE: Record<string, string> = {
  ingest_message: 'Ingest',
  normalize_message: 'Normalize',
  classify_intent: 'Classify intent',
  retrieve_memory: 'Load memory + KG',
  synthesize_email_insights: 'Synthesize insights',
  orchestration_agent: 'Orchestration',
  recruiter_agent: 'Recruiter path',
  scheduling_agent: 'Scheduling path',
  academic_agent: 'Academic path',
  support_agent: 'Support path',
  billing_agent: 'Billing path',
  draft_reply: 'Draft reply',
  generate_draft: 'Draft reply',
  extract_tasks: 'Extract tasks',
  persist_knowledge_memory: 'Save to knowledge graph',
  score_confidence: 'Confidence score',
  risk_gate: 'Risk gate',
  human_review_interrupt: 'Human review',
  finalize_output: 'Finalize',
}

function auditTitle(entry: AuditEntry): string {
  const n = String(entry.node || '')
  return NODE_TITLE[n] || n || 'Step'
}

function entityFill(t?: string): string {
  switch ((t || '').toLowerCase()) {
    case 'person':
      return '#dbeafe'
    case 'intent':
      return '#ede9fe'
    case 'topic':
      return '#fef3c7'
    case 'task_item':
      return '#d1fae5'
    default:
      return '#f3f4f6'
  }
}

function entityStroke(t?: string): string {
  switch ((t || '').toLowerCase()) {
    case 'person':
      return '#2563eb'
    case 'intent':
      return '#7c3aed'
    case 'topic':
      return '#d97706'
    case 'task_item':
      return '#059669'
    default:
      return '#6b7280'
  }
}

function layoutRadial(
  entities: KgEntity[],
  w: number,
  h: number,
): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>()
  const cx = w / 2
  const cy = h / 2
  const n = entities.length
  const r = Math.min(w, h) * 0.32
  entities.forEach((e, i) => {
    const angle = (2 * Math.PI * i) / Math.max(n, 1) - Math.PI / 2
    positions.set(e.id, { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) })
  })
  return positions
}

type TabId = 'workflow' | 'context' | 'written'

type Props = {
  auditLog?: AuditEntry[] | Array<Record<string, unknown>> | null
  knowledgeHits?: { entities?: KgEntity[]; relations?: KgRelation[] } | null
  knowledgeWritten?: { entities?: KgEntity[]; relations?: KgRelation[] } | null
  selectedAgent?: string | null
}

function normalizeRelationEndpoints(rel: KgRelation): { s: string; t: string } | null {
  const s = rel.source_id || rel.source_entity_id
  const t = rel.target_id || rel.target_entity_id
  if (!s || !t) return null
  return { s, t }
}

function KnowledgeGraphSvg(props: {
  entities: KgEntity[]
  relations: KgRelation[]
  title: string
  emptyHint: string
}) {
  const { entities, relations, title, emptyHint } = props
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [zoom, setZoom] = useState(1)

  const w = 880
  const h = 420

  const { positions, edges } = useMemo(() => {
    const positions = layoutRadial(entities, w, h)
    const edges: Array<{
      x1: number
      y1: number
      x2: number
      y2: number
      label: string
      key: string
    }> = []
    relations.forEach((rel, idx) => {
      const ends = normalizeRelationEndpoints(rel)
      if (!ends) return
      const p1 = positions.get(ends.s)
      const p2 = positions.get(ends.t)
      if (!p1 || !p2) return
      edges.push({
        x1: p1.x,
        y1: p1.y,
        x2: p2.x,
        y2: p2.y,
        label: String(rel.type || 'REL'),
        key: `${ends.s}-${ends.t}-${idx}`,
      })
    })
    return { positions, edges }
  }, [entities, relations, w, h])

  const selected = selectedId ? entities.find((e) => e.id === selectedId) : null

  const onWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -0.08 : 0.08
    setZoom((z) => Math.min(2.2, Math.max(0.55, z + delta)))
  }, [])

  if (!entities.length) {
    return (
      <div className="rounded-lg border border-dashed border-gray-200 bg-gray-50/80 px-4 py-8 text-center text-sm text-gray-600">
        {emptyHint}
      </div>
    )
  }

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-gray-800">{title}</p>
        <p className="text-xs text-gray-500">Scroll to zoom · Click a node for details</p>
      </div>
      <div
        className="overflow-hidden rounded-lg border border-gray-200 bg-white"
        onWheel={onWheel}
      >
        <div
          style={{
            transform: `scale(${zoom})`,
            transformOrigin: 'center top',
            transition: 'transform 0.08s ease-out',
          }}
        >
          <svg
            width={w}
            height={h}
            role="img"
            aria-label="Knowledge graph"
            className="mx-auto block"
          >
            <defs>
              <marker
                id="arrow-kg"
                markerWidth="8"
                markerHeight="8"
                refX="7"
                refY="4"
                orient="auto"
              >
                <path d="M0,0 L8,4 L0,8 Z" fill="#94a3b8" />
              </marker>
            </defs>
            {edges.map((e) => (
              <line
                key={e.key}
                x1={e.x1}
                y1={e.y1}
                x2={e.x2}
                y2={e.y2}
                stroke="#94a3b8"
                strokeWidth={1.5}
                markerEnd="url(#arrow-kg)"
              />
            ))}
            {edges.map((e) => {
              const mx = (e.x1 + e.x2) / 2
              const my = (e.y1 + e.y2) / 2
              return (
                <text
                  key={`${e.key}-lbl`}
                  x={mx}
                  y={my}
                  textAnchor="middle"
                  className="fill-gray-500 text-[9px]"
                  style={{ fontSize: '9px' }}
                >
                  {e.label}
                </text>
              )
            })}
            {entities.map((ent) => {
              const p = positions.get(ent.id)
              if (!p) return null
              const r = 52
              const active = selectedId === ent.id
              return (
                <g
                  key={ent.id}
                  transform={`translate(${p.x}, ${p.y})`}
                  className="cursor-pointer"
                  onClick={() => setSelectedId(ent.id === selectedId ? null : ent.id)}
                >
                  <rect
                    x={-r}
                    y={-22}
                    width={r * 2}
                    height={44}
                    rx={8}
                    fill={entityFill(ent.type)}
                    stroke={entityStroke(ent.type)}
                    strokeWidth={active ? 2.5 : 1.2}
                  />
                  <text
                    y={4}
                    textAnchor="middle"
                    className="pointer-events-none fill-gray-900 text-[11px] font-medium"
                    style={{ fontSize: '11px' }}
                  >
                    {(ent.name || '—').length > 22
                      ? `${(ent.name || '').slice(0, 20)}…`
                      : ent.name || '—'}
                  </text>
                  <text
                    y={-30}
                    textAnchor="middle"
                    className="pointer-events-none fill-gray-500 text-[9px] uppercase"
                    style={{ fontSize: '9px' }}
                  >
                    {ent.type || 'entity'}
                  </text>
                </g>
              )
            })}
          </svg>
        </div>
      </div>
      {selected ? (
        <div className="mt-3 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm">
          <div className="font-semibold text-gray-900">{selected.name || '(unnamed)'}</div>
          <div className="mt-1 text-xs text-gray-600">
            Type: {selected.type || '—'} · ID: {selected.id}
          </div>
        </div>
      ) : null}
    </div>
  )
}

export function WorkflowKnowledgeViz({
  auditLog,
  knowledgeHits,
  knowledgeWritten,
  selectedAgent,
}: Props) {
  const [tab, setTab] = useState<TabId>('workflow')
  const [stepIndex, setStepIndex] = useState<number | null>(null)

  const entries: AuditEntry[] = (Array.isArray(auditLog) ? auditLog : []) as AuditEntry[]
  const contextEntities = knowledgeHits?.entities ?? []
  const contextRelations = knowledgeHits?.relations ?? []
  const writtenEntities = knowledgeWritten?.entities ?? []
  const writtenRelations = knowledgeWritten?.relations ?? []

  const activeEntry = stepIndex !== null ? entries[stepIndex] : null

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
      <div className="border-b border-gray-100 px-6 py-4">
        <h2 className="text-xl font-semibold text-gray-900">Workflow &amp; knowledge graph</h2>
        <p className="mt-1 text-sm text-gray-600">
          Trace LangGraph steps and inspect memory that shaped this reply
          {selectedAgent ? (
            <>
              {' '}
              <span className="font-medium text-gray-800">· Routed agent: {selectedAgent}</span>
            </>
          ) : null}
        </p>
      </div>

      <div className="flex flex-wrap gap-1 border-b border-gray-100 px-4 pt-3">
        {(
          [
            ['workflow', 'Run timeline'],
            ['context', 'Context memory (KG)'],
            ['written', 'Saved this run'],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => {
              setTab(id)
              setStepIndex(null)
            }}
            className={[
              'rounded-t-lg px-4 py-2 text-sm font-medium transition-colors',
              tab === id
                ? 'bg-gray-100 text-gray-900'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
            ].join(' ')}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="px-6 py-6">
        {tab === 'workflow' ? (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Ordered audit events emitted by each graph node. Select a step to see raw metadata.
            </p>
            {entries.length === 0 ? (
              <p className="text-sm text-amber-800">No audit log in state (older run or checkpoint).</p>
            ) : (
              <>
                <div className="flex flex-wrap items-stretch gap-y-2 overflow-x-auto pb-2">
                  {entries.map((entry, i) => {
                    const active = stepIndex === i
                    return (
                      <div key={i} className="flex shrink-0 items-center">
                        <button
                          type="button"
                          onClick={() => setStepIndex(active ? null : i)}
                          className={[
                            'flex min-h-[4.5rem] w-[7.25rem] flex-col items-center justify-center rounded-lg border px-2 py-2 text-center text-xs transition-colors',
                            active
                              ? 'border-primary-600 bg-primary-50 text-primary-900'
                              : 'border-gray-200 bg-white text-gray-800 hover:border-gray-300',
                          ].join(' ')}
                        >
                          <span className="font-semibold leading-tight">{i + 1}</span>
                          <span className="mt-1 line-clamp-3 text-[10px] leading-snug text-gray-600">
                            {auditTitle(entry)}
                          </span>
                        </button>
                        {i < entries.length - 1 ? (
                          <span
                            className="mx-1 shrink-0 text-gray-400 select-none"
                            aria-hidden
                          >
                            →
                          </span>
                        ) : null}
                      </div>
                    )
                  })}
                </div>
                {activeEntry ? (
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                    <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                      Step detail
                    </div>
                    <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap break-words text-xs text-gray-800">
                      {JSON.stringify(activeEntry, null, 2)}
                    </pre>
                  </div>
                ) : null}
              </>
            )}
          </div>
        ) : null}

        {tab === 'context' ? (
          <KnowledgeGraphSvg
            entities={contextEntities}
            relations={contextRelations}
            title="Knowledge retrieved before this reply"
            emptyHint="No graph entities were loaded for this user yet (empty memory or first run)."
          />
        ) : null}

        {tab === 'written' ? (
          <KnowledgeGraphSvg
            entities={writtenEntities}
            relations={writtenRelations}
            title="Entities and relations saved from this email"
            emptyHint="Nothing was written to persistent memory for this run (or extraction produced no tasks / sender)."
          />
        ) : null}
      </div>
    </div>
  )
}
