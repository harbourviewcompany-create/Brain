"""Verify the constrained runtime login holds the privileges its queries need.

Migrations 021, 022 and 025 hand out privileges through `do $$ ... $$` loops that
read `information_schema.columns` or iterate a literal array. Those loops are
evaluated once, when their migration runs, so they can only ever cover objects
that exist at that moment and match that migration's shape. An object created
later, or a pre-tenant table carrying no `tenant_id`, silently ends up with row
level security enabled and no grant at all -- invisible to the non-owner
`brain_runtime_role` login the release topology requires, while remaining fully
readable to the owner that CI and single-role installations happen to use.

That failure mode is not observable from the migration files alone, so this runs
against a real database after `tools/apply_migrations.py` and asserts the property
directly. Reachability is not a single bit: a table the runtime writes needs more
than SELECT, and an INSERT into a sequence-backed table needs USAGE on the
sequence that migration 022 granted once, in bulk, to the sequences that existed
then. So every public table is checked against the privilege set its callers
actually need, every public sequence against USAGE and SELECT, and the two
deliberately read-only global catalogues are checked for the *absence* of write
privileges so that boundary cannot widen unnoticed.
"""

from __future__ import annotations

import argparse
import os

import psycopg


RUNTIME_ROLE = "brain_runtime_role"

#: What a tenant-owned runtime table needs. The runtime reads and writes these
#: through the ordinary adapters, so SELECT alone is not reachability: narrowing
#: a grant to SELECT would leave inserts failing at runtime with CI still green.
FULL_DML: tuple[str, ...] = ("select", "insert", "update", "delete")

#: Privileges no runtime table may grant the constrained role, whatever else it
#: holds. TRUNCATE is the dangerous one: PostgreSQL does not apply row level
#: security to it, so a tenant runtime holding TRUNCATE could empty every
#: tenant's rows from a table whose per-row policies look airtight. `grant all`
#: hands it over silently, which is why this is checked as an upper bound on
#: every table rather than only on the ones documented as read-only.
FORBIDDEN_PRIVILEGES: tuple[str, ...] = ("truncate",)

#: Sequence privileges migration 022 grants in bulk. An INSERT into a
#: sequence-backed table fails with "permission denied for sequence" without them.
SEQUENCE_PRIVILEGES: tuple[str, ...] = ("usage", "select")

# Tables the runtime may read but must never write. Checked in both directions:
# the SELECT must be present, and every write privilege must be absent.
READ_ONLY_TABLES: dict[str, str] = {
    # Migration 022 grants SELECT and then explicitly revokes DML. Tenant
    # lifecycle mutation waits on a durable administration service.
    "tenants": "read-only by migration 022",
    "tenant_memberships": "read-only by migration 022",
}

# Tables that belong to the audited trusted worker alone. The ordinary API
# runtime is granted nothing on these, and the service role must keep the
# privileges its adapters need -- checking only the runtime side would let a
# later revoke strand the worker with this gate still green.
#
# These are referenced by runtime SQL, unlike EXPECTED_UNGRANTED, but only from
# code the worker process runs: brain/connectors/service.py is imported solely by
# apps/worker/main.py, and the tenant API's TenantRevenueStore overrides every
# global write to a no-op and reconstructs learning from tenant-owned outcomes.
TRUSTED_SERVICE_ONLY: dict[str, str] = {
    "source_connector_runtime_state": "worker-only acquisition state (migration 026)",
    "source_connector_ingestion_runs": "worker-only acquisition state (migration 026)",
    "source_connector_observations": "worker-only acquisition state (migration 026)",
    "money_lanes": "global money-lane catalogue, service-context only (migration 026)",
    "revenue_source_scores": "global source learning, service-context only (migration 026)",
}

#: What the trusted worker must hold on the tables above. Migration 026 grants
#: these three; DELETE is deliberately not among them.
TRUSTED_SERVICE_PRIVILEGES: tuple[str, ...] = ("select", "insert", "update")

TRUSTED_SERVICE_ROLE = "brain_trusted_service_role"

