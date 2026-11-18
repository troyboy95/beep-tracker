
export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[]

export type Database = {
  
  "public": {
          Tables: {
            "ingest_runs": {
                  Row: {
                    "errors": NonNullable<Json>,"est_cost_usd": number,"expired_posts": number,"fetched": number,"finished_at": string | null,"id": number,"input_tokens": number,"mode": string,"new_posts": number,"output_tokens": number,"started_at": string,"status": string,"tag_queue_pending": number | null,"tagged": number,"trigger": string,"updated_posts": number
                  }
                  ComputedFields: never
                  Insert: {
                    "errors"?: NonNullable<Json>,"est_cost_usd"?: number,"expired_posts"?: number,"fetched"?: number,"finished_at"?: string | null,"id"?: never,"input_tokens"?: number,"mode"?: string,"new_posts"?: number,"output_tokens"?: number,"started_at"?: string,"status"?: string,"tag_queue_pending"?: number | null,"tagged"?: number,"trigger"?: string,"updated_posts"?: number
                  }
                  Update: {
                    "errors"?: NonNullable<Json>,"est_cost_usd"?: number,"expired_posts"?: number,"fetched"?: number,"finished_at"?: string | null,"id"?: never,"input_tokens"?: number,"mode"?: string,"new_posts"?: number,"output_tokens"?: number,"started_at"?: string,"status"?: string,"tag_queue_pending"?: number | null,"tagged"?: number,"trigger"?: string,"updated_posts"?: number
                  }
                  Relationships: [
                    
                  ]
                },"jobs": {
                  Row: {
                    "board": string,"city": string | null,"company": string,"content_hash": string,"dedup_key": string,"description": string | null,"external_id": string,"first_seen_at": string,"hints": string | null,"id": number,"is_active": boolean,"is_fresher": boolean | null,"job_type": string | null,"last_seen_at": string,"last_tag_error": string | null,"location_raw": string | null,"min_years_hint": number | null,"next_tag_at": string | null,"posted_at": string | null,"prefilter_reason": string | null,"role": string | null,"search_tsv": unknown,"source": string,"tag_attempts": number,"tag_call_id": number | null,"tag_confidence": number | null,"tag_model": string | null,"tag_prompt_version": string | null,"tag_status": string,"tagged_at": string | null,"title": string,"url": string
                  }
                  ComputedFields: never
                  Insert: {
                    "board": string,"city"?: string | null,"company": string,"content_hash": string,"dedup_key": string,"description"?: string | null,"external_id": string,"first_seen_at"?: string,"hints"?: string | null,"id"?: never,"is_active"?: boolean,"is_fresher"?: boolean | null,"job_type"?: string | null,"last_seen_at"?: string,"last_tag_error"?: string | null,"location_raw"?: string | null,"min_years_hint"?: number | null,"next_tag_at"?: string | null,"posted_at"?: string | null,"prefilter_reason"?: string | null,"role"?: string | null,"search_tsv"?: never,"source": string,"tag_attempts"?: number,"tag_call_id"?: number | null,"tag_confidence"?: number | null,"tag_model"?: string | null,"tag_prompt_version"?: string | null,"tag_status"?: string,"tagged_at"?: string | null,"title": string,"url": string
                  }
                  Update: {
                    "board"?: string,"city"?: string | null,"company"?: string,"content_hash"?: string,"dedup_key"?: string,"description"?: string | null,"external_id"?: string,"first_seen_at"?: string,"hints"?: string | null,"id"?: never,"is_active"?: boolean,"is_fresher"?: boolean | null,"job_type"?: string | null,"last_seen_at"?: string,"last_tag_error"?: string | null,"location_raw"?: string | null,"min_years_hint"?: number | null,"next_tag_at"?: string | null,"posted_at"?: string | null,"prefilter_reason"?: string | null,"role"?: string | null,"search_tsv"?: never,"source"?: string,"tag_attempts"?: number,"tag_call_id"?: number | null,"tag_confidence"?: number | null,"tag_model"?: string | null,"tag_prompt_version"?: string | null,"tag_status"?: string,"tagged_at"?: string | null,"title"?: string,"url"?: string
                  }
                  Relationships: [
                    {
      foreignKeyName: "jobs_tag_call_id_fkey"
      columns: ["tag_call_id"]
isOneToOne: false
      referencedRelation: "llm_calls"
      referencedColumns: ["id"]
    }
                  ]
                },"llm_calls": {
                  Row: {
                    "attempt": number,"cost_usd": number | null,"created_at": string,"error": string | null,"id": number,"input_tokens": number | null,"job_ids": (number)[],"latency_ms": number | null,"model": string,"output_tokens": number | null,"parsed_ok": boolean,"prompt_hash": string,"prompt_version": string,"provider": string,"request": Json | null,"response_raw": string | null,"retry_of": number | null,"run_id": number | null,"validation_errors": Json | null
                  }
                  ComputedFields: never
                  Insert: {
                    "attempt"?: number,"cost_usd"?: number | null,"created_at"?: string,"error"?: string | null,"id"?: never,"input_tokens"?: number | null,"job_ids"?: (number)[],"latency_ms"?: number | null,"model": string,"output_tokens"?: number | null,"parsed_ok"?: boolean,"prompt_hash": string,"prompt_version": string,"provider"?: string,"request"?: Json | null,"response_raw"?: string | null,"retry_of"?: number | null,"run_id"?: number | null,"validation_errors"?: Json | null
                  }
                  Update: {
                    "attempt"?: number,"cost_usd"?: number | null,"created_at"?: string,"error"?: string | null,"id"?: never,"input_tokens"?: number | null,"job_ids"?: (number)[],"latency_ms"?: number | null,"model"?: string,"output_tokens"?: number | null,"parsed_ok"?: boolean,"prompt_hash"?: string,"prompt_version"?: string,"provider"?: string,"request"?: Json | null,"response_raw"?: string | null,"retry_of"?: number | null,"run_id"?: number | null,"validation_errors"?: Json | null
                  }
                  Relationships: [
                    {
      foreignKeyName: "llm_calls_retry_of_fkey"
      columns: ["retry_of"]
isOneToOne: false
      referencedRelation: "llm_calls"
      referencedColumns: ["id"]
    },{
      foreignKeyName: "llm_calls_run_id_fkey"
      columns: ["run_id"]
isOneToOne: false
      referencedRelation: "ingest_runs"
      referencedColumns: ["id"]
    }
                  ]
                },"schema_migrations": {
                  Row: {
                    "applied_at": string,"version": string
                  }
                  ComputedFields: never
                  Insert: {
                    "applied_at"?: string,"version": string
                  }
                  Update: {
                    "applied_at"?: string,"version"?: string
                  }
                  Relationships: [
                    
                  ]
                }
          }
          Views: {
            "public_jobs": {
                  Row: {
                    "city": string | null,"company": string,"first_seen_at": string,"id": number,"job_type": string | null,"location_raw": string | null,"posted_at": string | null,"role": string | null,"search_tsv": unknown,"source": string,"title": string,"url": string
                  }
                  ComputedFields: never
                  Relationships: [
                    
                  ]
                }
          }
          Functions: {
            [_ in never]: never
          }
          Enums: {
            [_ in never]: never
          }
          CompositeTypes: {
            [_ in never]: never
          }
        }
}

type DatabaseWithoutInternals = Omit<Database, '__InternalSupabase'>

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never
> = DefaultSchemaTableNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
  ? (DefaultSchema["Tables"] & DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
      Row: infer R
    }
    ? R
    : never
  : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never
> = DefaultSchemaTableNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
  ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
      Insert: infer I
    }
    ? I
    : never
  : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never
> = DefaultSchemaTableNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
  ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
      Update: infer U
    }
    ? U
    : never
  : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never
> = DefaultSchemaEnumNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
  ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
  : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never
> = PublicCompositeTypeNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
  ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
  : never

export const Constants = {
  "public": {
          Enums: {
            
          }
        }
} as const
