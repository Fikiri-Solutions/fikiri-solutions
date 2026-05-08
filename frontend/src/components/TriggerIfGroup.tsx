import React, { useId, useMemo } from 'react'
import { Plus, Trash2, Filter } from 'lucide-react'

export type TriggerIfConditionRow = {
  field: string
  op: string
  value?: string | number | boolean | null
}

export type TriggerIfGroupValue = {
  match: 'all'
  conditions: TriggerIfConditionRow[]
}

export type TriggerConditionMetadata = {
  if_match_values: string[]
  operator_labels: Record<string, string>
  triggers: Record<
    string,
    {
      fields: { value: string; label: string }[]
      string_operators: string[]
      numeric_operators: string[]
      numeric_fields: string[]
    }
  >
}

function operatorsForField(
  field: string,
  triggerType: string,
  meta: TriggerConditionMetadata | null | undefined
): string[] {
  if (!field || !meta?.triggers?.[triggerType]) {
    return []
  }
  const t = meta.triggers[triggerType]
  if (field === 'scheduled_run') {
    return ['equals', 'not_equals', 'is_empty', 'is_not_empty']
  }
  if (t.numeric_fields.includes(field)) {
    const set = new Set<string>([
      ...t.numeric_operators,
      'equals',
      'not_equals',
      'is_empty',
      'is_not_empty',
    ])
    return Array.from(set).sort()
  }
  return [...t.string_operators].sort()
}

function opNeedsValue(op: string): boolean {
  return op !== 'is_empty' && op !== 'is_not_empty'
}

type Props = {
  triggerType: string
  value: TriggerIfGroupValue
  onChange: (next: TriggerIfGroupValue) => void
  metadata: TriggerConditionMetadata | null | undefined
}