# Tables the constrained runtime login is deliberately not granted at all.
#
# Each entry must stay unreferenced by runtime SQL -- tests/test_runtime_grant_coverage.py
# fails if any of these names appears in a query under brain/ or apps/, so adding a
# reader forces the grant question back open rather than reintroducing the
# permission-denied class of bug this file exists to catch. tools/ is deliberately
# out of scope: those run under the migration DSN as the table owner.
EXPECTED_UNGRANTED: dict[str, str] = {
    # Created by tools/apply_migrations.py itself, not by a migration. Only the
    # migrator and the release verifiers read it, both under the migration DSN.
    "brain_schema_migrations": "migration ledger, owned by the migrator",
    # Migration 022 revokes these outright: invite and audit rows are reachable
    # only under trusted service context.
    "tenant_invites": "service-context only, revoked by migration 022",
    "tenant_audit_events": "service-context only, revoked by migration 022",
    # Migrations 008-010 registries. Documentation/traceability tables with no
    # runtime reader; they are populated by migration and read by operators.
    "brain_region_maps": "no runtime reader",
    "implementation_hypotheses": "no runtime reader",
    "mechanistic_gaps": "no runtime reader",
    "multiscale_cognition_dependencies": "no runtime reader",
    "multiscale_cognition_levels": "no runtime reader",
    "neuro_abstractions": "no runtime reader",
    "neuro_acceptance_reports": "no runtime reader",
    "neuro_scale_levels": "no runtime reader",
    "neuro_theories": "no runtime reader",
    "neuro_theory_conflicts": "no runtime reader",
    "neuro_unknown_mechanisms": "no runtime reader",
}


def _dsn(name: str) -> str:
    """Read a required DSN from the environment, failing loudly when it is unset."""

    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def required_privileges(table: str) -> tuple[str, ...]:
    """Return the privileges `table` must grant the runtime role."""

    if table in EXPECTED_UNGRANTED or table in TRUSTED_SERVICE_ONLY:
        return ()
    if table in READ_ONLY_TABLES:
        return ("select",)
    return FULL_DML


def table_privileges(conn: psycopg.Connection) -> dict[str, set[str]]:
    """Return the privileges the runtime role actually holds, keyed by table.

    Asked as one cross join rather than a query per table-and-privilege: the
    forbidden set is inspected alongside the DML set so that `grant all` shows up
    here, rather than being invisible because only DML was ever looked at.
    """

    rows = conn.execute(
        """
        select c.relname, p.privilege
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        cross join unnest(%s::text[]) as p(privilege)
        where n.nspname = 'public'
          and c.relkind in ('r', 'p')
          and has_table_privilege(%s, c.oid, p.privilege)
        """,
        (list(FULL_DML + FORBIDDEN_PRIVILEGES), RUNTIME_ROLE),
    ).fetchall()
    held: dict[str, set[str]] = {}
    for name, privilege in rows:
        held.setdefault(name, set()).add(privilege)
    return held


def public_tables(conn: psycopg.Connection) -> list[str]:
    """Return every public table whose ACL the runtime is actually checked against.

    `relkind = 'p'` is included deliberately. A partitioned table's privileges are
    checked on the parent that callers name, so enumerating ordinary tables alone
    would skip the object that decides access and, worse, treat its child
    partitions as standalone runtime tables needing their own direct grants.
    """

    return [
        row[0]
        for row in conn.execute(
            "select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace"
            " where n.nspname = 'public' and c.relkind in ('r', 'p')"
            " and not exists (select 1 from pg_inherits i where i.inhrelid = c.oid)"
            " order by c.relname"
        ).fetchall()
    ]


def unpolicied_tables(conn: psycopg.Connection) -> list[str]:
    """Return RLS-enabled public tables that carry no policy at all.

    RLS with no policy denies every non-owner regardless of grants, so a grant
    check alone cannot prove reachability for the constrained login.
    """

    return [
        row[0]
        for row in conn.execute(
            """
            select c.relname
            from pg_class c
            join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = 'public'
              and c.relkind = 'r'
              and c.relrowsecurity
              and not exists (select 1 from pg_policy p where p.polrelid = c.oid)
            order by c.relname
            """
        ).fetchall()
    ]


def sequence_owners(conn: psycopg.Connection) -> list[tuple[str, str | None]]:
    """Return every public sequence paired with the table that owns it, if any."""

    rows = conn.execute(
        """
        select s.relname, t.relname
        from pg_class s
        join pg_namespace n on n.oid = s.relnamespace
        left join pg_depend d
          on d.objid = s.oid
         and d.classid = 'pg_class'::regclass
         and d.deptype in ('a', 'i')
        left join pg_class t on t.oid = d.refobjid
        where n.nspname = 'public' and s.relkind = 'S'
        order by s.relname
        """
    ).fetchall()
    return [(row[0], row[1]) for row in rows]


#: pg_policy.polcmd, keyed by the privilege each command letter authorises.
_POLICY_COMMANDS: dict[str, str] = {"select": "r", "insert": "a", "update": "w", "delete": "d"}


