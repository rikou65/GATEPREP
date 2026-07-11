import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { practiceApi } from "@/api/endpoints/practice";
import { queryKeys } from "@/api/queryKeys";

type PracticeFilters = Record<string, string | number | boolean | undefined>;

function cleanFilters(filters?: PracticeFilters) {
  if (!filters) return {};
  return Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== "" && value != null));
}

export function useQuestions(filters?: PracticeFilters) {
  const params = cleanFilters(filters);
  return useQuery({
    queryKey: queryKeys.questions.all(params),
    queryFn: () => practiceApi.questions(params),
  });
}

export function usePyqs(filters?: PracticeFilters) {
  const params = cleanFilters(filters);
  return useQuery({
    queryKey: queryKeys.pyqs.all(params),
    queryFn: () => practiceApi.pyqs(params),
  });
}

export function useMistakes(filters?: PracticeFilters) {
  const params = cleanFilters(filters);
  return useQuery({
    queryKey: queryKeys.mistakes.all(params),
    queryFn: () => practiceApi.mistakes(params),
  });
}

export function useQuestionNotes(questionId?: string) {
  return useQuery({
    queryKey: questionId ? queryKeys.questions.notes(questionId) : ["questions", "notes", "missing"],
    queryFn: () => practiceApi.questionNotes(questionId as string),
    enabled: Boolean(questionId),
  });
}

export function useQuestionAttempts(questionId?: string) {
  return useQuery({
    queryKey: questionId ? queryKeys.questions.attempts(questionId) : ["questions", "attempts", "missing"],
    queryFn: () => practiceApi.questionAttempts(questionId as string),
    enabled: Boolean(questionId),
  });
}

export function usePyqAttempts(pyqId?: string) {
  return useQuery({
    queryKey: pyqId ? queryKeys.pyqs.attempts(pyqId) : ["pyqs", "attempts", "missing"],
    queryFn: () => practiceApi.pyqAttempts(pyqId as string),
    enabled: Boolean(pyqId),
  });
}

export function useSaveQuestion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ questionId, payload }: { questionId?: string; payload: unknown }) =>
      questionId
        ? practiceApi.updateQuestion(questionId, payload)
        : practiceApi.createQuestion(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.questions.all() }),
  });
}

export function useSavePyq() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ pyqId, payload }: { pyqId?: string; payload: unknown }) =>
      pyqId ? practiceApi.updatePyq(pyqId, payload) : practiceApi.createPyq(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.pyqs.all() }),
  });
}

export function useSaveQuestionNotes(questionId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (noteContent: string) =>
      practiceApi.saveQuestionNotes(questionId as string, noteContent),
    onSuccess: () => {
      if (questionId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.questions.notes(questionId) });
      }
    },
  });
}

export function useSubmitQuestionAttempt(questionId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: unknown) => practiceApi.attemptQuestion(questionId as string, payload),
    onSuccess: () => {
      if (questionId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.questions.attempts(questionId) });
        queryClient.invalidateQueries({ queryKey: queryKeys.questions.all() });
      }
    },
  });
}

export function useSubmitPyqAttempt(pyqId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: unknown) => practiceApi.attemptPyq(pyqId as string, payload),
    onSuccess: () => {
      if (pyqId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.pyqs.attempts(pyqId) });
        queryClient.invalidateQueries({ queryKey: queryKeys.pyqs.all() });
      }
    },
  });
}

export function useToggleQuestionFlag(questionId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ flagType, enabled }: { flagType: string; enabled: boolean }) =>
      enabled
        ? practiceApi.setQuestionFlag(questionId as string, flagType)
        : practiceApi.removeQuestionFlag(questionId as string, flagType),
    onSuccess: () => {
      if (questionId) queryClient.invalidateQueries({ queryKey: queryKeys.questions.all() });
    },
  });
}

export function useTogglePyqFlag(pyqId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ flagType, enabled }: { flagType: string; enabled: boolean }) =>
      enabled
        ? practiceApi.setPyqFlag(pyqId as string, flagType)
        : practiceApi.removePyqFlag(pyqId as string, flagType),
    onSuccess: () => {
      if (pyqId) queryClient.invalidateQueries({ queryKey: queryKeys.pyqs.all() });
    },
  });
}

export function useCreateMistake() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: practiceApi.createMistake,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.mistakes.all() }),
  });
}

export function useDeleteQuestion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: practiceApi.deleteQuestion,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.questions.all() }),
  });
}

export function useDeletePyq() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: practiceApi.deletePyq,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.pyqs.all() }),
  });
}

export function useDeleteMistake() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: practiceApi.deleteMistake,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.mistakes.all() }),
  });
}
