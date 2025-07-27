# Test Client Information

## Valid Test Client User ID (Vervelyn Books)
```
client_user_id: 3a411a30-1653-4caf-acee-de257ff50e36
```

This client_user_id is confirmed to exist in the database and should be used for all testing of the book translation crew.

## Client Connection Chain
1. **client_user_id**: `3a411a30-1653-4caf-acee-de257ff50e36` (in main SparkJAR DB)
2. **clients_id**: `1d1c2154-242b-4f49-9ca8-e57129ddc823` (retrieved from client_users.clients_id)
3. **client database URL**: Retrieved from client_secrets table using clients_id
   - `postgresql://postgres.gvfiezbiyfggwdlvqnsc:OUXQVlj4q6taAIZm@aws-0-us-east-2.pooler.supabase.com:5432/postgres`
4. **book_key**: `https://drive.google.com/drive/u/0/folders/1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO`

## Usage

### In Direct Tests
```python
inputs = {
    "client_user_id": "3a411a30-1653-4caf-acee-de257ff50e36",
    "book_key": "el-baron-book",
    "target_language": "en"
}
```

### In Integration Tests
```python
test_client_data = {
    "client_user_id": "3a411a30-1653-4caf-acee-de257ff50e36",
    "book_key": "test_translation_quality"
}
```

## Important Notes
- This is the only confirmed working client_user_id for testing
- The previous ID (1d1c2154-242b-4f49-9ca8-e57129ddc823) returns "Tenant or user not found"
- Always use this ID when testing the book translation crew