import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../app/api'
import './DashboardPage.css'

type GateStatus = {
  cash_accumulated_cents: number
  entrance_fee_cents: number
  door_unlock_seconds: number
}

type ChipToast = {
  kind: 'granted' | 'denied'
  title: string
  message: string
  balanceCents: number | null
  balanceLabel?: string
}

type WsEvent = {
  type?: string
  method?: string
  uid?: string | null
  reason?: string
  balance_cents?: number
  balance_after_cents?: number
  fee_cents?: number
  amount_cents?: number
  total_cents?: number
  required_cents?: number
  remaining_cents?: number
}

type AccessDecision = {
  granted: boolean
  reason: string
  fee_cents: number
  balance_before_cents?: number | null
  balance_after_cents?: number | null
}

type SimulateCashResult = {
  granted: boolean
  accumulated_cents: number
  entrance_fee_cents: number
  remaining_cents: number
}

function formatMoney(cents: number) {
  return `₪${(cents / 100).toFixed(2)}`
}

function grantedToast(event: { balance_after_cents?: number; remaining_cents?: number; method?: string }): ChipToast {
  const isCash = event.method === 'cash'
  const changeCents = event.remaining_cents ?? 0
  return {
    kind: 'granted',
    title: 'הדלת נפתחה',
    message: isCash ? 'תשלום התקבל בהצלחה. ברוך הבא!' : 'ניכוי עלות כניסה בוצע בהצלחה. ברוך הבא!',
    balanceCents: isCash
      ? changeCents > 0
        ? changeCents
        : null
      : (event.balance_after_cents ?? null),
    balanceLabel: isCash ? 'עודף' : 'יתרה נותרת בצ\'יפ',
  }
}

function isCashGrantedEvent(event: WsEvent): boolean {
  return (
    event.type === 'access.granted' &&
    (event.method === 'cash' || event.reason === 'cash_paid')
  )
}

function chipToastFromEvent(event: WsEvent): ChipToast | null {
  if (isCashGrantedEvent(event)) {
    return grantedToast({ method: 'cash', remaining_cents: event.remaining_cents })
  }

  if (event.type === 'access.granted' && event.uid) {
    return grantedToast(event)
  }

  if (event.type === 'access.denied' && event.uid != null) {
    const balance = event.balance_cents ?? null
    if (event.reason === 'insufficient_balance') {
      const fee = event.fee_cents
      return {
        kind: 'denied',
        title: 'אין מספיק יתרה',
        message:
          fee != null
            ? `נדרשים ${formatMoney(fee)} לכניסה. אנא טען את הצ'יפ או שלם במזומן.`
            : 'אין מספיק יתרה בצ\'יפ. אנא טען או שלם במזומן.',
        balanceCents: balance,
      }
    }
    if (event.reason === 'chip_disabled') {
      return {
        kind: 'denied',
        title: 'צ\'יפ חסום',
        message: 'הצ\'יפ הזה אינו פעיל. פנה למנהל המערכת.',
        balanceCents: balance,
      }
    }
    if (event.reason === 'unknown_chip') {
      return {
        kind: 'denied',
        title: 'צ\'יפ לא מזוהה',
        message: 'הצ\'יפ לא רשום במערכת.',
        balanceCents: null,
      }
    }
  }

  return null
}

function chipToastFromDecision(decision: AccessDecision): ChipToast {
  if (decision.granted) {
    return grantedToast({ balance_after_cents: decision.balance_after_cents ?? undefined })
  }
  if (decision.reason === 'insufficient_balance') {
    return {
      kind: 'denied',
      title: 'אין מספיק יתרה',
      message: `נדרשים ${formatMoney(decision.fee_cents)} לכניסה.`,
      balanceCents: decision.balance_before_cents ?? null,
    }
  }
  return {
    kind: 'denied',
    title: 'הכניסה נדחתה',
    message: decision.reason,
    balanceCents: decision.balance_before_cents ?? null,
  }
}

