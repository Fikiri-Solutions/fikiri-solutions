import { useEffect, useState } from 'react'
import { createClient } from '@/utils/supabase/client'

type TodoRow = { id: string; name: string }

/**
 * Client-side equivalent of the Next.js App Router example that uses `cookies()` +
 * `createServerClient`. Wire a route in `App.tsx` if you want to open this page.
 */
export default function SupabaseTodosDemo() {
  const [todos, setTodos] = useState<TodoRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      try {
        const supabase = createClient()
        const { data, error: qErr } = await supabase.from('todos').select()
        if (qErr) throw qErr
        if (!cancelled) setTodos(data ?? [])
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load todos')
      }
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [])

  if (error) {
    return <p className="text-sm text-red-600">{error}</p>
  }
  if (todos === null) {
    return <p className="text-sm text-muted-foreground">Loading…</p>
  }

  return (
    <ul className="list-inside list-disc text-sm">
      {todos.map((todo) => (
        <li key={todo.id}>{todo.name}</li>
      ))}
    </ul>
  )
}
