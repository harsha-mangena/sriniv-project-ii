import { useCallback } from 'react'
import { useSessionStore } from '../stores/sessionStore'
import { startInterview, submitAnswer, getNextQuestion, endInterview } from '../services/interviewService'

export function useInterview() {
  const store = useSessionStore()

  const start = useCallback(async (resumeId: string, jdId: string) => {
    store.setLoading(true)
    try {
      const result = await startInterview(resumeId, jdId)
      store.setSession(result.session_id, resumeId, jdId)
      if (result.first_question) {
        const q = result.first_question
        store.setQuestion(q.question_text, q.category, q.difficulty)
        store.addMessage({ role: 'ai', text: q.question_text })
      }
      return result
    } catch (err) {
      // Fix 2.17: Clear loading state on error and re-throw for UI handling
      store.setLoading(false)
      throw err
    } finally {
      store.setLoading(false)
    }
  }, [store])

  const answer = useCallback(async (text: string) => {
    if (!store.sessionId) return null
    store.addMessage({ role: 'user', text })
    store.setLoading(true)
    try {
      const result = await submitAnswer(store.sessionId, text)
      const atoms = Object.entries(result.atom_scores).map(([id, data]) => ({
        id,
        label: id,
        score: typeof data === 'object' && data !== null ? (data as { score: number }).score : 0,
      }))
      store.addMessage({
        role: 'ai',
        text: result.feedback_summary,
        score: result.overall_score,
        atoms,
      })
      // If follow-up question
      if (result.next_action.action === 'follow_up' && result.next_action.question) {
        store.setQuestion(result.next_action.question, store.currentCategory || '', store.currentDifficulty)
        store.addMessage({ role: 'ai', text: result.next_action.question })
      }
      return result
    } catch (err) {
      // Fix 2.17: Clear "Evaluating..." state on error and show user-facing message
      store.setLoading(false)
      throw err
    } finally {
      store.setLoading(false)
    }
  }, [store])

  const next = useCallback(async () => {
    if (!store.sessionId) return null
    store.setLoading(true)
    try {
      const result = await getNextQuestion(store.sessionId)
      store.setQuestion(result.question_text, result.category, result.difficulty)
      store.addMessage({ role: 'ai', text: result.question_text })
      return result
    } catch (err) {
      // Fix 2.17: Clear loading state on error
      store.setLoading(false)
      throw err
    } finally {
      store.setLoading(false)
    }
  }, [store])

  const end = useCallback(async () => {
    if (!store.sessionId) return null
    try {
      const result = await endInterview(store.sessionId)
      store.setActive(false)
      return result
    } catch (err) {
      store.setLoading(false)
      throw err
    } finally {
      store.setLoading(false)
    }
  }, [store])

  return { start, answer, next, end, ...store }
}
