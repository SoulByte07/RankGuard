"""
  - `POST /transaction` → calls `create_transaction`, returns `201` (new) or `200` (duplicate)
  - Validation errors via pydantic → `422`
  - Business rule violations → `400`
"""
