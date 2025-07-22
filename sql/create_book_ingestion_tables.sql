-- Book Ingestion Tables for Client Databases
-- These tables store transcribed book pages and their embeddings

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Stores transcribed pages
CREATE TABLE IF NOT EXISTS book_ingestions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    book_key TEXT NOT NULL,        -- From folder path
    page_number INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    language_code TEXT NOT NULL,
    version TEXT DEFAULT 'original',
    page_text TEXT NOT NULL,
    ocr_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_book_page UNIQUE (book_key, page_number, version)
);

-- Stores embeddings for search
CREATE TABLE IF NOT EXISTS object_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES book_ingestions(id) ON DELETE CASCADE,
    embedding vector(1536),
    chunk_index INTEGER,
    chunk_text TEXT,
    start_char INTEGER,
    end_char INTEGER,
    embeddings_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_book_ingestions_book_key ON book_ingestions(book_key);
CREATE INDEX idx_book_ingestions_page_number ON book_ingestions(page_number);
CREATE INDEX idx_object_embeddings_source_id ON object_embeddings(source_id);