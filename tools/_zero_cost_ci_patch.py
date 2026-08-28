from pathlib import Path

path = Path('.github/workflows/test.yml')
text = path.read_text(encoding='utf-8')

old_steps = '''      - name: Test
        run: pytest -q
      - name: Lint
        run: ruff check --select E4,E7,E9,F .
      - name: Verify Observatory frontend
        working-directory: apps/observatory
        run: npm run verify

'''
new_steps = '''      - name: Validate zero-cost runtime policy
        run: python scripts/validate_zero_cost_runtime.py
      - name: Compile Python sources
        run: python -m compileall -q api apps/api brain scripts tools tests
      - name: Targeted Turso and migration contracts
        run: pytest -q tests/test_turso_persistence.py tests/test_railway_turso_migration.py
      - name: Full test suite
        run: pytest -q
      - name: Ruff static checks
        run: ruff check --select E4,E7,E9,F .
      - name: Verify Observatory frontend
        working-directory: apps/observatory
        run: npm run verify

'''
if text.count(old_steps) != 1:
    raise SystemExit(f'expected one test-step block, found {text.count(old_steps)}')
text = text.replace(old_steps, new_steps)

marker = '  container-integration:\n'
if text.count(marker) != 1:
    raise SystemExit(f'expected one container job marker, found {text.count(marker)}')

fixture = '''  zero-cost-migration-fixture:
    name: Zero-cost migration fixture
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: brain
          POSTGRES_PASSWORD: brain
          POSTGRES_DB: brain
        ports:
          - 55433:5432
        options: >-
          --health-cmd "pg_isready -U brain -d brain"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 12
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install
        run: pip install -c constraints.txt -e '.[dev]'
      - name: Seed deterministic PostgreSQL source fixture
        env:
          FIXTURE_DSN: postgresql://brain:brain@127.0.0.1:55433/brain
        run: |
          python - <<'PY'
          import os
          import psycopg

          dsn = os.environ['FIXTURE_DSN']
          events = [
              ('00000000-0000-0000-0000-000000000001','signal.enqueued','signal','00000000-0000-0000-0000-000000000101',None,'00000000-0000-0000-0000-000000000201','{"sequence":1}','2026-08-28T12:00:00+00:00'),
              ('00000000-0000-0000-0000-000000000002','belief.created','belief','00000000-0000-0000-0000-000000000102','00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000201','{"sequence":2}','2026-08-28T12:00:01+00:00'),
              ('00000000-0000-0000-0000-000000000003','cycle.completed','cycle','00000000-0000-0000-0000-000000000103','00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000201','{"sequence":3}','2026-08-28T12:00:02+00:00'),
          ]
          with psycopg.connect(dsn) as conn:
              conn.execute('''CREATE TABLE public.brain_events(
                  id uuid PRIMARY KEY,
                  event_type text NOT NULL,
                  aggregate_type text NOT NULL,
                  aggregate_id uuid NOT NULL,
                  causation_id uuid,
                  correlation_id uuid,
                  payload jsonb NOT NULL,
                  occurred_at timestamptz NOT NULL
              )''')
              conn.execute('CREATE TABLE public.migration_fixture_notes(id text PRIMARY KEY,payload text NOT NULL)')
              conn.executemany('''INSERT INTO public.brain_events(
                  id,event_type,aggregate_type,aggregate_id,causation_id,correlation_id,payload,occurred_at
              ) VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s)''', events)
              conn.execute("INSERT INTO public.migration_fixture_notes VALUES ('fixture-1','complete-extra-table-row')")
          PY
      - name: Convert and verify deterministic PostgreSQL to SQLite fixture
        env:
          FIXTURE_DSN: postgresql://brain:brain@127.0.0.1:55433/brain
        run: |
          set -euo pipefail
          rm -rf migration-fixture-evidence /tmp/brain-zero-cost-fixture.sqlite
          mkdir -p migration-fixture-evidence
          python tools/railway_turso_migration.py convert \
            --postgres-dsn "$FIXTURE_DSN" \
            --sqlite /tmp/brain-zero-cost-fixture.sqlite \
            --evidence-dir migration-fixture-evidence
          python tools/verify_event_replay_equivalence.py \
            --postgres-dsn "$FIXTURE_DSN" \
            --sqlite /tmp/brain-zero-cost-fixture.sqlite \
            --output migration-fixture-evidence/replay_equivalence.json
          python tools/railway_turso_migration.py verify-sqlite \
            --sqlite /tmp/brain-zero-cost-fixture.sqlite \
            --evidence-dir migration-fixture-evidence/independent
          python - <<'PY'
          import hashlib
          import json
          from pathlib import Path

          evidence = Path('migration-fixture-evidence')
          sqlite_path = Path('/tmp/brain-zero-cost-fixture.sqlite')
          counts = json.loads((evidence / 'source_counts.json').read_text())
          migration = json.loads((evidence / 'migration_verification.json').read_text())
          replay = json.loads((evidence / 'replay_equivalence.json').read_text())
          independent = json.loads((evidence / 'independent/sqlite_full_verification.json').read_text())
          if counts.get('brain_events') != 3:
              raise SystemExit(f"expected 3 canonical events, got {counts.get('brain_events')}")
          if counts.get('migration_fixture_notes') != 1:
              raise SystemExit(f"expected 1 extra-table row, got {counts.get('migration_fixture_notes')}")
          if not migration.get('verified') or not replay.get('verified') or not independent.get('verified'):
              raise SystemExit('fixture migration/replay/independent verification did not all pass')
          digest = hashlib.sha256(sqlite_path.read_bytes()).hexdigest()
          summary = {
              'verified': True,
              'source_counts': counts,
              'source_table_count': migration['source_table_count'],
              'source_row_count': migration['source_row_count'],
              'event_replay_count': replay['source']['event_count'],
              'event_replay_sha256': replay['source']['sha256_replay'],
              'sqlite_sha256': digest,
              'sqlite_bytes': sqlite_path.stat().st_size,
              'independent_table_count': independent['table_count'],
              'independent_row_count': independent['row_count'],
          }
          (evidence / 'fixture-summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
          print(json.dumps(summary, indent=2, sort_keys=True))
          PY
      - name: Upload migration fixture evidence
        uses: actions/upload-artifact@v4
        with:
          name: migration-fixture-evidence
          path: migration-fixture-evidence/**
          if-no-files-found: error
          retention-days: 7

'''
text = text.replace(marker, fixture + marker)
path.write_text(text, encoding='utf-8')
