import { useCallback, useEffect, useMemo, useState } from 'react'
import { MessageCircleMore, Send, Sparkles } from 'lucide-react'
import { getChats, sendChat } from '../lib/api'
import { Badge, Card, ErrorState, LoadingState, PageHeader, timeAgo } from '../components/ui'

export default function Chats() {
  const [chats, setChats] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)

  const load = useCallback(async () => {
    try {
      const rows = await getChats()
      setChats(rows)
      setError('')
    } catch (err) {
      setError(err.message || 'Could not load conversations')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const timer = setInterval(load, 5000)
    return () => clearInterval(timer)
  }, [load])

  const conversations = useMemo(() => {
    const groups = new Map()
    chats.forEach((chat) => {
      const key = chat.user_id
      if (!groups.has(key)) {
        groups.set(key, {
          key,
          name: chat.guest_name,
          phone_number: chat.phone_number,
          platform: chat.platform,
          messages: [],
          last: chat.created_at,
        })
      }
      const group = groups.get(key)
      group.messages.push(chat)
      if (new Date(chat.created_at) > new Date(group.last)) group.last = chat.created_at
    })
    return [...groups.values()]
      .map((group) => ({ ...group, messages: group.messages.sort((a, b) => new Date(a.created_at) - new Date(b.created_at)) }))
      .sort((a, b) => new Date(b.last) - new Date(a.last))
  }, [chats])

  const active = conversations.find((item) => item.key === selectedId) || conversations[0]

  const handleSend = async (event) => {
    event.preventDefault()
    if (!draft.trim() || !active || sending) return
    setSending(true)
    try {
      await sendChat({
        phone_number: active.phone_number,
        platform: active.platform,
        message: draft.trim(),
        name: active.name,
      })
      setDraft('')
      await load()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Could not send message')
    } finally {
      setSending(false)
    }
  }

  if (error && !chats.length) return <ErrorState message={error} onRetry={load} />
  if (loading) return <LoadingState label="Loading conversations..." />

  return (
    <>
      <PageHeader
        eyebrow="Inbox"
        title="Live chats"
        description="Conversations routed from WhatsApp, Instagram DMs and SMS into one AI-assisted inbox."
        action={
          <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm text-slate-400">
            <span className="size-2 animate-pulse rounded-full bg-emerald-400" />
            Auto-refresh 5s
          </div>
        }
      />

      <div className="grid gap-5 lg:grid-cols-[340px_1fr]">
        <Card className="p-0">
          <div className="border-b border-slate-800/80 px-4 py-3">
            <p className="text-sm font-semibold text-white">Conversations</p>
            <p className="text-xs text-slate-500">{conversations.length} travelers</p>
          </div>
          <div className="max-h-[650px] overflow-y-auto">
            {conversations.map((conversation) => (
              <button
                key={conversation.key}
                onClick={() => setSelectedId(conversation.key)}
                className={`flex w-full items-start gap-3 border-b border-slate-800/60 px-4 py-3 text-left transition ${
                  active?.key === conversation.key ? 'bg-emerald-500/10' : 'hover:bg-slate-800/40'
                }`}
              >
                <span className="grid size-9 shrink-0 place-items-center rounded-full bg-slate-800 text-xs font-semibold text-emerald-300">
                  {conversation.name?.slice(0, 2).toUpperCase()}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-medium text-white">{conversation.name}</span>
                    <span className="shrink-0 text-[10px] text-slate-500">{timeAgo(conversation.last)}</span>
                  </span>
                  <span className="mt-1 block truncate text-xs text-slate-500">
                    {conversation.messages.at(-1)?.content}
                  </span>
                  <span className="mt-1.5 block text-[10px] uppercase tracking-wide text-slate-600">{conversation.platform}</span>
                </span>
              </button>
            ))}
          </div>
        </Card>

        <Card className="flex min-h-[560px] flex-col p-0">
          {active ? (
            <>
              <div className="flex items-center gap-3 border-b border-slate-800/80 px-5 py-4">
                <span className="grid size-10 place-items-center rounded-full bg-gradient-to-br from-emerald-400 to-teal-600 text-sm font-bold text-slate-950">
                  {active.name?.slice(0, 2).toUpperCase()}
                </span>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-white">{active.name}</p>
                  <p className="text-xs text-slate-500">{active.phone_number} · {active.platform}</p>
                </div>
                <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                  <Sparkles className="size-3.5" /> AI concierge active
                </span>
              </div>

              <div className="flex-1 space-y-4 overflow-y-auto bg-slate-950/30 px-5 py-6">
                {active.messages.map((message) => (
                  <div key={message.id} className={`flex ${message.direction === 'out' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${message.direction === 'out' ? 'rounded-br-sm bg-emerald-500/15 text-emerald-50 ring-1 ring-emerald-500/25' : 'rounded-bl-sm bg-slate-800/80 text-slate-200'}`}>
                      <p className="leading-relaxed">{message.content}</p>
                      <div className="mt-2 flex items-center gap-2 text-[10px] text-slate-500">
                        <Badge value={message.direction} />
                        {message.intent && <span>{message.intent}</span>}
                        <span>{timeAgo(message.created_at)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <form onSubmit={handleSend} className="flex items-center gap-3 border-t border-slate-800/80 px-5 py-4">
                <MessageCircleMore className="size-5 shrink-0 text-slate-500" />
                <input
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  placeholder="Reply as the AI concierge..."
                  className="w-full rounded-xl border border-slate-800 bg-slate-950/70 px-4 py-2.5 text-sm text-white outline-none placeholder:text-slate-600 focus:border-emerald-500/50"
                />
                <button
                  type="submit"
                  disabled={sending || !draft.trim()}
                  className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <Send className="size-4" /> {sending ? 'Sending' : 'Send'}
                </button>
              </form>
            </>
          ) : (
            <div className="grid flex-1 place-items-center text-sm text-slate-500">
              <div className="text-center">
                <MessageCircleMore className="mx-auto mb-3 size-10 text-slate-700" />
                No conversations yet. Send a message from WhatsApp or Instagram.
              </div>
            </div>
          )}
        </Card>
      </div>
    </>
  )
}
