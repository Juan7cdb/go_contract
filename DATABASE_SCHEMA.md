# =============================================
# Go Contract AI - Database Schema Reference
# =============================================
# 
# This file documents the actual Supabase database structure
# Last updated: 2026-02-06
#
# TABLES:
# -------
#
# ## profiles (users table)
#   - id: uuid (PK, references auth.users)
#   - first_name: text
#   - last_name: text
#   - email: text
#   - created_at: timestamp with time zone
#   - updated_at: timestamp with time zone
#
# ## plans (subscription plans info)
#   - id: uuid (PK)
#   - title: text
#   - description: text
#   - price: numeric
#   - time_subscription: integer (days)
#   - created_at: timestamp with time zone
#   - updated_at: timestamp with time zone
#
# ## subscriptions (user subscriptions)
#   - id: uuid (PK)
#   - user_id: uuid (FK -> profiles.id)
#   - plan_id: uuid (FK -> plans.id)
#   - payment_method: text
#   - start_subscription: timestamp with time zone
#   - end_subscription: timestamp with time zone
#
# ## template_contracts (contract templates for AI)
#   - id: uuid (PK)
#   - title: text
#   - description: text
#   - rules: text (AI generation rules)
#   - contract_template_url: text
#   - created_at: timestamp with time zone
#   - updated_at: timestamp with time zone
#
# ## contracts (user generated contracts)
#   - id: uuid (PK)
#   - user_id: uuid (FK -> profiles.id)
#   - template_id: uuid (FK -> template_contracts.id)
#   - title: text
#   - description: text
#   - contract_url: text (stored file URL)
#   - created_at: timestamp with time zone
#
# ## agents (AI agents per template)
#   - id: uuid (PK)
#   - template_id: uuid (FK -> template_contracts.id)
#   - title: text
#   - prompt: text (system prompt for AI)
#   - created_at: timestamp with time zone
#   - updated_at: timestamp with time zone
