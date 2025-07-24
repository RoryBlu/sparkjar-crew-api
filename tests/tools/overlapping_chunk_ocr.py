#!/usr/bin/env python3
"""OCR with overlapping chunks for better accuracy and deduplication."""

class OverlappingChunkOCR:
    """Extract text with overlapping chunks for validation."""
    
    def __init__(self):
        self.chunk_size = 50
        self.overlap = 10  # 10 word overlap
        
    def calculate_chunks(self, total_words: int) -> list:
        """Calculate chunk ranges with overlap."""
        chunks = []
        position = 1
        
        while position <= total_words:
            chunk_end = min(position + self.chunk_size - 1, total_words)
            
            # Add overlap to previous chunk (except first)
            if chunks:
                actual_start = position - self.overlap
            else:
                actual_start = position
                
            chunks.append({
                'chunk_id': len(chunks) + 1,
                'start': actual_start,
                'end': chunk_end,
                'expected_start': position,  # Where non-overlapped part starts
                'overlap_words': self.overlap if chunks else 0
            })
            
            position += self.chunk_size - self.overlap
            
        return chunks
    
    def extract_with_overlap(self, base64_image: str, chunk_info: dict, 
                            page_structure: dict) -> dict:
        """Extract chunk with overlap for validation."""
        
        # Find line info for this chunk
        line_info = self.find_line_info(chunk_info['start'], page_structure)
        
        messages = [{
            "role": "system",
            "content": f"""Extract words {chunk_info['start']} to {chunk_info['end']} from this manuscript.
Location: Starting at Line {line_info['line']}, approximately {line_info['position']}% down.
First word should be: '{line_info['first_word']}'
Last word should be near: '{line_info['last_word']}'

Extract EXACTLY these {chunk_info['end'] - chunk_info['start'] + 1} words.
Return ONLY the words, no commentary."""
        }, {
            "role": "user",
            "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]
        }]
        
        # Nano extracts with overlap
        extracted = self.nano_extract(messages)
        
        return {
            'chunk_id': chunk_info['chunk_id'],
            'text': extracted,
            'start': chunk_info['start'],
            'end': chunk_info['end'],
            'overlap_start': chunk_info['expected_start']
        }
    
    def mini_merge_and_validate(self, chunks: list) -> dict:
        """Mini merges overlapping chunks and identifies issues."""
        
        prompt = f"""Merge these overlapping text chunks from a Spanish manuscript.
Each chunk overlaps by {self.overlap} words with the next.

"""
        for i, chunk in enumerate(chunks):
            prompt += f"\nChunk {i+1} (words {chunk['start']}-{chunk['end']}):\n"
            prompt += f'"{chunk["text"]}"\n'
            
            if i < len(chunks) - 1:
                prompt += f"↓ Overlaps {self.overlap} words with next chunk ↓\n"
        
        prompt += """
Tasks:
1. Merge chunks by matching the overlapping words
2. Remove all duplicates 
3. Identify any chunks that don't align properly
4. Check for repetition patterns or hallucination
5. Return the clean merged text and list any problem chunks

Format response as:
MERGED TEXT: [clean text without duplicates]
PROBLEM CHUNKS: [list chunk IDs with issues]
REPETITIONS FOUND: [any repeated phrases]
"""
        
        messages = [{
            "role": "system",
            "content": "You are an expert at merging overlapping text segments and detecting quality issues."
        }, {
            "role": "user",
            "content": prompt
        }]
        
        # Mini does the merge and validation
        response = self.mini_process(messages)
        
        return self.parse_mini_response(response)
    
    def nano_redo_problem_chunks(self, base64_image: str, problem_chunks: list, 
                                page_structure: dict) -> list:
        """Nano re-extracts problem chunks with more specific guidance."""
        
        fixed_chunks = []
        
        for chunk_id in problem_chunks:
            original = next(c for c in self.chunks if c['chunk_id'] == chunk_id)
            
            # Get context from surrounding chunks
            prev_chunk = self.get_chunk(chunk_id - 1)
            next_chunk = self.get_chunk(chunk_id + 1)
            
            messages = [{
                "role": "system",
                "content": f"""RE-EXTRACT words {original['start']} to {original['end']}.
                
Previous chunk ended with: "{prev_chunk['text'][-30:]}"
Next chunk starts with: "{next_chunk['text'][:30]}"

The {self.overlap} overlapping words should match.
Extract the EXACT words from the manuscript, ensuring continuity."""
            }, {
                "role": "user",
                "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]
            }]
            
            fixed = self.nano_extract(messages)
            fixed_chunks.append({
                'chunk_id': chunk_id,
                'text': fixed
            })
            
        return fixed_chunks
    
    def process_page_with_overlap(self, image_path: str) -> dict:
        """Complete overlapping chunk process."""
        
        # 1. Map page structure
        page_structure = self.map_page_structure(image_path)
        total_words = page_structure['total_words']
        
        # 2. Calculate overlapping chunks
        chunk_plan = self.calculate_chunks(total_words)
        print(f"Plan: {len(chunk_plan)} chunks with {self.overlap}-word overlaps")
        
        # 3. Extract all chunks with overlap
        extracted_chunks = []
        for chunk_info in chunk_plan:
            result = self.extract_with_overlap(base64_image, chunk_info, page_structure)
            extracted_chunks.append(result)
            
        # 4. Mini merges and validates
        merge_result = self.mini_merge_and_validate(extracted_chunks)
        
        # 5. If problems found, nano re-extracts those chunks
        if merge_result['problem_chunks']:
            print(f"Issues found in chunks: {merge_result['problem_chunks']}")
            fixed = self.nano_redo_problem_chunks(
                base64_image, 
                merge_result['problem_chunks'],
                page_structure
            )
            
            # 6. Mini does final merge with fixed chunks
            merge_result = self.mini_final_merge(extracted_chunks, fixed)
            
        return {
            'text': merge_result['merged_text'],
            'total_words': len(merge_result['merged_text'].split()),
            'chunks_used': len(chunk_plan),
            'chunks_with_issues': len(merge_result.get('problem_chunks', [])),
            'repetitions_found': merge_result.get('repetitions', [])
        }

# Example chunk overlap visualization:
"""
Chunk 1: Words 1-50    "Que estabamos nosotros...hasta la media hora"
                                                   ↓ overlap ↓
Chunk 2: Words 41-90   "parte ya estaba...la media hora me volvió a llamar"  
                                                          ↓ overlap ↓
Chunk 3: Words 81-130  "hora me volvió a llamar...Enseguida fue"

Mini merges by matching "la media hora" in chunks 1&2, "me volvió a llamar" in chunks 2&3
"""