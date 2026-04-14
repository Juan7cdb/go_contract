# =============================================
# Go Contract AI - Database Schema Reference
# =============================================
# 
# This file documents the actual PostgreSQL database structure (SQLAlchemy models)
# Last updated: 2026-04-13
#
# TABLES:
# -------
#
# ## users
#   - id: integer (PK)
#   - email: varchar(255) (Unique)
#   - hashed_password: varchar(255)
#   - first_name: varchar(100)
#   - last_name: varchar(100)
#   - credits_remaining: integer (Default: 5)
#   - preferences: json
#   - created_at: timestamp
#   - updated_at: timestamp
#
# ## plans
#   - id: integer (PK)
#   - title: varchar(100)
#   - description: varchar(255)
#   - price: float
#   - contracts_included: integer
#   - time_subscription: varchar(50)
#   - created_at: timestamp
#   - updated_at: timestamp
#
# ## subscriptions
#   - id: integer (PK)
#   - user_id: integer (FK -> users.id)
#   - plan_id: integer (FK -> plans.id)
#   - payment_method: varchar(100)
#   - start_subscription: timestamp
#   - end_subscription: timestamp
#
# ## template_contracts
#   - id: integer (PK)
#   - category: varchar(100)
#   - subcategory: varchar(100)
#   - title: varchar(255)
#   - description: text
#   - rules: text (AI generation rules)
#   - steps_config: json
#   - contract_template_url: varchar(255)
#   - created_at: timestamp
#   - updated_at: timestamp
#
# ## contracts
#   - id: integer (PK)
#   - user_id: integer (FK -> users.id)
#   - template_id: integer (FK -> template_contracts.id)
#   - title: varchar(255)
#   - description: text
#   - status: varchar(50)
#   - form_data: json
#   - generated_content: text
#   - contract_url: varchar(255)
#   - created_at: timestamp
#   - updated_at: timestamp
#
# ## contract_drafts
#   - id: integer (PK)
#   - user_id: integer (FK -> users.id)
#   - template_id: integer (FK -> template_contracts.id)
#   - current_step: integer
#   - form_data: json
#   - created_at: timestamp
#   - updated_at: timestamp
#
# ## agents
#   - id: integer (PK)
#   - template_id: integer (FK -> template_contracts.id)
#   - title: varchar(255)
#   - description: text
#   - prompt: text (system prompt for AI)
#   - created_at: timestamp
#   - updated_at: timestamp