def policy_coverage_gaps(conn: psycopg.Connection) -> list[str]:
    """Return (table, privilege) pairs whose grant no row level policy can satisfy.

    A grant is only half of reachability. With RLS enabled, an operation also needs
    a policy that covers it, and the two fail differently: a missing *policy* on
    SELECT is silent -- the read succeeds and returns nothing -- so neither an ACL
    check nor a probe read can tell it from an empty table. Only the policy
    catalogue distinguishes them, so per-command coverage is checked structurally.
    """

    rows = conn.execute(
        """
        select c.relname, coalesce(array_agg(distinct p.polcmd), '{}')
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        left join pg_policy p on p.polrelid = c.oid
        where n.nspname = 'public'
          and c.relkind in ('r', 'p')
          and c.relrowsecurity
        group by c.relname
        order by c.relname
        """
    ).fetchall()

    gaps: list[str] = []
    for table, commands in rows:
        covered = {str(command) for command in commands if command is not None}
        for privilege in required_privileges(table):
            letter = _POLICY_COMMANDS[privilege]
            if letter not in covered and "*" not in covered:
                gaps.append(f"{table} ({privilege})")
    return gaps


def ungranted_sequences(conn: psycopg.Connection) -> list[tuple[str, str]]:
    """Return (sequence, missing privilege) pairs that would break a runtime insert.

    Only sequences backing a table the runtime inserts into are required. A
    sequence owned by a deliberately withheld table must *not* drag a grant along
    with it: that would let the runtime consume values from a table it may never
    write. An unowned sequence has no table to classify it by, so it is required
    conservatively -- anything creating a free-standing sequence in this schema is
    doing something the runtime probably uses directly.
    """

    required: list[str] = []
    for sequence, owner in sequence_owners(conn):
        if owner is not None and "insert" not in required_privileges(owner):
            continue
        required.append(sequence)
    if not required:
        return []

    rows = conn.execute(
        """
        select c.relname, p.privilege
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        cross join unnest(%s::text[]) as p(privilege)
        where n.nspname = 'public'
          and c.relkind = 'S'
          and c.relname = any(%s::text[])
          and not has_sequence_privilege(%s, c.oid, p.privilege)
        order by c.relname, p.privilege
        """,
        (list(SEQUENCE_PRIVILEGES), required, RUNTIME_ROLE),
    ).fetchall()
    return [(row[0], row[1]) for row in rows]


def trusted_service_write_gaps(conn: psycopg.Connection) -> list[str]:
    """Return global catalogues the trusted worker can no longer write.

    The read-only boundary on these tables only makes sense if someone can still
    persist to them. Checking the runtime role's *absence* of writes without
    checking the service role's *presence* would let a later revoke silently strand
    `seed_lanes()`, `save_lane_priority()` and `save_source_score()`.
    """

    gaps: list[str] = []
    for table in TRUSTED_SERVICE_ONLY:
        if conn.execute("select to_regclass(%s)", (f"public.{table}",)).fetchone()[0] is None:
            continue
        missing = [
            privilege
            for privilege in TRUSTED_SERVICE_PRIVILEGES
            if not conn.execute(
                "select has_table_privilege(%s, %s, %s)",
                (TRUSTED_SERVICE_ROLE, f"public.{table}", privilege),
            ).fetchone()[0]
        ]
        if missing:
            gaps.append(f"{table} (missing {', '.join(missing)})")
    return gaps


