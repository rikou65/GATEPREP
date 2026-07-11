export type ApiEnvelope<T> = {
  success?: boolean;
  data: T;
  error?: string;
  message?: string;
};

export type AppUser = {
  user_id: string;
  email: string;
  name?: string;
  picture?: string;
  auth_provider?: "supabase" | "legacy_google" | string;
  supabase_user_id?: string;
  email_verified?: boolean;
};

export type AuthSession = {
  session_token?: string;
  user: AppUser;
};

export type Subject = {
  subject_id: string;
  name: string;
  order?: number;
};

export type Topic = {
  topic_id: string;
  subject_id: string;
  name: string;
  order?: number;
};

export type QuestionType = "MCQ" | "MSQ" | "NAT";

export type PracticeItem = {
  question_id?: string;
  pyq_id?: string;
  subject_id: string;
  topic_id?: string;
  subject_name?: string;
  topic_name?: string;
  question_type: QuestionType;
  question_text: string;
  options?: string[] | null;
  correct_answer?: string | string[];
  solution?: string;
  source?: string;
  flags?: string[];
  year?: number;
};

export type Attempt = {
  attempt_id: string;
  selected_answer: unknown;
  is_correct: boolean;
  time_taken: number;
  attempted_at: string;
};

export type Playlist = {
  playlist_id: string;
  title: string;
  subject_id?: string;
  videos?: Video[];
};

export type Video = {
  video_id: string;
  playlist_id: string;
  youtube_video_id: string;
  title: string;
  duration?: number;
  progress?: {
    watch_percentage?: number;
    watch_time?: number;
    completed?: boolean;
    last_watched_at?: string;
  };
};

export type Resource = {
  resource_id: string;
  subject_id: string;
  resource_type: string;
  title: string;
  filename?: string;
  file_size?: number;
  source?: string;
  external_url?: string;
};

export type IntegrationStatus = {
  connected: boolean;
  user_id?: string;
  drive_email?: string;
  youtube_email?: string;
  connected_at?: string;
};

export type DashboardSummary = {
  questions_solved: number;
  pyqs_solved: number;
  videos_completed: number;
  total_playlists: number;
  question_accuracy: number;
  pyq_accuracy: number;
  total_mistakes: number;
  resources_uploaded: number;
};
