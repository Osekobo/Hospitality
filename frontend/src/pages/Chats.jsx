import { useEffect, useMemo, useRef, useState } from 'react'
import { getChats, sendAdminReply } from '../lib/api'
import { formatRelative, initials } from '../lib/format'
import { useI18n } from '../lib/i18nCore'
import { useApiResource } from '../lib/resource'
import { Badge, Card, EmptyState, ErrorState, LoadingState, PageHeader } from '../components/ui'

const loadChats = () => getChats()

export default function Chats() {
  const { t, locale } = useI18n()
  const { data, status, error, refresh } = useApiResource('chats', loadChats)
  const [selectedId, setSelectedId] = useState(null)
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') refresh()
    }, 15000)
    return () => clearInterval(timer)
  }, [refresh])

  const conversations = useMemo(() => {
    const groups = new Map()
    for (const chat of data || []) {
      if (!groups.has(chat.user_id)) {
        groups.set(chat.user_id, {
          key: chat.user_id,
          name: chat.guest_name,
          phoneNumber: chat.phone_number,
          platform: chat.platform,
          messages: [],
          last: chat.created_at,
        })
      }
      const group = groups.get(chat.user_id)
      group.messages.push(chat)
      if (new Date(chat.created_at) > new Date(group.last)) group.last = chat.created_at
    }
    return [...groups.values()]
      .map((group) => ({
        ...group,
        messages: group.messages.sort((a, b) => new Date(a.created_at) - new Date(b.created_at)),
      }))
      .sort((a, b) => new Date(b.last) - new Date(a.last))
  }, [data])

  const active = conversations.find((item) => item.key === selectedId) || conversations[0]

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'nearest' })
  }, [active?.key, active?.messages.length])

  const handleSend = async (event) => {
    event.preventDefault()
    const message = draft.trim()
    if (!message || !active || sending) return
    setSending(true)
    setSendError('')
    try {
      await sendAdminReply(active.key, message)
      setDraft('')
      await refresh()
    } catch (err) {
      setSendError(err.response?.data?.detail || err.message || t('chats.sendFailed'))
    } finally {
      setSending(false)
    }
  }

  if (status === 'error') return <ErrorState message={error} onRetry={refresh} retryLabel={t('common.retry')} />
  if (!data || status === 'loading') return <LoadingState label={t('common.loading')} />

  return (
    <>
      <PageHeader
        title={t('chats.title')}
        description={`${t('chats.description')} ${t('chats.refreshHint')}`}
        action={
          <button type="button" className="app-button app-button-secondary" onClick={refresh}>
            {t('common.refresh')}
          </button>
        }
      />

      {sendError && <p className="app-alert" role="alert">{sendError}</p>}

      <div className="app-chat-layout">
        <Card className="app-card-flush app-chat-list">
          <div className="app-chat-list-heading">
            <h2>{t('chats.list')}</h2>
            <small>{conversations.length} {t('chats.travelers')}</small>
          </div>
          {conversations.length ? (
            <ul className="app-conversation-list">
              {conversations.map((conversation) => (
                <li key={conversation.key}>
                  <button
                    type="button"
                    aria-current={active?.key === conversation.key ? 'true' : undefined}
                    onClick={() => setSelectedId(conversation.key)}
                  >
                    <span className="app-avatar" aria-hidden="true">{initials(conversation.name)}</span>
                    <span className="app-conversation-copy">
                      <span className="app-conversation-top">
                        <strong>{conversation.name}</strong>
                        <time dateTime={conversation.last}>{formatRelative(conversation.last, locale)}</time>
                      </span>
                      <span className="app-conversation-preview">{conversation.messages.at(-1)?.content}</span>
                      <small>{conversation.platform}</small>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState message={t('chats.empty')} />
          )}
        </Card>

        <Card className="app-card-flush app-chat-thread">
          {active ? (
            <>
              <div className="app-chat-heading">
                <span className="app-avatar app-avatar-large" aria-hidden="true">{initials(active.name)}</span>
                <div>
                  <strong>{active.name}</strong>
                  <small>{active.phoneNumber} · {active.platform}</small>
                </div>
                <span className="app-thread-label">{t('chats.agent')}</span>
              </div>

              <div className="app-messages" role="log" aria-live="polite" aria-relevant="additions text">
                {active.messages.map((message) => (
                  <article key={message.id} className={`app-message${message.direction === 'out' ? ' is-out' : ''}`}>
                    <p>{message.content}</p>
                    <footer>
                      <Badge value={message.direction} label={t(`common.${message.direction}`)} />
                      {message.intent && <span>{message.intent}</span>}
                      <time dateTime={message.created_at}>{formatRelative(message.created_at, locale)}</time>
                    </footer>
                  </article>
                ))}
                <div ref={bottomRef} />
              </div>

              <form className="app-chat-form" onSubmit={handleSend}>
                <label className="app-sr-only" htmlFor="reply-message">{t('chats.replyPlaceholder')}</label>
                <input
                  id="reply-message"
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  placeholder={t('chats.replyPlaceholder')}
                  maxLength={2000}
                />
                <button type="submit" className="app-button" disabled={sending || !draft.trim()}>
                  {sending ? t('chats.sending') : t('chats.send')}
                </button>
              </form>
            </>
          ) : (
            <EmptyState message={t('chats.empty')} />
          )}
        </Card>
      </div>
    </>
  )
}
