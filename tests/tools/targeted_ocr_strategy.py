#!/usr/bin/env python3
"""Targeted OCR strategy with precise location guidance."""

class TargetedOCR:
    """OCR with precise word location targeting."""
    
    def __init__(self):
        self.page_map = {}  # Store page structure
    
    def step1_map_page_structure(self, base64_image: str) -> dict:
        """Create a map of the page structure."""
        messages = [{
            "role": "system",
            "content": """Analyze this handwritten Spanish page. Return:
1. Total word count
2. For each line, report: 'Line X: [first 5 words] (Y words)'
3. Notable features (paragraphs, margins, page numbers)
Format exactly as shown."""
        }, {
            "role": "user",
            "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]
        }]
        
        # Nano extracts page structure
        # Returns something like:
        # Total: 348 words
        # Line 1: "Que estabamos nosotros todavía me" (8 words)
        # Line 2: "faltaba algo por hacer arte" (7 words)
        # etc.
        
    def step2_extract_targeted_chunk(self, base64_image: str, start_word: int, end_word: int, 
                                   line_num: int, first_word: str, last_word: str) -> str:
        """Extract specific word range with location guidance."""
        messages = [{
            "role": "system", 
            "content": f"""Extract EXACTLY words {start_word} to {end_word} from this manuscript.
Location: Line {line_num}, approximately {(start_word/self.total_words)*100:.0f}% down the page.
The section BEGINS with the word '{first_word}' and ENDS near '{last_word}'.
Return ONLY these {end_word-start_word+1} words. No commentary."""
        }, {
            "role": "user",
            "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]
        }]
        
        # Nano extracts exactly those words
        
    def step3_quality_review(self, extracted_text: str, start_word: int, 
                           end_word: int, expected_first: str) -> dict:
        """Mini reviews extraction quality once."""
        messages = [{
            "role": "system",
            "content": """Review this Spanish manuscript extraction for quality.
Expected: Coherent Spanish text without repetition or meta-commentary.
If issues found, provide the corrected text."""
        }, {
            "role": "user", 
            "content": f"""Nano extracted words {start_word}-{end_word}:
'{extracted_text}'

This should start with '{expected_first}'.
Is this correct? If not, what should it be?"""
        }]
        
        # Mini reviews and potentially corrects
        
    def process_page_with_targeting(self, image_path: str) -> str:
        """Process entire page with targeted extraction."""
        # Step 1: Map the page
        page_structure = self.step1_map_page_structure(base64_image)
        
        # Step 2: Extract in targeted chunks
        chunk_size = 50
        full_text = []
        
        for chunk_start in range(1, total_words, chunk_size):
            chunk_end = min(chunk_start + chunk_size - 1, total_words)
            
            # Find which line this chunk starts on
            line_info = self.find_line_for_word(chunk_start)
            
            # Extract with precise targeting
            chunk_text = self.step2_extract_targeted_chunk(
                base64_image, chunk_start, chunk_end,
                line_info['line_num'], 
                line_info['first_word'],
                line_info['last_word']
            )
            
            # Quality check with mini (only if suspicious)
            if self.looks_suspicious(chunk_text):
                review = self.step3_quality_review(
                    chunk_text, chunk_start, chunk_end, 
                    line_info['first_word']
                )
                if review['needs_correction']:
                    chunk_text = review['corrected_text']
            
            full_text.append(chunk_text)
        
        return ' '.join(full_text)

# Integration into Book Ingestion Crew
class EnhancedBookIngestionCrew:
    """Book ingestion with targeted OCR."""
    
    def __init__(self):
        self.ocr = TargetedOCR()
        
    def create_ocr_task(self):
        return Task(
            description="""Extract text from manuscript pages using targeted OCR:
1. Map page structure with line numbers and word positions
2. Extract 50-word chunks with precise location guidance  
3. Use mini for quality review only when needed
4. Ensure no repetition or hallucination""",
            agent=self.ocr_specialist,
            expected_output="Accurate transcription without repetition"
        )
    
    # The crew orchestrates:
    # 1. Google Drive scanning (existing)
    # 2. Targeted OCR extraction (new approach)
    # 3. Quality validation (mini reviews)
    # 4. Assembly and upload (existing)