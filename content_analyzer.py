"""
Content Analyzer - AI-powered content quality insights for Easy Crawl4AI

This module provides functions to analyze crawled content using AI technologies
and generate insights about content quality, readability, structure, and more.
"""

import os
import json
import logging
import nltk
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not available. Some AI features will be limited.")

# Download necessary NLTK resources on first run
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
try:
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('averaged_perceptron_tagger', quiet=True)
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

# Import NLTK modules after downloading
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk import pos_tag

class ContentAnalyzer:
    """Class to analyze content and provide quality insights"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the content analyzer
        
        Args:
            api_key: OpenAI API key (optional)
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.openai_client = None
        
        # Initialize OpenAI client if available
        if OPENAI_AVAILABLE and self.api_key:
            try:
                openai.api_key = self.api_key
                self.openai_client = openai.OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing OpenAI client: {str(e)}")
    
    def analyze_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze content and return insights
        
        Args:
            content: Dictionary containing crawled content
        
        Returns:
            Dictionary of content insights
        """
        insights = {
            "basic_metrics": {},
            "readability": {},
            "content_structure": {},
            "ai_analysis": {},
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        
        # Extract text content
        text = content.get("text", "")
        title = content.get("title", "")
        
        if not text:
            logger.warning("No text content to analyze")
            insights["error"] = "No text content to analyze"
            return insights
        
        # Basic metrics analysis
        basic_metrics = self.analyze_basic_metrics(text)
        insights["basic_metrics"] = basic_metrics
        
        # Readability analysis
        readability = self.analyze_readability(text)
        insights["readability"] = readability
        
        # Content structure analysis
        structure = self.analyze_structure(text)
        insights["content_structure"] = structure
        
        # AI-powered analysis if available
        if self.openai_client:
            ai_analysis = self.analyze_with_ai(title, text)
            insights["ai_analysis"] = ai_analysis
        else:
            insights["ai_analysis"] = {
                "status": "unavailable",
                "message": "OpenAI API key not configured or package not installed"
            }
        
        return insights
    
    def analyze_basic_metrics(self, text: str) -> Dict[str, Any]:
        """
        Analyze basic metrics of text content
        
        Args:
            text: Text content to analyze
        
        Returns:
            Dictionary of basic metrics
        """
        # Tokenize the text
        sentences = sent_tokenize(text)
        words = word_tokenize(text)
        
        # Filter out punctuation from words
        words = [word for word in words if word.isalnum()]
        
        # Get stopwords
        stop_words = set(stopwords.words('english'))
        
        # Calculate word frequency
        word_freq = {}
        for word in words:
            if word.lower() not in stop_words:
                if word.lower() in word_freq:
                    word_freq[word.lower()] += 1
                else:
                    word_freq[word.lower()] = 1
        
        # Calculate character count
        char_count = sum(len(word) for word in words)
        
        # Calculate average word length
        avg_word_length = char_count / len(words) if words else 0
        
        # Calculate average sentence length
        avg_sentence_length = len(words) / len(sentences) if sentences else 0
        
        # Get top keywords (most frequent non-stopwords)
        top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Calculate unique word ratio
        unique_words = len(set(word.lower() for word in words))
        unique_word_ratio = unique_words / len(words) if words else 0
        
        return {
            "word_count": len(words),
            "sentence_count": len(sentences),
            "character_count": char_count,
            "avg_word_length": round(avg_word_length, 2),
            "avg_sentence_length": round(avg_sentence_length, 2),
            "unique_words": unique_words,
            "unique_word_ratio": round(unique_word_ratio, 3),
            "top_keywords": [{"word": word, "count": count} for word, count in top_keywords]
        }
    
    def analyze_readability(self, text: str) -> Dict[str, Any]:
        """
        Analyze readability of text content
        
        Args:
            text: Text content to analyze
        
        Returns:
            Dictionary of readability metrics
        """
        # Tokenize text
        sentences = sent_tokenize(text)
        words = word_tokenize(text)
        
        # Filter out punctuation from words
        words = [word for word in words if word.isalnum()]
        
        # Count syllables (simplified approach)
        def count_syllables(word):
            vowels = "aeiouy"
            word = word.lower()
            count = 0
            if word[0] in vowels:
                count += 1
            for i in range(1, len(word)):
                if word[i] in vowels and word[i-1] not in vowels:
                    count += 1
            if word.endswith("e"):
                count -= 1
            if count == 0:
                count = 1
            return count
        
        syllable_count = sum(count_syllables(word) for word in words)
        
        # Calculate Flesch Reading Ease
        # FRE = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
        word_count = len(words)
        sentence_count = len(sentences)
        
        if word_count == 0 or sentence_count == 0:
            flesch_reading_ease = 0
        else:
            flesch_reading_ease = 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (syllable_count / word_count)
        
        # Calculate Flesch-Kincaid Grade Level
        # FKGL = 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59
        if word_count == 0 or sentence_count == 0:
            flesch_kincaid_grade = 0
        else:
            flesch_kincaid_grade = 0.39 * (word_count / sentence_count) + 11.8 * (syllable_count / word_count) - 15.59
        
        # Determine readability assessment
        if flesch_reading_ease >= 90:
            readability_assessment = "Very Easy: 5th grade level"
        elif flesch_reading_ease >= 80:
            readability_assessment = "Easy: 6th grade level"
        elif flesch_reading_ease >= 70:
            readability_assessment = "Fairly Easy: 7th grade level"
        elif flesch_reading_ease >= 60:
            readability_assessment = "Standard: 8th-9th grade level"
        elif flesch_reading_ease >= 50:
            readability_assessment = "Fairly Difficult: 10th-12th grade level"
        elif flesch_reading_ease >= 30:
            readability_assessment = "Difficult: College level"
        else:
            readability_assessment = "Very Difficult: College graduate level"
        
        return {
            "flesch_reading_ease": round(flesch_reading_ease, 2),
            "flesch_kincaid_grade": round(flesch_kincaid_grade, 2),
            "readability_assessment": readability_assessment,
            "syllable_count": syllable_count,
            "avg_syllables_per_word": round(syllable_count / word_count if word_count else 0, 2)
        }
    
    def analyze_structure(self, text: str) -> Dict[str, Any]:
        """
        Analyze structure of text content
        
        Args:
            text: Text content to analyze
        
        Returns:
            Dictionary of structure metrics
        """
        # Tokenize text
        sentences = sent_tokenize(text)
        words = word_tokenize(text)
        
        # Get POS tags
        pos_tags = pos_tag(words)
        
        # Count different POS
        num_nouns = sum(1 for _, pos in pos_tags if pos.startswith('NN'))
        num_verbs = sum(1 for _, pos in pos_tags if pos.startswith('VB'))
        num_adjectives = sum(1 for _, pos in pos_tags if pos.startswith('JJ'))
        num_adverbs = sum(1 for _, pos in pos_tags if pos.startswith('RB'))
        
        # Calculate paragraph estimate (rough approximation)
        # Consider a paragraph break when there are consecutive newlines
        paragraphs = text.split('\n\n')
        paragraph_count = len([p for p in paragraphs if p.strip()])
        
        # Calculate section estimate (rough approximation)
        # Look for lines that might be headings (short lines not ending with period)
        potential_headings = [
            line for line in text.split('\n')
            if line.strip() and not line.strip().endswith(('.', '?', '!')) 
            and len(line.strip().split()) < 10 and len(line.strip()) < 100
        ]
        
        # Structure assessment
        pos_ratio = num_nouns / max(num_verbs, 1)
        if pos_ratio > 3:
            style_assessment = "Highly descriptive, noun-heavy content"
        elif pos_ratio > 2:
            style_assessment = "Descriptive content with balanced structure"
        elif pos_ratio > 1:
            style_assessment = "Balanced content with good noun-verb ratio"
        else:
            style_assessment = "Action-oriented, verb-heavy content"
        
        if paragraph_count == 0:
            organization_assessment = "No clear paragraph structure detected"
        elif paragraph_count == 1:
            organization_assessment = "Single block of text, minimal structure"
        elif paragraph_count < 5:
            organization_assessment = "Basic paragraph structure"
        elif paragraph_count < 10:
            organization_assessment = "Well-structured content with multiple paragraphs"
        else:
            organization_assessment = "Extensive content with comprehensive paragraph structure"
        
        return {
            "paragraph_count": paragraph_count,
            "estimated_sections": len(potential_headings),
            "pos_distribution": {
                "nouns": num_nouns,
                "verbs": num_verbs,
                "adjectives": num_adjectives,
                "adverbs": num_adverbs
            },
            "noun_verb_ratio": round(pos_ratio, 2),
            "style_assessment": style_assessment,
            "organization_assessment": organization_assessment
        }
    
    def analyze_with_ai(self, title: str, text: str) -> Dict[str, Any]:
        """
        Analyze content using OpenAI's API
        
        Args:
            title: Title of the content
            text: Text content to analyze
        
        Returns:
            Dictionary of AI-powered insights
        """
        if not self.openai_client:
            return {
                "status": "error",
                "message": "OpenAI client not available"
            }
        
        try:
            # Truncate text if too long
            max_length = 8000
            if len(text) > max_length:
                truncated_text = text[:max_length] + "... [truncated]"
            else:
                truncated_text = text
            
            # Create prompt
            prompt = f"""
            Analyze the following content and provide insights on quality, topic, tone, and structure.
            
            Title: {title}
            
            Content:
            {truncated_text}
            
            Provide the following in JSON format:
            1. A 1-2 sentence summary of the content
            2. Overall quality score (scale 1-10)
            3. Quality assessment (excellent, good, average, poor)
            4. Target audience (who would find this content most useful/relevant)
            5. Content purpose (informational, persuasive, educational, etc.)
            6. A list of 3-5 content strengths
            7. A list of 3-5 improvement areas
            8. A list of 3-5 specific recommendations to improve the content
            
            Format your response as a JSON object with these exact fields:
            {
              "summary": "brief summary here",
              "quality_score": 7,
              "quality_assessment": "good",
              "target_audience": "audience description here",
              "content_purpose": "purpose description here",
              "strengths": ["strength 1", "strength 2", "strength 3"],
              "improvement_areas": ["area 1", "area 2", "area 3"],
              "recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"]
            }
            """
            
            # Call OpenAI API
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a content analysis expert. Analyze the provided content and return insights in the specified JSON format. Be concise and specific."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            # Parse JSON response
            try:
                response_text = response.choices[0].message.content
                
                # Extract JSON from response (in case there's extra text)
                # Find opening and closing braces
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    ai_insights = json.loads(json_str)
                else:
                    # Fall back to parsing the whole response
                    ai_insights = json.loads(response_text)
                
                return {
                    "status": "success",
                    "insights": ai_insights
                }
            except json.JSONDecodeError:
                logger.error(f"Failed to parse OpenAI response as JSON: {response_text}")
                return {
                    "status": "error",
                    "message": "Failed to parse AI response as JSON",
                    "raw_response": response_text
                }
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            return {
                "status": "error",
                "message": f"Error calling OpenAI API: {str(e)}"
            }
        
def analyze_content_quality(content: Dict[str, Any], api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze content quality and provide insights
    
    Args:
        content: Dictionary containing crawled content
        api_key: OpenAI API key (optional)
    
    Returns:
        Dictionary of content quality insights
    """
    analyzer = ContentAnalyzer(api_key)
    return analyzer.analyze_content(content)

if __name__ == "__main__":
    # Test with a sample content
    sample_content = {
        "title": "Sample Article",
        "text": """
        This is a sample article for testing the content analyzer.
        It contains multiple sentences with varying structures.
        Some sentences are short. Others are much longer and contain more complex structures with multiple clauses and conjunctions.
        
        This represents a new paragraph in the content.
        We can test how well the paragraph detection works.
        
        Here is another paragraph with technical terms like Python, NLP, and machine learning.
        These terms should be identified as important keywords in the content.
        """
    }
    
    # Test the analyzer
    analyzer = ContentAnalyzer()
    insights = analyzer.analyze_content(sample_content)
    
    # Print results
    print(json.dumps(insights, indent=2))