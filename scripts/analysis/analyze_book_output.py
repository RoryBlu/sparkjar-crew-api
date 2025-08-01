#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""
Analysis script for Book Ingestion Crew output quality.
Reads and analyzes Spanish and English output files against source images.
"""
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any
import tempfile
import os

# Add project root to path
script_dir = Path(__file__).parent
crew_api_root = script_dir.parent.parent

from sparkjar_shared.tools.google_drive_tool import GoogleDriveTool
from sparkjar_shared.tools.document.ocr_tool import OCRTool

class BookOutputAnalyzer:
    """Analyzes book ingestion crew output quality."""
    
    def __init__(self):
        self.drive_tool = GoogleDriveTool()
        self.ocr_tool = OCRTool()
        
    def analyze_job_output(self, author_name: str, job_id: str, 
                          folder_path: str, client_user_id: str) -> Dict[str, Any]:
        """
        Analyze the output files for a specific job.
        
        Args:
            author_name: Author name (e.g., 'castor_gonzalez')
            job_id: Job ID used in processing
            folder_path: Google Drive folder path
            client_user_id: Client user ID for credentials
            
        Returns:
            Analysis results dictionary
        """
        results = {
            "job_id": job_id,
            "author": author_name,
            "analysis_timestamp": self._get_timestamp(),
            "source_analysis": {},
            "output_analysis": {},
            "quality_metrics": {},
            "recommendations": []
        }
        
        # 1. Analyze source images
        logger.info(f"📁 Analyzing source images in {folder_path}")
        source_analysis = self._analyze_source_images(folder_path, client_user_id)
        results["source_analysis"] = source_analysis
        
        # 2. Download and analyze output files
        logger.info(f"📄 Analyzing output files for {author_name}_{job_id}")
        output_analysis = self._analyze_output_files(
            author_name, job_id, folder_path, client_user_id
        )
        results["output_analysis"] = output_analysis
        
        # 3. Calculate quality metrics
        logger.info("📊 Calculating quality metrics")
        quality_metrics = self._calculate_quality_metrics(
            source_analysis, output_analysis
        )
        results["quality_metrics"] = quality_metrics
        
        # 4. Generate recommendations
        logger.info("💡 Generating recommendations")
        recommendations = self._generate_recommendations(quality_metrics)
        results["recommendations"] = recommendations
        
        return results
    
    def _analyze_source_images(self, folder_path: str, client_user_id: str) -> Dict[str, Any]:
        """Analyze source images to establish baseline."""
        # Download source images
        download_result = self.drive_tool._run(
            folder_path=folder_path,
            client_user_id=client_user_id,
            file_types=["image/jpeg", "image/png", "image/jpg", "image/webp"],
            download=True
        )
        
        download_data = json.loads(download_result)
        if download_data.get('status') != 'success':
            return {"error": "Failed to download source images"}
            
        files = download_data.get('files', [])
        
        analysis = {
            "total_pages": len(files),
            "image_files": [],
            "estimated_complexity": "unknown",
            "languages_detected": [],
            "sample_analysis": {}
        }
        
        # Analyze first few pages for complexity estimation
        for i, file_info in enumerate(files[:3]):  # Sample first 3 pages
            if 'local_path' not in file_info:
                continue
                
            try:
                # Use OCR tool to analyze image
                ocr_result = self.ocr_tool._run(file_path=file_info['local_path'])
                ocr_data = json.loads(ocr_result)
                
                page_analysis = {
                    "file_name": file_info['name'],
                    "estimated_words": len(ocr_data.get('text', '').split()) if ocr_data.get('text') else 0,
                    "detected_language": ocr_data.get('language', 'unknown'),
                    "complexity_indicators": self._assess_image_complexity(ocr_data)
                }
                
                analysis["image_files"].append(page_analysis)
                
                # Track languages
                lang = page_analysis["detected_language"]
                if lang not in analysis["languages_detected"]:
                    analysis["languages_detected"].append(lang)
                    
            except Exception as e:
                logger.error(f"⚠️ Error analyzing {file_info['name']}: {e}")
        
        # Estimate overall complexity
        avg_words = sum(p["estimated_words"] for p in analysis["image_files"]) / max(len(analysis["image_files"]), 1)
        if avg_words > 200:
            analysis["estimated_complexity"] = "high"
        elif avg_words > 100:
            analysis["estimated_complexity"] = "medium"
        else:
            analysis["estimated_complexity"] = "low"
            
        return analysis
    
    def _analyze_output_files(self, author_name: str, job_id: str, 
                             folder_path: str, client_user_id: str) -> Dict[str, Any]:
        """Download and analyze output files."""
        analysis = {
            "spanish_file": {},
            "english_file": {},
            "files_found": []
        }
        
        # Try to download Spanish file
        spanish_filename = f"{author_name}_{job_id}_es.txt"
        spanish_analysis = self._download_and_analyze_text_file(
            spanish_filename, folder_path, client_user_id, "spanish"
        )
        analysis["spanish_file"] = spanish_analysis
        if spanish_analysis.get("found"):
            analysis["files_found"].append("spanish")
        
        # Try to download English file
        english_filename = f"{author_name}_{job_id}_en.txt"
        english_analysis = self._download_and_analyze_text_file(
            english_filename, folder_path, client_user_id, "english"
        )
        analysis["english_file"] = english_analysis
        if english_analysis.get("found"):
            analysis["files_found"].append("english")
            
        return analysis
    
    def _download_and_analyze_text_file(self, filename: str, folder_path: str, 
                                       client_user_id: str, language: str) -> Dict[str, Any]:
        """Download and analyze a specific text file."""
        analysis = {
            "filename": filename,
            "found": False,
            "file_size": 0,
            "word_count": 0,
            "line_count": 0,
            "language_analysis": {},
            "content_preview": "",
            "quality_indicators": {}
        }
        
        try:
            # List files to find our target
            list_result = self.drive_tool._run(
                folder_path=folder_path,
                client_user_id=client_user_id,
                file_types=["text/plain"],
                download=False
            )
            
            list_data = json.loads(list_result)
            if list_data.get('status') != 'success':
                return analysis
            
            # Find our file
            target_file = None
            for file_info in list_data.get('files', []):
                if file_info['name'] == filename:
                    target_file = file_info
                    break
            
            if not target_file:
                return analysis
            
            analysis["found"] = True
            analysis["file_size"] = target_file.get('size', 0)
            
            # Download the file content
            download_result = self.drive_tool._run(
                folder_path=folder_path,
                client_user_id=client_user_id,
                file_types=["text/plain"],
                download=True
            )
            
            download_data = json.loads(download_result)
            if download_data.get('status') == 'success':
                # Find downloaded file
                for file_info in download_data.get('files', []):
                    if file_info['name'] == filename and 'local_path' in file_info:
                        with open(file_info['local_path'], 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        analysis.update(self._analyze_text_content(content, language))
                        break
                        
        except Exception as e:
            analysis["error"] = str(e)
            
        return analysis
    
    def _analyze_text_content(self, content: str, expected_language: str) -> Dict[str, Any]:
        """Analyze text content for quality indicators."""
        lines = content.split('\n')
        words = content.split()
        
        analysis = {
            "word_count": len(words),
            "line_count": len(lines),
            "character_count": len(content),
            "avg_words_per_line": len(words) / max(len([l for l in lines if l.strip()]), 1),
            "content_preview": content[:500] + "..." if len(content) > 500 else content,
            "language_analysis": self._analyze_language_quality(content, expected_language),
            "quality_indicators": self._assess_text_quality(content)
        }
        
        return analysis
    
    def _analyze_language_quality(self, content: str, expected_language: str) -> Dict[str, Any]:
        """Analyze language-specific quality indicators."""
        analysis = {
            "expected_language": expected_language,
            "spanish_indicators": 0,
            "english_indicators": 0,
            "special_characters": 0,
            "proper_nouns": [],
            "potential_ocr_errors": []
        }
        
        # Spanish language indicators
        spanish_patterns = [
            r'\bel\b', r'\bla\b', r'\blos\b', r'\blas\b',  # articles
            r'\bque\b', r'\bcon\b', r'\bpor\b', r'\bpara\b',  # common words
            r'ñ', r'á', r'é', r'í', r'ó', r'ú'  # Spanish characters
        ]
        
        for pattern in spanish_patterns:
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            analysis["spanish_indicators"] += matches
        
        # English language indicators
        english_patterns = [
            r'\bthe\b', r'\band\b', r'\bof\b', r'\bto\b',
            r'\bin\b', r'\ba\b', r'\bthat\b', r'\bwas\b'
        ]
        
        for pattern in english_patterns:
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            analysis["english_indicators"] += matches
        
        # Count special characters
        analysis["special_characters"] = len(re.findall(r'[ñáéíóúü¿¡]', content, re.IGNORECASE))
        
        # Find potential proper nouns (capitalized words)
        proper_nouns = re.findall(r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñü]+\b', content)
        analysis["proper_nouns"] = list(set(proper_nouns))[:10]  # Top 10 unique
        
        # Look for potential OCR errors
        ocr_error_patterns = [
            r'\b[a-z]+\d+[a-z]*\b',  # Mixed letters and numbers
            r'\b[A-Z]{3,}\b',  # All caps sequences
            r'[l1][l1][l1]',  # Repeated l/1 confusion
            r'[oO0][oO0][oO0]'  # Repeated o/0 confusion
        ]
        
        for pattern in ocr_error_patterns:
            errors = re.findall(pattern, content)
            analysis["potential_ocr_errors"].extend(errors)
        
        analysis["potential_ocr_errors"] = list(set(analysis["potential_ocr_errors"]))[:10]
        
        return analysis
    
    def _assess_text_quality(self, content: str) -> Dict[str, Any]:
        """Assess overall text quality."""
        quality = {
            "coherence_score": 0,
            "sentence_structure_score": 0,
            "vocabulary_richness": 0,
            "readability_estimate": "unknown",
            "issues_found": []
        }
        
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if sentences:
            # Basic coherence: average sentence length
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            if 10 <= avg_sentence_length <= 25:
                quality["coherence_score"] = 0.8
            elif 5 <= avg_sentence_length <= 35:
                quality["coherence_score"] = 0.6
            else:
                quality["coherence_score"] = 0.3
            
            # Sentence structure: proper capitalization
            properly_capitalized = sum(1 for s in sentences if s[0].isupper())
            quality["sentence_structure_score"] = properly_capitalized / len(sentences)
            
            # Vocabulary richness
            words = content.lower().split()
            unique_words = set(words)
            if words:
                quality["vocabulary_richness"] = len(unique_words) / len(words)
        
        # Readability estimate
        if quality["coherence_score"] > 0.7 and quality["sentence_structure_score"] > 0.7:
            quality["readability_estimate"] = "high"
        elif quality["coherence_score"] > 0.5 and quality["sentence_structure_score"] > 0.5:
            quality["readability_estimate"] = "medium"
        else:
            quality["readability_estimate"] = "low"
        
        # Check for common issues
        if len(re.findall(r'\[.*?\]', content)) > 5:
            quality["issues_found"].append("multiple_placeholder_sections")
        
        if len(re.findall(r'\b\w{20,}\b', content)) > 3:
            quality["issues_found"].append("extremely_long_words")
        
        if content.count('???') > 3:
            quality["issues_found"].append("many_unknown_characters")
            
        return quality
    
    def _assess_image_complexity(self, ocr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess complexity of source image based on OCR data."""
        indicators = {
            "handwritten": False,
            "cursive": False,
            "multiple_columns": False,
            "poor_quality": False,
            "complexity_score": 0
        }
        
        text = ocr_data.get('text', '')
        confidence = ocr_data.get('confidence', 0)
        
        # Low confidence might indicate handwritten/cursive text
        if confidence < 0.7:
            indicators["poor_quality"] = True
            indicators["complexity_score"] += 2
        
        if confidence < 0.5:
            indicators["handwritten"] = True
            indicators["complexity_score"] += 3
        
        # Short, fragmented text might indicate cursive or poor quality
        if len(text.split()) < 50 and confidence < 0.8:
            indicators["cursive"] = True
            indicators["complexity_score"] += 2
        
        return indicators
    
    def _calculate_quality_metrics(self, source_analysis: Dict, output_analysis: Dict) -> Dict[str, Any]:
        """Calculate overall quality metrics."""
        metrics = {
            "extraction_efficiency": 0,
            "language_accuracy": 0,
            "content_preservation": 0,
            "output_completeness": 0,
            "overall_score": 0,
            "grade": "F"
        }
        
        # Extraction efficiency
        source_pages = source_analysis.get("total_pages", 1)
        spanish_words = output_analysis.get("spanish_file", {}).get("word_count", 0)
        
        if source_pages > 0 and spanish_words > 0:
            words_per_page = spanish_words / source_pages
            if words_per_page > 150:
                metrics["extraction_efficiency"] = 0.9
            elif words_per_page > 100:
                metrics["extraction_efficiency"] = 0.7
            elif words_per_page > 50:
                metrics["extraction_efficiency"] = 0.5
            else:
                metrics["extraction_efficiency"] = 0.3
        
        # Language accuracy
        spanish_file = output_analysis.get("spanish_file", {})
        if spanish_file.get("found"):
            lang_analysis = spanish_file.get("language_analysis", {})
            spanish_indicators = lang_analysis.get("spanish_indicators", 0)
            english_indicators = lang_analysis.get("english_indicators", 0)
            
            total_indicators = spanish_indicators + english_indicators
            if total_indicators > 0:
                metrics["language_accuracy"] = spanish_indicators / total_indicators
            else:
                metrics["language_accuracy"] = 0.5
        
        # Content preservation
        quality_indicators = spanish_file.get("quality_indicators", {})
        readability = quality_indicators.get("readability_estimate", "low")
        if readability == "high":
            metrics["content_preservation"] = 0.9
        elif readability == "medium":
            metrics["content_preservation"] = 0.7
        else:
            metrics["content_preservation"] = 0.4
        
        # Output completeness
        files_found = len(output_analysis.get("files_found", []))
        expected_files = 2  # Spanish + English
        metrics["output_completeness"] = files_found / expected_files
        
        # Overall score
        weights = {
            "extraction_efficiency": 0.3,
            "language_accuracy": 0.25,
            "content_preservation": 0.3,
            "output_completeness": 0.15
        }
        
        metrics["overall_score"] = sum(
            metrics[key] * weights[key] for key in weights
        )
        
        # Assign grade
        if metrics["overall_score"] >= 0.9:
            metrics["grade"] = "A+"
        elif metrics["overall_score"] >= 0.8:
            metrics["grade"] = "A"
        elif metrics["overall_score"] >= 0.7:
            metrics["grade"] = "B"
        elif metrics["overall_score"] >= 0.6:
            metrics["grade"] = "C"
        elif metrics["overall_score"] >= 0.5:
            metrics["grade"] = "D"
        else:
            metrics["grade"] = "F"
        
        return metrics
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on quality metrics."""
        recommendations = []
        
        if metrics["extraction_efficiency"] < 0.7:
            recommendations.append(
                "🔍 Consider adjusting OCR chunk size or retry parameters for better text extraction"
            )
        
        if metrics["language_accuracy"] < 0.8:
            recommendations.append(
                "🌐 Review language detection and context usage in OCR specialist"
            )
        
        if metrics["content_preservation"] < 0.7:
            recommendations.append(
                "📝 Improve assembly and literary rewriting to maintain better coherence"
            )
        
        if metrics["output_completeness"] < 1.0:
            recommendations.append(
                "📄 Ensure both Spanish and English outputs are generated successfully"
            )
        
        if metrics["overall_score"] < 0.6:
            recommendations.append(
                "⚠️ Overall quality is below acceptable threshold. Review entire pipeline."
            )
        elif metrics["overall_score"] > 0.8:
            recommendations.append(
                "✅ Excellent quality! Pipeline is performing well."
            )
        
        return recommendations
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def print_analysis_report(self, analysis: Dict[str, Any]):
        """Print a formatted analysis report."""
        logger.info("\n" + "="*80)
        logger.info(f"📊 BOOK INGESTION ANALYSIS REPORT")
        logger.info("="*80)
        logger.info(f"Job ID: {analysis['job_id']}")
        logger.info(f"Author: {analysis['author']}")
        logger.info(f"Timestamp: {analysis['analysis_timestamp']}")
        
        # Source Analysis
        logger.info(f"\n📁 SOURCE ANALYSIS:")
        source = analysis["source_analysis"]
        logger.info(f"  Total Pages: {source.get('total_pages', 'Unknown')}")
        logger.info(f"  Estimated Complexity: {source.get('estimated_complexity', 'Unknown')}")
        logger.info(f"  Languages Detected: {', '.join(source.get('languages_detected', ['Unknown']))}")
        
        # Output Analysis
        logger.info(f"\n📄 OUTPUT ANALYSIS:")
        output = analysis["output_analysis"]
        files_found = output.get("files_found", [])
        logger.info(f"  Files Found: {', '.join(files_found) if files_found else 'None'}")
        
        spanish_file = output.get("spanish_file", {})
        if spanish_file.get("found"):
            logger.info(f"  Spanish File: {spanish_file['word_count']} words, {spanish_file['line_count']} lines")
        
        english_file = output.get("english_file", {})
        if english_file.get("found"):
            logger.info(f"  English File: {english_file['word_count']} words, {english_file['line_count']} lines")
        
        # Quality Metrics
        logger.info(f"\n📊 QUALITY METRICS:")
        metrics = analysis["quality_metrics"]
        logger.info(f"  Overall Grade: {metrics['grade']} ({metrics['overall_score']:.2f})")
        logger.info(f"  Extraction Efficiency: {metrics['extraction_efficiency']:.2f}")
        logger.info(f"  Language Accuracy: {metrics['language_accuracy']:.2f}")
        logger.info(f"  Content Preservation: {metrics['content_preservation']:.2f}")
        logger.info(f"  Output Completeness: {metrics['output_completeness']:.2f}")
        
        # Recommendations
        logger.info(f"\n💡 RECOMMENDATIONS:")
        for rec in analysis["recommendations"]:
            logger.info(f"  {rec}")
        
        logger.info("\n" + "="*80)

def main():
    """Main function for command-line usage."""
    if len(sys.argv) < 5:
        logger.info("Usage: python analyze_book_output.py <author_name> <job_id> <folder_path> <client_user_id>")
        logger.info("Example: python analyze_book_output.py castor_gonzalez test-job-123 'folder_id/path' 'user-uuid'")
        sys.exit(1)
    
    author_name = sys.argv[1]
    job_id = sys.argv[2]
    folder_path = sys.argv[3]
    client_user_id = sys.argv[4]
    
    analyzer = BookOutputAnalyzer()
    
    try:
        logger.info(f"🔍 Starting analysis for {author_name}_{job_id}")
        analysis = analyzer.analyze_job_output(author_name, job_id, folder_path, client_user_id)
        
        analyzer.print_analysis_report(analysis)
        
        # Save detailed results
        output_file = f"analysis_{author_name}_{job_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n💾 Detailed analysis saved to {output_file}")
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()