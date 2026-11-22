import { createServer } from 'node:http'

const port = Number(process.env.PORT || 7777)
const attempts = new Map()

const databases = [
  ['fixture-db-slow-a', 'Slow database A'],
  ['fixture-db-fast-b', 'Fast database B'],
  ['fixture-db-403', 'Forbidden database'],
  ['fixture-db-503-once', 'Retry after 503'],
  ['fixture-db-drop-once', 'Retry after disconnect']
].map(([db_id, display_name]) => ({
  db_id,
  domain_config: { display_name }
}))

const sendJson = (response, status, body) => {
  if (response.destroyed) return
  response.writeHead(status, { 'content-type': 'application/json' })
  response.end(JSON.stringify(body))
}

const sessionPayload = (name) => ({
  data: [{
    session_id: `fixture-${name.toLowerCase().replaceAll(' ', '-')}`,
    session_name: name,
    session_type: 'agent',
    component_id: 'fixture-agent',
    updated_at: '2026-11-22T00:00:00Z'
  }],
  meta: { page: 1, limit: 5, total_pages: 1, total_count: 1 }
})

const server = createServer((request, response) => {
  const url = new URL(request.url || '/', `http://127.0.0.1:${port}`)
  const pathname = url.pathname.replace(/\/$/, '') || '/'

  if (pathname === '/health') {
    return sendJson(response, 200, { status: 'ok' })
  }
  if (pathname === '/info') {
    return sendJson(response, 200, {
      agentos_version: 'fixture',
      agentos_id: 'agent-ui-fixture',
      auth_enabled: true,
      interfaces: []
    })
  }
  if (pathname === '/config') {
    return sendJson(response, 200, {
      agents: [{ id: 'fixture-agent', name: 'Fixture Agent' }],
      teams: [],
      workflows: [{ id: 'fixture-workflow', name: 'Fixture Workflow' }],
      session: { dbs: databases },
      interfaces: [],
      available_models: []
    })
  }
  if (pathname === '/factory/revision') {
    return sendJson(response, 200, { revision: 'fixture-revision' })
  }
  if (pathname === '/agents') return sendJson(response, 200, [])
  if (pathname === '/teams') return sendJson(response, 200, [])
  if (pathname === '/workflows') {
    return sendJson(response, 200, [{
      id: 'fixture-workflow',
      name: 'Fixture Workflow',
      description: 'Synthetic labels only; this workflow is never executed.'
    }])
  }
  if (pathname === '/workflows/fixture-workflow') {
    return sendJson(response, 200, {
      id: 'fixture-workflow',
      name: 'Fixture Workflow',
      steps: [{ name: 'Fallback runtime step', type: 'custom' }]
    })
  }
  if (pathname === '/factory/workflows/fixture-workflow') {
    return sendJson(response, 200, {
      id: 'fixture-workflow',
      name: 'Fixture Workflow',
      revision: 'fixture-revision',
      steps: [
        { name: 'Loop label fixture', type: 'loop' },
        { name: 'Router label fixture', type: 'router' },
        { name: 'Unknown label fixture', type: 'custom_step' }
      ]
    })
  }
  if (pathname === '/sessions') {
    const dbId = url.searchParams.get('db_id') || 'default'
    const attempt = (attempts.get(dbId) || 0) + 1
    attempts.set(dbId, attempt)

    if (dbId === 'fixture-db-403') {
      return sendJson(response, 403, { detail: 'Fixture token is not permitted.' })
    }
    if (dbId === 'fixture-db-503-once' && attempt === 1) {
      return sendJson(response, 503, { detail: 'One-time fixture failure.' })
    }
    if (dbId === 'fixture-db-drop-once' && attempt === 1) {
      response.destroy()
      return
    }

    if (dbId === 'fixture-db-slow-a') {
      return setTimeout(() => sendJson(response, 200, sessionPayload('Slow A result')), 1800)
    }
    if (dbId === 'fixture-db-fast-b') {
      return setTimeout(() => sendJson(response, 200, sessionPayload('Fast B result')), 80)
    }
    if (dbId === 'fixture-db-503-once' || dbId === 'fixture-db-drop-once') {
      return sendJson(response, 200, { data: [], meta: { page: 1, limit: 5, total_pages: 0, total_count: 0 } })
    }
    return sendJson(response, 200, { data: [], meta: { page: 1, limit: 5, total_pages: 0, total_count: 0 } })
  }
  if (pathname === '/metrics') {
    const start = url.searchParams.get('starting_date') || '2026-11-17'
    const end = url.searchParams.get('ending_date') || '2026-11-18'
    const rows = start === end
      ? [{
          date: start,
          agent_runs_count: 2,
          agent_sessions_count: 1,
          team_runs_count: 0,
          team_sessions_count: 0,
          workflow_runs_count: 0,
          workflow_sessions_count: 0,
          users_count: 0,
          token_metrics: { input_tokens: 3, output_tokens: 5 },
          model_metrics: [],
          created_at: `${start}T00:00:00Z`,
          updated_at: `${start}T23:59:59Z`
        }]
      : [start, end].map((date) => ({
          date,
          agent_runs_count: 2,
          agent_sessions_count: 1,
          team_runs_count: 0,
          team_sessions_count: 0,
          workflow_runs_count: 0,
          workflow_sessions_count: 0,
          users_count: 0,
          token_metrics: { input_tokens: 3, output_tokens: 5 },
          model_metrics: [],
          created_at: `${date}T00:00:00Z`,
          updated_at: `${date}T23:59:59Z`
        }))
    return sendJson(response, 200, { metrics: rows, updated_at: '2026-11-22T00:00:00Z' })
  }
  if (pathname.startsWith('/os/metrics/')) {
    const metric = pathname.split('/').at(-1)
    const common = { window_days: 1, updated_at: '2026-11-22T00:00:00Z' }
    if (metric === 'runs') {
      return sendJson(response, 200, {
        ...common,
        total_runs: 2,
        success_rate: 0,
        previous_total_runs: 0,
        change_percent: 100,
        metrics: [{ date: '2026-11-22', runs_count: 2, status_metrics: { ERROR: 2 } }]
      })
    }
    if (metric === 'latency') {
      return sendJson(response, 200, {
        ...common,
        runs_count: 2,
        avg_duration_ms: 500,
        median_duration_ms: 500,
        p95_duration_ms: 500,
        max_duration_ms: 500,
        avg_time_to_first_token_ms: 100,
        p95_time_to_first_token_ms: 100,
        avg_model_call_ms: 250,
        p95_model_call_ms: 250,
        metrics: [{ date: '2026-11-22', runs_count: 2, avg_duration_ms: 500 }]
      })
    }
    if (metric === 'models') {
      return sendJson(response, 200, {
        ...common,
        total_model_runs: 2,
        models: [{ model_id: 'fixture-model', model_provider: 'fixture', runs_count: 2, runs_share: 100 }]
      })
    }
    if (metric === 'sessions') {
      return sendJson(response, 200, {
        ...common,
        total_sessions: 1,
        previous_total_sessions: 0,
        change_percent: 100,
        metrics: [{ date: '2026-11-22', sessions_count: 1 }]
      })
    }
    if (metric === 'tokens') {
      return sendJson(response, 200, {
        ...common,
        total_tokens: 8,
        previous_total_tokens: 0,
        change_percent: 100,
        metrics: [{ date: '2026-11-22', tokens_count: 8 }]
      })
    }
    if (metric === 'users') {
      return sendJson(response, 503, { detail: 'Fixture user directory is not configured.' })
    }
  }
  if (pathname === '/approvals' || pathname === '/queue') {
    return sendJson(response, 503, { detail: 'Fixture capability is disabled.' })
  }
  if (pathname === '/registry') {
    return sendJson(response, 200, { data: [], meta: { page: 1, limit: 10, total_pages: 0, total_count: 0 } })
  }

  return sendJson(response, 404, { detail: 'Fixture route not found.' })
})

server.listen(port, '0.0.0.0', () => {
  process.stdout.write(`Mock AgentOS fixture listening on ${port}\n`)
})