def verify(conn: psycopg.Connection) -> None:
    """Assert the whole privilege model against `conn`, raising on the first failure.

    Ordered cheapest-first so the message a reader gets names the root cause rather
    than a consequence: a table that vanished is reported before the privileges it
    no longer has, and a missing RLS policy before the grant it makes useless.
    """

    if conn.execute("select to_regrole(%s)", (RUNTIME_ROLE,)).fetchone()[0] is None:
        raise RuntimeError(f"{RUNTIME_ROLE} is missing; apply migration 019 first")

    present = public_tables(conn)
    held = table_privileges(conn)

    unpolicied = [t for t in unpolicied_tables(conn) if required_privileges(t)]
    if unpolicied:
        raise RuntimeError(
            "row level security is enabled with no policy, so the constrained runtime "
            "login is denied regardless of its grants: " + ", ".join(unpolicied)
        )

    known = set(present)
    vanished = sorted(
        name
        for name in (READ_ONLY_TABLES.keys() | TRUSTED_SERVICE_ONLY.keys())
        if name not in known
    )
    if vanished:
        raise RuntimeError(
            "tables this verifier makes claims about are no longer in the schema: "
            + ", ".join(vanished)
            + ". A rename carries the old ACL to the new name, so the privilege checks "
            "would keep passing while the adapters query a table that no longer exists. "
            "Update tools/verify_runtime_grant_coverage.py and the adapters together."
        )

    missing: list[str] = []
    excess: list[str] = []
    forbidden: list[str] = []
    for table in present:
        required = set(required_privileges(table))
        actual = held.get(table, set())

        absent = sorted(required - actual)
        if absent:
            missing.append(f"{table} (missing {', '.join(absent)})")

        # TRUNCATE is refused on every table, not just the documented ones: row
        # level security does not apply to it, so it is an upper bound even where
        # full DML is expected.
        held_forbidden = sorted(actual & set(FORBIDDEN_PRIVILEGES))
        if held_forbidden:
            forbidden.append(f"{table} (holds {', '.join(held_forbidden)})")

        # A table listed as read-only or withheld must not quietly gain writes.
        # Only those two lists constrain the DML upper bound; a tenant-owned table
        # holding full DML is the expected case, not an excess.
        if table in READ_ONLY_TABLES or table in EXPECTED_UNGRANTED or table in TRUSTED_SERVICE_ONLY:
            unexpected = sorted((actual & set(FULL_DML)) - required)
            if unexpected:
                excess.append(f"{table} (unexpected {', '.join(unexpected)})")

    if missing:
        raise RuntimeError(
            "the constrained runtime login lacks privileges its queries need: "
            + "; ".join(missing)
            + ". Grant them in a migration, or record the table in READ_ONLY_TABLES "
            "or EXPECTED_UNGRANTED in tools/verify_runtime_grant_coverage.py with a reason."
        )
    if excess:
        raise RuntimeError(
            "tables documented as read-only, trusted-worker only, or withheld hold "
            "privileges beyond what they allow: " + "; ".join(excess)
            + ". Revoke them, or update tools/verify_runtime_grant_coverage.py if the "
            "trust boundary really did change."
        )
    if forbidden:
        raise RuntimeError(
            f"{RUNTIME_ROLE} holds privileges no runtime table may grant it: "
            + "; ".join(forbidden)
            + ". PostgreSQL does not apply row level security to TRUNCATE, so this "
            "would let one tenant's runtime empty every tenant's rows. Revoke it -- "
            "`grant all` is usually the cause; grant the four DML privileges instead."
        )

    policy_gaps = policy_coverage_gaps(conn)
    if policy_gaps:
        raise RuntimeError(
            "row level security is enabled but no policy covers operations the "
            "constrained runtime login is granted: " + "; ".join(policy_gaps)
            + ". The grant is intact, so nothing else in this gate notices -- a "
            "missing SELECT policy makes the read return no rows rather than fail."
        )

    service_gaps = trusted_service_write_gaps(conn)
    if service_gaps:
        raise RuntimeError(
            f"{TRUSTED_SERVICE_ROLE} can no longer use the tables it owns: "
            + "; ".join(service_gaps)
            + ". The ordinary runtime role is granted nothing on these by design, so "
            "revoking the service role's access leaves nothing able to use them at all."
        )

    sequence_gaps = ungranted_sequences(conn)
    if sequence_gaps:
        raise RuntimeError(
            "the constrained runtime login cannot use sequences its inserts need: "
            + "; ".join(f"{name} (missing {privilege})" for name, privilege in sequence_gaps)
            + ". Migration 022's `grant ... on all sequences` covers only the sequences "
            "that existed when it ran, so a later sequence needs its own grant."
        )

    stale = sorted(
        name
        for name in (EXPECTED_UNGRANTED.keys() | READ_ONLY_TABLES.keys() | TRUSTED_SERVICE_ONLY.keys())
        if name in known and held.get(name, set()) != set(required_privileges(name))
    )
    if stale:  # pragma: no cover - unreachable while the two checks above pass
        raise RuntimeError("privilege documentation is out of date for: " + ", ".join(stale))

    writable = sum(1 for table in present if required_privileges(table) == FULL_DML)
    owners = sequence_owners(conn)
    required_sequences = sum(
        1
        for _, owner in owners
        if owner is None or "insert" in required_privileges(owner)
    )
    print(
        f"runtime grant coverage verified: {writable} tables writable by {RUNTIME_ROLE}, "
        f"{len(READ_ONLY_TABLES)} read-only, "
        f"{len(TRUSTED_SERVICE_ONLY)} trusted-worker only, "
        f"{len(EXPECTED_UNGRANTED)} withheld, "
        f"{required_sequences} of {len(owners)} sequences usable, "
        f"no {', '.join(FORBIDDEN_PRIVILEGES)} anywhere",
        flush=True,
    )


