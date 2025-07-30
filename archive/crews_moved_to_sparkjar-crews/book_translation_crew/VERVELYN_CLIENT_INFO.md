# Vervelyn Client Information for Book Translation

## Client Connection Chain
1. **client_user_id**: `3a411a30-1653-4caf-acee-de257ff50e36`
2. **clients_id**: `1d1c2154-242b-4f49-9ca8-e57129ddc823`
3. **client database URL**: `postgresql://postgres.gvfiezbiyfggwdlvqnsc:OUXQVlj4q6taAIZm@aws-0-us-east-2.pooler.supabase.com:5432/postgres`

## Important Book Key
```
book_key: https://drive.google.com/drive/u/0/folders/1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO
```

## How This Works
1. The client_user_id is used to look up the user in the main SparkJAR database
2. From that user record, we get the clients_id
3. Using the clients_id, we query client_secrets table for the database_url
4. This gives us the vervelyn-specific database URL where the book data is stored

## Usage Example
```python
inputs = {
    "client_user_id": "3a411a30-1653-4caf-acee-de257ff50e36",
    "book_key": "https://drive.google.com/drive/u/0/folders/1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO",
    "target_language": "en"
}
```

## Database Notes
- The vervelyn database is a separate Supabase instance
- Book pages are stored in the book_ingestions table
- Use version="original" for source pages
- Use version="translation_en" for English translations