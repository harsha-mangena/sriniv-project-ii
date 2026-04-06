import { api } from './api'

export interface InterviewStartResponse {
  session_id: string
  status: string
  total_questions: number
  categories: number
  first_question: {
    question_text: string
    category: string
    subcategory: string
    difficulty: number
    atoms_count: number
  } | null
}

export interface EvaluationResponse {
  overall_score: number
  atom_scores: Record<string, { score: number; feedback: string; missing_points: string[]; strength: string }>
  passed_atoms: string[]
  failed_atoms: string[]
  feedback_summary: string
  next_action: { action: string; question?: string; reason: string }
}

export interface NextQuestionResponse {
  question_text: string
  category: string
  subcategory: string
  difficulty: number
  atoms_count: number
  is_follow_up: boolean
}

export interface PrepResponse {
  session_id: string
  questions: {
    question: string
    category: string
    difficulty: number
    model_answer: string
    talking_points: string[]
    target_skills: string[]
  }[]
  weakness_analysis: Record<string, unknown>
  match_score: Record<string, unknown>
  total_generated: number
}

export async function startInterview(
  resumeId: string,
  jdId: string,
  mode: string = 'mock',
  roleType: string = 'Software Engineer'
): Promise<InterviewStartResponse> {
  return api.post('/interview/start', { resume_id: resumeId, jd_id: jdId, mode, role_type: roleType })
}

export async function submitAnswer(sessionId: string, answerText: string): Promise<EvaluationResponse> {
  return api.post('/interview/answer', { session_id: sessionId, answer_text: answerText })
}

export async function getNextQuestion(sessionId: string): Promise<NextQuestionResponse> {
  return api.post(`/interview/next?session_id=${sessionId}`, {})
}

export async function endInterview(sessionId: string) {
  return api.post(`/interview/end?session_id=${sessionId}`, {})
}

export async function generatePrep(
  resumeId: string,
  jdId: string,
  numQuestions: number = 30,
  roleType: string = 'Software Engineer'
): Promise<PrepResponse> {
  return api.post('/questions/generate-prep', {
    resume_id: resumeId,
    jd_id: jdId,
    num_questions: numQuestions,
    role_type: roleType,
  })
}