export function DashboardPage() {
  const [gateStatus, setGateStatus] = useState<GateStatus | null>(null)
  const [chipToast, setChipToast] = useState<ChipToast | null>(null)
  const [lastActivity, setLastActivity] = useState<string | null>(null)
  const [simError, setSimError] = useState<string | null>(null)
  const [simLoading, setSimLoading] = useState(false)
  const toastTimer = useRef<number | null>(null)

  const wsUrl = useMemo(() => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    return `${proto}://${location.host}/api/access/ws/events`
  }, [])

  const cashProgress = gateStatus
    ? Math.min(100, (gateStatus.cash_accumulated_cents / gateStatus.entrance_fee_cents) * 100)
    : 0

  function refreshStatus() {
    api.get<GateStatus>('/access/healthz').then((r) => setGateStatus(r.data)).catch(() => {})
  }

  function showChipToast(toast: ChipToast) {
    if (toastTimer.current != null) window.clearTimeout(toastTimer.current)
    setChipToast(toast)
    if (toast.kind === 'granted') {
      toastTimer.current = window.setTimeout(() => setChipToast(null), 4000)
    }
  }

  async function simulateChip() {
    setSimLoading(true)
    setSimError(null)
    try {
      const res = await api.post<AccessDecision>('/access/dev/simulate/chip')
      showChipToast(chipToastFromDecision(res.data))
      refreshStatus()
      setLastActivity(res.data.granted ? 'סימולציית צ\'יפ — הדלת נפתחה' : 'סימולציית צ\'יפ — הכניסה נדחתה')
    } catch {
      setSimError('סימולציית הצ\'יפ נכשלה. ודא שהשרתים רצים (docker compose up).')
    } finally {
      setSimLoading(false)
    }
  }

  async function simulateCash(amountCents: number) {
    setSimLoading(true)
    setSimError(null)
    try {
      const res = await api.post<SimulateCashResult>('/access/dev/simulate/cash', { amount_cents: amountCents })
      refreshStatus()
      if (res.data.granted) {
        showChipToast(
          grantedToast({
            method: 'cash',
            remaining_cents: res.data.remaining_cents,
          }),
        )
        setLastActivity(`סימולציית מזומן — הדלת נפתחה (${formatMoney(amountCents)} הוכנסו)`)
      } else {
        setLastActivity(
          `הוכנס ${formatMoney(amountCents)} — סה"כ ${formatMoney(res.data.accumulated_cents)} מתוך ${formatMoney(res.data.entrance_fee_cents)}`,
        )
      }
    } catch {
      setSimError('סימולציית המזומן נכשלה. ודא שהשרתים רצים (docker compose up).')
    } finally {
      setSimLoading(false)
    }
  }

  useEffect(() => {
    refreshStatus()
    const interval = window.setInterval(refreshStatus, 10000)
    return () => window.clearInterval(interval)
  }, [])

  useEffect(() => {
    const ws = new WebSocket(wsUrl)
    ws.onmessage = (msg) => {
      let event: WsEvent
      try {
        event = JSON.parse(msg.data)
      } catch {
        return
      }

      refreshStatus()

      const toast = chipToastFromEvent(event)
      if (toast) {
        showChipToast(toast)
      }

      if (event.type === 'cash.accumulated' && event.total_cents != null && event.required_cents != null) {
        setLastActivity(`הוכנס ${formatMoney(event.amount_cents ?? 0)} — סה"כ ${formatMoney(event.total_cents)} מתוך ${formatMoney(event.required_cents)}`)
      } else if (event.type === 'access.granted' && event.uid == null) {
        setLastActivity('תשלום מזומן התקבל — הדלת נפתחה')
      } else if (event.type === 'door.opened') {
        setLastActivity('הדלת נפתחה')
      }
    }
    return () => ws.close()
  }, [wsUrl])

  return (
    <div className="gate-page" dir="rtl">
      {chipToast && (
        <div
          className="chip-toast-overlay"
          onClick={chipToast.kind === 'denied' ? () => setChipToast(null) : undefined}
        >
          <div
            className={`chip-toast ${chipToast.kind}`}
            onClick={(e) => e.stopPropagation()}
            role="alert"
            aria-live="assertive"
          >
            <div className="chip-toast-icon">{chipToast.kind === 'granted' ? '✓' : '✕'}</div>
            <h3>{chipToast.title}</h3>
            {chipToast.balanceCents != null && (
              <>
                <div className="balance">{formatMoney(chipToast.balanceCents)}</div>
                <p className="message">{chipToast.balanceLabel ?? 'יתרה נותרת בצ\'יפ'}</p>
              </>
            )}
            <p className="message">{chipToast.message}</p>
            {chipToast.kind === 'denied' && (
              <button type="button" onClick={() => setChipToast(null)}>
                הבנתי
              </button>
            )}
          </div>
        </div>
      )}

      <header className="gate-header">
        <h1>שער כניסה</h1>
        <p>העבר צ&apos;יפ או הכנס מטבעות כדי להיכנס</p>
      </header>

      <section className="gate-status-card">
        <div className="gate-status-icon" aria-hidden>
          🚪
        </div>
        <h2>המערכת פעילה ומאזינה</h2>
        <p className="hint">
          הצמד צ&apos;יפ לקורא או הכנס מטבעות.
          <br />
          {gateStatus
            ? `כשהתשלום מתקבל — הדלת תיפתח אוטומטית ל-${gateStatus.door_unlock_seconds} שניות.`
            : 'כשהתשלום מתקבל — הדלת תיפתח אוטומטית.'}
        </p>

        {gateStatus && (
          <>
            <div className="fee-badge">עלות כניסה: {formatMoney(gateStatus.entrance_fee_cents)}</div>
            <div className="fee-badge" style={{ marginTop: 8 }}>
              זמן פתיחת דלת: {gateStatus.door_unlock_seconds} שניות
            </div>

            <div className="cash-progress">
              <div className="cash-progress-label">
                <span>מזומן שהוכנס</span>
                <span>
                  {formatMoney(gateStatus.cash_accumulated_cents)} / {formatMoney(gateStatus.entrance_fee_cents)}
                </span>
              </div>
              <div className="cash-progress-bar" aria-hidden>
                <div className="cash-progress-fill" style={{ width: `${cashProgress}%` }} />
              </div>
            </div>
          </>
        )}

        {lastActivity && (
          <p className="hint" style={{ marginTop: 20 }}>
            {lastActivity}
          </p>
        )}
      </section>

      <details className="gate-dev" open>
        <summary>כלי פיתוח (סימולציה)</summary>
        <div className="gate-dev-buttons">
          <button type="button" disabled={simLoading} onClick={() => void simulateChip()}>
            {simLoading ? 'מריץ…' : "סימולציית צ'יפ"}
          </button>
          <button type="button" disabled={simLoading} onClick={() => void simulateCash(100)}>
            ₪1 מזומן
          </button>
          <button
            type="button"
            disabled={simLoading || !gateStatus}
            onClick={() => gateStatus && void simulateCash(gateStatus.entrance_fee_cents)}
          >
            {gateStatus ? `עלות כניסה (${formatMoney(gateStatus.entrance_fee_cents)})` : 'עלות כניסה'}
          </button>
        </div>
        {simError && <p className="gate-dev-error">{simError}</p>}
      </details>

      <Link className="gate-admin-link" to="/admin">
        הגדרות מנהל
      </Link>
    </div>
  )
}
