import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../app/api'

type User = {
  id: string
  email: string
  full_name: string | null
  role: string
  is_active: boolean
  created_at: string
}

type Tx = {
  id: string
  amount_cents: number
  method: string
  status: string
  purpose: string
  created_at: string
}

type GateStatus = {
  entrance_fee_cents: number
  cash_accumulated_cents: number
  door_unlock_seconds: number
}

function formatMoney(cents: number) {
  return `₪${(cents / 100).toFixed(2)}`
}

export function AdminPage() {
  const [users, setUsers] = useState<User[]>([])
  const [txs, setTxs] = useState<Tx[]>([])
  const [hardwareStatus, setHardwareStatus] = useState<any>(null)
  const [gateStatus, setGateStatus] = useState<GateStatus | null>(null)

  useEffect(() => {
    api.get<User[]>('/users/admin/users').then((r) => setUsers(r.data)).catch(() => {})
    api.get<Tx[]>('/payments/transactions').then((r) => setTxs(r.data)).catch(() => {})
    api.get('/hardware/status').then((r) => setHardwareStatus(r.data)).catch(() => {})
    api.get<GateStatus>('/access/healthz').then((r) => setGateStatus(r.data)).catch(() => {})
  }, [])

  return (
    <div style={{ maxWidth: 980, margin: '24px auto', padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0 }}>Admin</h2>
        <Link to="/dashboard">Back</Link>
      </div>

      <div style={{ height: 16 }} />

      <section style={{ border: '1px solid #ddd', borderRadius: 12, padding: 16, marginBottom: 16 }} dir="rtl">
        <h3 style={{ marginTop: 0 }}>הגדרות שער</h3>
        {gateStatus ? (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: 14, color: '#6b7280' }}>עלות כניסה</div>
                <div style={{ fontSize: 28, fontWeight: 600 }}>{formatMoney(gateStatus.entrance_fee_cents)}</div>
              </div>
              <div>
                <div style={{ fontSize: 14, color: '#6b7280' }}>זמן פתיחת דלת</div>
                <div style={{ fontSize: 28, fontWeight: 600 }}>{gateStatus.door_unlock_seconds} שניות</div>
              </div>
            </div>
            <p style={{ fontSize: 14, color: '#6b7280', margin: 0, textAlign: 'right' }}>
              לשינוי ערוך בקובץ <code>services/access-control-service/.env</code>:
              <br />
              <code>ENTRANCE_FEE_CENTS</code> (באגורות, למשל 500 = ₪5)
              <br />
              <code>DOOR_UNLOCK_SECONDS</code> (שניות, למשל 5)
              <br />
              ואז הפעל מחדש: <code>docker compose up -d access-control-service</code>
            </p>
          </>
        ) : (
          <div>טוען…</div>
        )}
      </section>

      <section style={{ border: '1px solid #ddd', borderRadius: 12, padding: 16 }}>
        <h3 style={{ marginTop: 0 }}>Hardware status</h3>
        <pre style={{ margin: 0, fontSize: 12 }}>{hardwareStatus ? JSON.stringify(hardwareStatus, null, 2) : 'Loading…'}</pre>
        <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
          <button
            onClick={() =>
              gateStatus &&
              api.post('/hardware/door/open', { seconds: gateStatus.door_unlock_seconds })
            }
          >
            פתח דלת ({gateStatus?.door_unlock_seconds ?? '…'} שניות)
          </button>
        </div>
      </section>

      <div style={{ height: 16 }} />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <section style={{ border: '1px solid #ddd', borderRadius: 12, padding: 16 }}>
          <h3 style={{ marginTop: 0 }}>Users</h3>
          <div style={{ maxHeight: 360, overflow: 'auto' }}>
            {users.map((u) => (
              <div key={u.id} style={{ padding: '8px 0', borderBottom: '1px solid #eee' }}>
                <b>{u.email}</b> — {u.role} — {u.is_active ? 'active' : 'disabled'}
              </div>
            ))}
            {!users.length && <div style={{ opacity: 0.7 }}>No users or not authorized.</div>}
          </div>
        </section>

        <section style={{ border: '1px solid #ddd', borderRadius: 12, padding: 16 }}>
          <h3 style={{ marginTop: 0 }}>Transactions</h3>
          <div style={{ maxHeight: 360, overflow: 'auto' }}>
            {txs.map((t) => (
              <div key={t.id} style={{ padding: '8px 0', borderBottom: '1px solid #eee' }}>
                <div>
                  <b>{t.status}</b> {t.method} {t.amount_cents} — {t.purpose}
                </div>
                <div style={{ opacity: 0.7, fontSize: 12 }}>{new Date(t.created_at).toLocaleString()}</div>
              </div>
            ))}
            {!txs.length && <div style={{ opacity: 0.7 }}>No transactions.</div>}
          </div>
        </section>
      </div>
    </div>
  )
}