export const TriggerIfGroup: React.FC<Props> = ({ triggerType, value, onChange, metadata }) => {
  const idPrefix = useId()
  const triggerMeta = metadata?.triggers?.[triggerType]
  const fields = triggerMeta?.fields ?? []

  const defaultField = fields[0]?.value ?? ''

  const addCondition = () => {
    const field = defaultField
    const ops = operatorsForField(field, triggerType, metadata)
    const op = ops[0] ?? 'contains'
    onChange({
      match: 'all',
      conditions: [...value.conditions, { field, op, value: '' }],
    })
  }

  const removeCondition = (index: number) => {
    const next = value.conditions.filter((_, i) => i !== index)
    onChange({ match: 'all', conditions: next })
  }

  const patchCondition = (index: number, patch: Partial<TriggerIfConditionRow>) => {
    const nextConds = value.conditions.map((c, i) => (i === index ? { ...c, ...patch } : c))
    onChange({ match: 'all', conditions: nextConds })
  }

  const onFieldChange = (index: number, field: string) => {
    const ops = operatorsForField(field, triggerType, metadata)
    const current = value.conditions[index]
    const op = ops.includes(current.op) ? current.op : ops[0] ?? 'contains'
    patchCondition(index, { field, op, value: opNeedsValue(op) ? current.value : undefined })
  }

  const onOpChange = (index: number, op: string) => {
    const current = value.conditions[index]
    patchCondition(index, {
      op,
      value: opNeedsValue(op) ? (current.value ?? '') : undefined,
    })
  }

  const hint = useMemo(() => {
    if (!triggerMeta) {
      return 'Loading trigger options…'
    }
    return 'All rows must pass (AND). Leave empty to use legacy filters or match all events for this trigger.'
  }, [triggerMeta])

  return (
    <div className="rounded-lg border border-brand-text/10 dark:border-gray-700 bg-white/60 dark:bg-gray-900/40 p-3 space-y-2">
      <div className="flex items-center gap-2">
        <Filter className="h-3.5 w-3.5 text-brand-primary flex-shrink-0" />
        <div>
          <p className="text-xs font-semibold text-brand-text dark:text-white">Run only if (all match)</p>
          <p className="text-xs text-brand-text/60 dark:text-gray-400">{hint}</p>
        </div>
      </div>

      {value.conditions.length === 0 && (
        <p className="text-xs text-brand-text/50 dark:text-gray-500 italic">No extra filters — workflow runs for every event of this type (subject to legacy rules).</p>
      )}

      <div className="space-y-2">
        {value.conditions.map((row, index) => {
          const ops = operatorsForField(row.field, triggerType, metadata)
          const showValue = opNeedsValue(row.op)
          const isScheduled = row.field === 'scheduled_run' && (row.op === 'equals' || row.op === 'not_equals')
          const fieldId = `${idPrefix}-condition-${index}-field`
          const operatorId = `${idPrefix}-condition-${index}-operator`
          const valueId = `${idPrefix}-condition-${index}-value`

          return (
            <div
              key={`${index}-${row.field}-${row.op}`}
              className="flex flex-wrap items-end gap-2 p-2 rounded-md border border-brand-text/10 dark:border-gray-700 bg-brand-accent/5 dark:bg-gray-950/50"
            >
              <div className="min-w-[140px] flex-1">
                <label htmlFor={fieldId} className="text-[10px] uppercase tracking-wide text-brand-text/50 dark:text-gray-500">Field</label>
                <select
                  id={fieldId}
                  className="mt-0.5 w-full rounded-lg border border-brand-text/20 px-2 py-1.5 text-xs bg-white dark:bg-gray-900"
                  value={row.field}
                  onChange={e => onFieldChange(index, e.target.value)}
                  disabled={!fields.length}
                >
                  {fields.map(f => (
                    <option key={f.value} value={f.value}>
                      {f.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="min-w-[120px] flex-1">
                <label htmlFor={operatorId} className="text-[10px] uppercase tracking-wide text-brand-text/50 dark:text-gray-500">Operator</label>
                <select
                  id={operatorId}
                  className="mt-0.5 w-full rounded-lg border border-brand-text/20 px-2 py-1.5 text-xs bg-white dark:bg-gray-900"
                  value={row.op}
                  onChange={e => onOpChange(index, e.target.value)}
                >
                  {ops.map(op => (
                    <option key={op} value={op}>
                      {metadata?.operator_labels?.[op] ?? op.replace(/_/g, ' ')}
                    </option>
                  ))}
                </select>
              </div>
              {showValue && (
                <div className="min-w-[160px] flex-[2]">
                  <label htmlFor={valueId} className="text-[10px] uppercase tracking-wide text-brand-text/50 dark:text-gray-500">Value</label>
                  {isScheduled ? (
                    <select
                      id={valueId}
                      className="mt-0.5 w-full rounded-lg border border-brand-text/20 px-2 py-1.5 text-xs bg-white dark:bg-gray-900"
                      value={String(row.value === true || row.value === 'true' || row.value === 1)}
                      onChange={e => patchCondition(index, { value: e.target.value === 'true' })}
                    >
                      <option value="true">true</option>
                      <option value="false">false</option>
                    </select>
                  ) : (
                    <input
                      id={valueId}
                      type={triggerMeta?.numeric_fields?.includes(row.field) && ['gt', 'gte', 'lt', 'lte', 'equals', 'not_equals'].includes(row.op) ? 'number' : 'text'}
                      className="mt-0.5 w-full rounded-lg border border-brand-text/20 px-2 py-1.5 text-xs bg-white dark:bg-gray-900"
                      value={row.value === null || row.value === undefined ? '' : String(row.value)}
                      onChange={e => {
                        const v = e.target.value
                        if (triggerMeta?.numeric_fields?.includes(row.field) && ['gt', 'gte', 'lt', 'lte'].includes(row.op)) {
                          patchCondition(index, { value: v === '' ? '' : Number(v) })
                        } else {
                          patchCondition(index, { value: v })
                        }
                      }}
                    />
                  )}
                </div>
              )}
              <button
                type="button"
                onClick={() => removeCondition(index)}
                className="p-1.5 rounded-lg text-rose-600 hover:bg-rose-500/10 dark:text-rose-400 mb-0.5"
                aria-label="Remove condition"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          )
        })}
      </div>

      <button
        type="button"
        onClick={addCondition}
        disabled={!fields.length}
        className="text-xs font-medium inline-flex items-center gap-1 text-brand-primary hover:text-brand-secondary disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <Plus className="h-3.5 w-3.5" />
        Add condition
      </button>
    </div>
  )
}
