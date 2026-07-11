import { api, unwrap } from "@/api/http";
import type { Attempt, PracticeItem } from "@/types/api";

export const practiceApi = {
  questions: (params?: unknown) =>
    unwrap<{ items: PracticeItem[]; total: number }>(api.get("/questions", { params })),
  createQuestion: (payload: unknown) => unwrap<PracticeItem>(api.post("/questions", payload)),
  updateQuestion: (questionId: string, payload: unknown) =>
    unwrap<PracticeItem>(api.put(`/questions/${questionId}`, payload)),
  deleteQuestion: (questionId: string) => unwrap(api.delete(`/questions/${questionId}`)),
  questionAttempts: (questionId: string) =>
    unwrap<Attempt[]>(api.get(`/questions/${questionId}/attempts`)),
  attemptQuestion: (questionId: string, payload: unknown) =>
    unwrap(api.post(`/questions/${questionId}/attempt`, payload)),
  questionNotes: (questionId: string) => unwrap(api.get(`/questions/${questionId}/notes`)),
  saveQuestionNotes: (questionId: string, note_content: string) =>
    unwrap(api.post(`/questions/${questionId}/notes`, { note_content })),
  setQuestionFlag: (questionId: string, flag_type: string) =>
    unwrap(api.post(`/questions/${questionId}/flag`, { flag_type })),
  removeQuestionFlag: (questionId: string, flagType: string) =>
    unwrap(api.delete(`/questions/${questionId}/flag/${flagType}`)),
  pyqs: (params?: unknown) =>
    unwrap<{ items: PracticeItem[]; total: number }>(api.get("/pyqs", { params })),
  createPyq: (payload: unknown) => unwrap<PracticeItem>(api.post("/pyqs", payload)),
  updatePyq: (pyqId: string, payload: unknown) =>
    unwrap<PracticeItem>(api.put(`/pyqs/${pyqId}`, payload)),
  deletePyq: (pyqId: string) => unwrap(api.delete(`/pyqs/${pyqId}`)),
  pyqAttempts: (pyqId: string) => unwrap<Attempt[]>(api.get(`/pyqs/${pyqId}/attempts`)),
  attemptPyq: (pyqId: string, payload: unknown) =>
    unwrap(api.post(`/pyqs/${pyqId}/attempt`, payload)),
  setPyqFlag: (pyqId: string, flag_type: string) =>
    unwrap(api.post(`/pyqs/${pyqId}/flag`, { flag_type })),
  removePyqFlag: (pyqId: string, flagType: string) =>
    unwrap(api.delete(`/pyqs/${pyqId}/flag/${flagType}`)),
  mistakes: (params?: unknown) => unwrap(api.get("/mistakes", { params })),
  createMistake: (payload: unknown) => unwrap(api.post("/mistakes", payload)),
  deleteMistake: (mistakeId: string) => unwrap(api.delete(`/mistakes/${mistakeId}`)),
};