def verify_effective_login(conn: psycopg.Connection, present: list[str]) -> None:
    """Verify the model through the connection the API actually uses.

    Everything above reasons about `brain_runtime_role`. The API authenticates as
    a login role that is only a *member* of it, so a direct grant on the login, or
    membership in some other ACL-bearing role, can hand it privileges the role
    itself does not carry -- and `require_safe_runtime_role` rejects owner,
    superuser, BYPASSRLS and trusted-service identities without excluding that.

    Row level security is checked the only way it can be: by reading. ACLs say
    nothing about policies, so a narrowed or dropped policy leaves the grants
    intact while the constrained login silently reads nothing. The owner DSN
    cannot see this at all -- owners bypass RLS on tables that are not FORCEd.

    Reads only. Proving writes would mean writing rows into the database being
    verified, and a verifier with side effects is worse than a narrower one.
    """

    effective = conn.execute("select current_user").fetchone()[0]

    forbidden: list[str] = []
    excess: list[str] = []
    for table in present:
        required = set(required_privileges(table))
        for privilege in FORBIDDEN_PRIVILEGES:
            if conn.execute(
                "select has_table_privilege(%s, %s)", (f"public.{table}", privilege)
            ).fetchone()[0]:
                forbidden.append(f"{table} ({privilege})")
        if table in READ_ONLY_TABLES or table in EXPECTED_UNGRANTED or table in TRUSTED_SERVICE_ONLY:
            for privilege in set(FULL_DML) - required:
                if conn.execute(
                    "select has_table_privilege(%s, %s)", (f"public.{table}", privilege)
                ).fetchone()[0]:
                    excess.append(f"{table} ({privilege})")

    if forbidden:
        raise RuntimeError(
            f"the runtime login {effective!r} holds forbidden privileges directly, "
            f"even though {RUNTIME_ROLE} does not: " + "; ".join(sorted(forbidden))
        )
    if excess:
        raise RuntimeError(
            f"the runtime login {effective!r} holds privileges on tables documented as "
            f"read-only, trusted-worker only, or withheld that {RUNTIME_ROLE} does not: " + "; ".join(sorted(excess))
            + ". Look for a direct grant on the login or membership in another role."
        )

    unreadable: list[str] = []
    for table in present:
        if "select" not in required_privileges(table):
            continue
        try:
            conn.execute(f'select 1 from public."{table}" limit 1').fetchone()
        except psycopg.Error as exc:
            unreadable.append(f"{table} ({exc.diag.sqlstate or type(exc).__name__})")
            conn.rollback()

    if unreadable:
        raise RuntimeError(
            f"the runtime login {effective!r} cannot read tables its queries need: "
            + "; ".join(unreadable)
            + ". Grants alone cannot prove this -- a dropped or narrowed row level "
            "security policy leaves the ACL intact while the read is refused."
        )

    print(
        f"effective runtime login verified: {effective} reads every table it must, "
        f"holds no forbidden privilege, and cannot write the read-only catalogues",
        flush=True,
    )


def main() -> int:
    """Run the role-level checks, then re-run the model as the effective login.

    The second pass needs a constrained DSN and is skipped -- loudly -- when none is
    configured, so the role-level guarantee still holds everywhere this runs.
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dsn-env",
        default="BRAIN_MIGRATION_DATABASE_URL",
        help="environment variable holding the database DSN to inspect",
    )
    parser.add_argument(
        "--runtime-dsn-env",
        default="DATABASE_URL",
        help=(
            "environment variable holding the constrained runtime DSN. When set, the "
            "model is re-checked through the login the API actually authenticates as."
        ),
    )
    args = parser.parse_args()

    with psycopg.connect(_dsn(args.dsn_env), autocommit=True) as conn:
        verify(conn)
        present = public_tables(conn)

    runtime_dsn = os.environ.get(args.runtime_dsn_env)
    if not runtime_dsn:
        print(
            f"{args.runtime_dsn_env} is not set; skipping the effective-login check "
            "(role-level privileges were still verified)",
            flush=True,
        )
        return 0

    with psycopg.connect(runtime_dsn) as runtime_conn:
        verify_effective_login(runtime_conn, present)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
